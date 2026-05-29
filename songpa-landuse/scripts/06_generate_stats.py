# -*- coding: utf-8 -*-
"""
06_generate_stats.py — 통계 JSON 산출
======================================

입력:
  - data/interim/parcels_final.parquet (PNU, JIBUN, zone_norm, main_purpose, area_m2)
  - data/processed/oa_stats.geojson (TOT_OA_CD, population, households)
  - data/processed/admin_emd.geojson (EMD_CD, EMD_KOR_NM) — 동 코드→이름 매핑용

출력:
  - frontend/public/data/stats.json

JSON 구조:
  {
    "summary": {"parcel_count", "building_count", "total_area_m2", "emd_count"},
    "by_purpose": [{"key", "parcels", "area_m2", "pct"}, ...],
    "by_zone": [{"key", "parcels", "area_m2", "pct"}, ...],
    "by_emd_purpose": [{"emd", "purpose", "parcels", "area_m2"}, ...],
    "oa_totals": {"population", "households"}
  }
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import geopandas as gpd
import pandas as pd

from utils.io import read_parquet

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

PROJECT_ROOT = SCRIPT_DIR.parent

PARCELS_IN = PROJECT_ROOT / "data" / "interim" / "parcels_final.parquet"
OA_IN = PROJECT_ROOT / "data" / "processed" / "oa_stats.geojson"
EMD_IN = PROJECT_ROOT / "data" / "processed" / "admin_emd.geojson"
STATS_OUT = PROJECT_ROOT / "frontend" / "public" / "data" / "stats.json"


# ---------------------------------------------------------------------------
# 법정동코드 → 행정동명 매핑
# ---------------------------------------------------------------------------
def _build_emd_name_map(emd_path: Path) -> dict[str, str]:
    """admin_emd.geojson에서 법정동코드(3자리) → EMD_KOR_NM 딕셔너리를 구축한다.

    EMD_CD는 8자리 (시군구5 + 동3): 예) 11710101 → 동코드 '101'
    PNU는 19자리에서 [5:8] = 법정동 3자리: 예) 1171010100... → '101'
    """
    if not emd_path.exists():
        logger.warning(
            "행정동 GeoJSON(%s)이 없습니다. 동 이름 대신 코드를 사용합니다.",
            emd_path,
        )
        return {}

    emd = gpd.read_file(emd_path)
    name_map: dict[str, str] = {}

    for _, row in emd.iterrows():
        code = str(row.get("EMD_CD", "")).strip()
        name = str(row.get("EMD_KOR_NM", "")).strip()
        if code and name and len(code) >= 8:
            # EMD_CD[5:8] = 법정동 3자리 코드 → 동 이름
            dong_3 = code[5:8]
            name_map[dong_3] = name

    logger.info("동 이름 매핑: %d개 로드", len(name_map))
    return name_map


def _resolve_emd(pnu: str, emd_map: dict[str, str]) -> str:
    """PNU에서 법정동코드 3자리(chars [5:8])를 추출하여 동 이름을 반환한다."""
    if not isinstance(pnu, str) or len(pnu) < 10:
        return "알수없음"
    dong_cd = pnu[5:8]
    return emd_map.get(dong_cd, dong_cd)



# ---------------------------------------------------------------------------
# 집계 함수들
# ---------------------------------------------------------------------------
def _calc_by_group(
    df: pd.DataFrame,
    group_col: str,
    total_area: float,
) -> list[dict]:
    """group_col 기준으로 필지수·면적·면적비율(%)를 집계한다."""
    agg = (
        df.groupby(group_col, as_index=False)
        .agg(parcels=("PNU", "count"), area_m2=("area_m2", "sum"))
    )
    agg = agg.sort_values("area_m2", ascending=False)

    result = []
    for _, row in agg.iterrows():
        pct = round(row["area_m2"] / total_area * 100, 1) if total_area > 0 else 0.0
        result.append({
            "key": row[group_col],
            "parcels": int(row["parcels"]),
            "area_m2": round(float(row["area_m2"]), 1),
            "pct": pct,
        })
    return result


def _calc_emd_purpose(
    df: pd.DataFrame,
    emd_map: dict[str, str],
) -> list[dict]:
    """행정동 × 주용도 교차표를 생성한다."""
    df = df.copy()
    df["emd"] = df["PNU"].apply(lambda x: _resolve_emd(x, emd_map))

    agg = (
        df.groupby(["emd", "main_purpose"], as_index=False)
        .agg(parcels=("PNU", "count"), area_m2=("area_m2", "sum"))
    )
    agg = agg.sort_values(["emd", "area_m2"], ascending=[True, False])

    return [
        {
            "emd": row["emd"],
            "purpose": row["main_purpose"],
            "parcels": int(row["parcels"]),
            "area_m2": round(float(row["area_m2"]), 1),
        }
        for _, row in agg.iterrows()
    ]


# ---------------------------------------------------------------------------
# 메인 처리
# ---------------------------------------------------------------------------
def main() -> None:
    """통계 JSON 산출."""

    # ── 1. 데이터 로드 ───────────────────────────────────────────────
    parcels = read_parquet(PARCELS_IN)
    parcels["PNU"] = parcels["PNU"].astype(str)
    parcels["area_m2"] = pd.to_numeric(parcels["area_m2"], errors="coerce").fillna(0.0)

    # main_purpose가 없을 경우 기본값
    if "main_purpose" not in parcels.columns:
        parcels["main_purpose"] = "기타"

    # zone_norm이 없을 경우 기본값
    if "zone_norm" not in parcels.columns:
        parcels["zone_norm"] = "기타"

    logger.info("필지: %d건 로드", len(parcels))

    # ── 2. 동 이름 매핑 ──────────────────────────────────────────────
    emd_map = _build_emd_name_map(EMD_IN)

    # ── 3. 전체 요약 ────────────────────────────────────────────────
    total_area = float(parcels["area_m2"].sum())
    parcel_count = len(parcels)

    # 건물이 매칭된 필지 수 (main_purpose != "기타")
    building_count = int((parcels["main_purpose"] != "기타").sum())

    # 고유 법정동 수
    emd_codes = parcels["PNU"].str[5:10].nunique()

    summary = {
        "parcel_count": parcel_count,
        "building_count": building_count,
        "total_area_m2": round(total_area, 1),
        "emd_count": int(emd_codes),
    }
    logger.info("요약: %s", summary)

    # ── 4. 주용도별 집계 ─────────────────────────────────────────────
    by_purpose = _calc_by_group(parcels, "main_purpose", total_area)
    logger.info("주용도별: %d categories", len(by_purpose))

    # ── 5. 용도지역별 집계 ───────────────────────────────────────────
    by_zone = _calc_by_group(parcels, "zone_norm", total_area)
    logger.info("용도지역별: %d categories", len(by_zone))

    # ── 6. 행정동 × 주용도 교차표 ────────────────────────────────────
    by_emd_purpose = _calc_emd_purpose(parcels, emd_map)
    logger.info("행정동×주용도: %d rows", len(by_emd_purpose))

    # ── 7. OA 인구·가구 합계 ─────────────────────────────────────────
    oa_totals = {"population": 0, "households": 0}
    if OA_IN.exists():
        oa = gpd.read_file(OA_IN)
        oa_totals = {
            "population": int(pd.to_numeric(oa["population"], errors="coerce").fillna(0).sum()),
            "households": int(pd.to_numeric(oa["households"], errors="coerce").fillna(0).sum()),
        }
        logger.info("OA 합계: 인구 %s, 가구 %s",
                     f"{oa_totals['population']:,}",
                     f"{oa_totals['households']:,}")
    else:
        logger.warning("OA GeoJSON(%s)이 없습니다. oa_totals=0", OA_IN)

    # ── 8. JSON 조립 및 저장 ─────────────────────────────────────────
    stats = {
        "summary": summary,
        "by_purpose": by_purpose,
        "by_zone": by_zone,
        "by_emd_purpose": by_emd_purpose,
        "oa_totals": oa_totals,
    }

    STATS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_OUT, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    file_size = STATS_OUT.stat().st_size / 1024
    logger.info("=" * 60)
    logger.info("통계 JSON 저장:")
    logger.info("  출력: %s", STATS_OUT)
    logger.info("  크기: %.1f KB", file_size)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    main()
