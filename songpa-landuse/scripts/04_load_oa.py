# -*- coding: utf-8 -*-
"""
04_load_oa.py — 집계구(OA) 경계 + 인구·가구 통계 로드
======================================================

입력:
  - OA 경계 SHP (EPSG:5179): bnd_oa_11240_2025_2Q.shp
    컬럼: BASE_DATE, ADM_CD, TOT_OA_CD (14자리 str), geometry
  - 인구 CSV (header 없음, 4열): year, oa_code, metric, value
    metric='to_in_001' → 총인구
  - 가구 CSV (header 없음, 4열): year, oa_code, metric, value
    metric='to_ga_001' → 총가구수

출력:
  - data/processed/oa_stats.geojson (EPSG:4326)
    속성: TOT_OA_CD, population, households, ADM_CD
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import geopandas as gpd
import pandas as pd

from utils.crs import to_export
from utils.io import write_geojson

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# 프로젝트 루트 (scripts/ 의 상위)
PROJECT_ROOT = SCRIPT_DIR.parent

# 데이터 소스 경로 (prom/ 디렉터리 기준)
DATA_SRC = PROJECT_ROOT.parent  # c:\Users\gangg\antigravity\prom

OA_SHP = DATA_SRC / "bnd_oa_11240_2025_2Q" / "bnd_oa_11240_2025_2Q.shp"
POP_CSV = DATA_SRC / "_census_reqdoc_1779776403427" / "11240_2024년_인구총괄(총인구).csv"
HH_CSV = DATA_SRC / "_census_reqdoc_1779776403427" / "11240_2024년_가구총괄.csv"

OUT_GEOJSON = PROJECT_ROOT / "data" / "processed" / "oa_stats.geojson"


# ---------------------------------------------------------------------------
# 메인 처리
# ---------------------------------------------------------------------------
def main() -> None:
    """집계구 경계 + 인구·가구 통계 결합 → GeoJSON 출력."""

    # ── 1. OA 경계 로드 ──────────────────────────────────────────────
    logger.info("OA 경계 SHP 읽기: %s", OA_SHP)
    if not OA_SHP.exists():
        raise FileNotFoundError(f"OA 경계 SHP를 찾을 수 없습니다: {OA_SHP}")

    oa = gpd.read_file(OA_SHP, encoding="euc-kr")
    logger.info("  → %d features, CRS=%s", len(oa), oa.crs)

    # TOT_OA_CD를 반드시 문자열 14자리로 유지
    oa["TOT_OA_CD"] = oa["TOT_OA_CD"].astype(str).str.strip()
    oa["ADM_CD"] = oa["ADM_CD"].astype(str).str.strip()

    # 지오메트리 유효성 보정
    invalid_count = (~oa.geometry.is_valid).sum()
    if invalid_count > 0:
        logger.warning("유효하지 않은 지오메트리 %d건 → buffer(0) 보정", invalid_count)
        oa["geometry"] = oa.geometry.buffer(0)

    # ── 2. 인구 CSV 로드 ─────────────────────────────────────────────
    logger.info("인구 CSV 읽기: %s", POP_CSV)
    if not POP_CSV.exists():
        raise FileNotFoundError(f"인구 CSV를 찾을 수 없습니다: {POP_CSV}")

    df_pop = pd.read_csv(
        POP_CSV,
        header=None,
        names=["year", "oa_code", "metric", "value"],
        dtype={"year": str, "oa_code": str, "metric": str},
    )
    logger.info("  → %d rows", len(df_pop))

    # 총인구(to_in_001)만 필터
    df_pop = df_pop[df_pop["metric"] == "to_in_001"].copy()
    df_pop["value"] = pd.to_numeric(df_pop["value"], errors="coerce").fillna(0).astype(int)
    logger.info("  → 'to_in_001' 필터 후 %d rows", len(df_pop))

    # oa_code 당 대표값 (중복 시 최대값)
    pop_agg = (
        df_pop.groupby("oa_code", as_index=False)["value"]
        .max()
        .rename(columns={"value": "population"})
    )

    # ── 3. 가구 CSV 로드 ─────────────────────────────────────────────
    logger.info("가구 CSV 읽기: %s", HH_CSV)
    if not HH_CSV.exists():
        raise FileNotFoundError(f"가구 CSV를 찾을 수 없습니다: {HH_CSV}")

    df_hh = pd.read_csv(
        HH_CSV,
        header=None,
        names=["year", "oa_code", "metric", "value"],
        dtype={"year": str, "oa_code": str, "metric": str},
    )
    logger.info("  → %d rows", len(df_hh))

    # 총가구수(to_ga_001)만 필터
    df_hh = df_hh[df_hh["metric"] == "to_ga_001"].copy()
    df_hh["value"] = pd.to_numeric(df_hh["value"], errors="coerce").fillna(0)
    # 가구수는 float일 수 있으므로 int로 변환 (소수점 버림)
    df_hh["value"] = df_hh["value"].astype(int)
    logger.info("  → 'to_ga_001' 필터 후 %d rows", len(df_hh))

    hh_agg = (
        df_hh.groupby("oa_code", as_index=False)["value"]
        .max()
        .rename(columns={"value": "households"})
    )

    # ── 4. OA 경계와 통계 조인 ───────────────────────────────────────
    logger.info("OA 경계 ↔ 인구·가구 통계 조인")

    oa = oa.merge(pop_agg, left_on="TOT_OA_CD", right_on="oa_code", how="left")
    oa = oa.merge(hh_agg, left_on="TOT_OA_CD", right_on="oa_code", how="left")

    # 조인 키 정리
    oa = oa.drop(columns=["oa_code_x", "oa_code_y"], errors="ignore")

    # 미매칭 OA는 0으로 처리
    oa["population"] = oa["population"].fillna(0).astype(int)
    oa["households"] = oa["households"].fillna(0).astype(int)

    matched_pop = (oa["population"] > 0).sum()
    matched_hh = (oa["households"] > 0).sum()
    logger.info("  → 인구 매칭: %d/%d OA", matched_pop, len(oa))
    logger.info("  → 가구 매칭: %d/%d OA", matched_hh, len(oa))

    # ── 5. 필요 컬럼만 유지 ──────────────────────────────────────────
    keep_cols = ["TOT_OA_CD", "population", "households", "ADM_CD", "geometry"]
    oa = oa[keep_cols].copy()

    # ── 6. EPSG:4326 변환 및 저장 ────────────────────────────────────
    oa = to_export(oa)
    write_geojson(oa, OUT_GEOJSON)

    # ── 7. 요약 로깅 ────────────────────────────────────────────────
    total_pop = oa["population"].sum()
    total_hh = oa["households"].sum()
    logger.info("=" * 60)
    logger.info("집계구(OA) 통계 요약:")
    logger.info("  OA 수:     %d", len(oa))
    logger.info("  총인구:    %s", f"{total_pop:,}")
    logger.info("  총가구수:  %s", f"{total_hh:,}")
    logger.info("  출력:      %s", OUT_GEOJSON)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    main()
