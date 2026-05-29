# -*- coding: utf-8 -*-
"""
05_build_parcel_attrs.py — 필지별 대표 건축물 속성 산정
======================================================

전략 변경: GIS 건물(PNU)과 표제부를 부속지번을 통해 연결한 뒤,
GIS 건물의 PNU로 필지와 직접 조인한다.

입력:
  - data/interim/parcels.parquet
  - data/interim/buildings.parquet (GIS 건물, PNU 포함)
  - data/interim/parcel_building.parquet (부속지번 매핑)

출력:
  - data/interim/parcels_final.parquet
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import geopandas as gpd
import pandas as pd

from utils.io import read_parquet, write_parquet
from utils.normalize import categorize_purpose

# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
PROJECT_ROOT = SCRIPT_DIR.parent

PARCELS_IN = PROJECT_ROOT / "data" / "interim" / "parcels.parquet"
BUILDINGS_IN = PROJECT_ROOT / "data" / "interim" / "buildings.parquet"
PB_IN = PROJECT_ROOT / "data" / "interim" / "parcel_building.parquet"
PARCELS_OUT = PROJECT_ROOT / "data" / "interim" / "parcels_final.parquet"


def main() -> None:
    # ── 1. 필지 데이터 로드 ──────────────────────────────────────────
    parcels = read_parquet(PARCELS_IN)
    parcels["PNU"] = parcels["PNU"].astype(str)
    logger.info("필지: %d건 로드", len(parcels))

    # ── 2. GIS 건물 로드 (PNU + gis_purpose) ─────────────────────────
    buildings = read_parquet(BUILDINGS_IN)
    buildings["PNU"] = buildings["PNU"].astype(str)
    buildings["BD_MGT_SN"] = buildings["BD_MGT_SN"].astype(str)
    logger.info("GIS 건물: %d건 로드", len(buildings))

    # ── 3. 부속지번 매핑 로드 (표제부 주용도 포함) ───────────────────
    pb = pd.read_parquet(PB_IN)
    pb["MGM_BLDRGST_PK"] = pb["MGM_BLDRGST_PK"].astype(str)
    logger.info("표제부 매핑: %d건", len(pb))

    # ── 4. GIS 건물 → 표제부 연결 (BD_MGT_SN → MGM_BLDRGST_PK) ─────
    # BD_MGT_SN 앞자리가 MGM_BLDRGST_PK를 포함하는 경우 매핑
    # 우선 GIS 건물 PNU 기반으로 직접 주용도 배정

    # 4a. GIS 건물에 gis_purpose가 있으므로 바로 사용
    # PNU별 대표 건물 선정 (가장 큰 면적)
    buildings["gis_area"] = pd.to_numeric(buildings["gis_area"], errors="coerce").fillna(0)
    bldg_sorted = buildings.sort_values("gis_area", ascending=False)
    bldg_rep = bldg_sorted.drop_duplicates(subset=["PNU"], keep="first")
    logger.info("GIS PNU 대표 건물: %d", len(bldg_rep))

    # 4b. 표제부에서 MAIN_PURPS_CD_NM 가져오기 (정확한 주용도)
    if "MAIN_PURPS_CD_NM" in pb.columns:
        pk_purpose = pb[["MGM_BLDRGST_PK", "MAIN_PURPS_CD_NM"]].drop_duplicates(
            subset=["MGM_BLDRGST_PK"], keep="first"
        )
        # BD_MGT_SN → MGM_BLDRGST_PK 매핑 시도
        # BD_MGT_SN의 앞부분이 MGM_BLDRGST_PK를 포함
        bldg_rep = bldg_rep.copy()
        bldg_rep["_pk_candidate"] = bldg_rep["BD_MGT_SN"].str[:25]  # 표제부 PK 최대 길이

        # Direct join attempt
        merged = bldg_rep.merge(
            pk_purpose,
            left_on="_pk_candidate",
            right_on="MGM_BLDRGST_PK",
            how="left",
        )
        direct_match = merged["MAIN_PURPS_CD_NM"].notna().sum()
        logger.info("BD_MGT_SN→PK 직접 매핑: %d건 (%.1f%%)",
                     direct_match, direct_match / len(merged) * 100 if len(merged) > 0 else 0)

        # 매핑 성공한 경우 표제부 주용도 사용, 실패 시 gis_purpose 사용
        merged["raw_purpose"] = merged["MAIN_PURPS_CD_NM"].fillna(merged["gis_purpose"])
        bldg_rep_final = merged[["PNU", "raw_purpose"]].copy()
    else:
        # 표제부 없으면 gis_purpose 사용
        bldg_rep_final = bldg_rep[["PNU", "gis_purpose"]].copy()
        bldg_rep_final = bldg_rep_final.rename(columns={"gis_purpose": "raw_purpose"})

    # ── 5. 주용도 범주화 ────────────────────────────────────────────
    bldg_rep_final["main_purpose"] = bldg_rep_final["raw_purpose"].apply(categorize_purpose)

    rep_slim = bldg_rep_final[["PNU", "main_purpose"]].copy()
    rep_slim = rep_slim.drop_duplicates(subset=["PNU"], keep="first")

    # ── 6. 필지와 조인 ──────────────────────────────────────────────
    parcels_final = parcels.merge(rep_slim, on="PNU", how="left")
    parcels_final["main_purpose"] = parcels_final["main_purpose"].fillna("기타")

    # ── 7. 최종 컬럼 정리 ───────────────────────────────────────────
    keep_cols = ["PNU", "JIBUN", "zone_norm", "main_purpose", "area_m2", "geometry"]
    available = [c for c in keep_cols if c in parcels_final.columns]
    parcels_final = parcels_final[available].copy()
    write_parquet(parcels_final, PARCELS_OUT)

    # ── 8. 요약 ─────────────────────────────────────────────────────
    total = len(parcels_final)
    with_building = (parcels_final["main_purpose"] != "기타").sum()
    without_building = total - with_building

    logger.info("=" * 60)
    logger.info("필지 속성 산정 요약:")
    logger.info("  총 필지:          %d", total)
    logger.info("  건물 매칭:        %d (%.1f%%)", with_building, with_building / total * 100 if total else 0)
    logger.info("  미매칭(기타):     %d (%.1f%%)", without_building, without_building / total * 100 if total else 0)

    purpose_dist = parcels_final["main_purpose"].value_counts()
    logger.info("  주용도 분포:")
    for purpose, count in purpose_dist.items():
        pct = count / total * 100 if total else 0
        logger.info("    %-20s %6d (%5.1f%%)", purpose, count, pct)
    logger.info("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    main()
