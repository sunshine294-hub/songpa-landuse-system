# -*- coding: utf-8 -*-
"""
05_build_parcel_attrs.py — 필지별 대표 건축물 속성 산정 (정밀 대장 조인)
========================================================================

규칙 (§2.4):
  1순위: 필지 내 건축물대장 건물 중 총동연면적(TOTAREA)이 최대인 건물의 주용도를 그 필지의 대표 주용도로 지정한다.
  2순위: 동률일 경우 사용승인일(USE_APR_DAY)이 가장 최근인 건물의 주용도.
  3순위: 그마저 같으면 MGM_BLDRGST_PK 사전순 최소값.
  4순위: 대장 매핑이 없는 경우, GIS 건물(gis_area 최대)의 용도(gis_purpose)를 폴백으로 사용.

입력:
  - data/interim/parcels.parquet
  - data/interim/buildings.parquet (GIS 건물, PNU 포함)
  - data/interim/parcel_building.parquet (대장-필지 매핑 및 표제부 컬럼 포함)

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
    logger.info("=" * 60)
    logger.info("05_build_parcel_attrs.py 시작 (정밀 대장 조인)")
    logger.info("=" * 60)

    # ── 1. 필지 데이터 로드 ──────────────────────────────────────────
    parcels = read_parquet(PARCELS_IN)
    parcels["PNU"] = parcels["PNU"].astype(str)
    logger.info("필지: %d건 로드", len(parcels))

    # ── 2. 대장 매핑 로드 (03_load_buildings.py의 출력물) ───────────────
    if not PB_IN.exists():
        raise FileNotFoundError(f"필지-건물 매핑 파일 없음: {PB_IN}")
    pb = pd.read_parquet(PB_IN)
    pb["PNU"] = pb["PNU"].astype(str)
    pb["MGM_BLDRGST_PK"] = pb["MGM_BLDRGST_PK"].astype(str)
    logger.info("필지-건물 대장 매핑: %d건 로드", len(pb))

    # ── 3. 대장 기준 대표 건물 결정 (TOTAREA 최대) ──────────────────────
    # 연면적, 사용승인일 컬럼 전처리
    pb["TOTAREA"] = pd.to_numeric(pb["TOTAREA"], errors="coerce").fillna(0)
    pb["USE_APR_DAY"] = pb["USE_APR_DAY"].fillna("00000000").astype(str)

    # 정렬: 1) TOTAREA 내림차순, 2) USE_APR_DAY 내림차순, 3) PK 오름차순
    pb_sorted = pb.sort_values(
        by=["TOTAREA", "USE_APR_DAY", "MGM_BLDRGST_PK"],
        ascending=[False, False, True]
    )
    # PNU별 중복 제거하여 각 필지별 대표 1동만 남김
    pb_rep = pb_sorted.drop_duplicates(subset=["PNU"], keep="first").copy()
    logger.info("대장 매핑 기반 대표 필지 속성 도출: %d건", len(pb_rep))

    # ── 4. GIS 건물 기반 대표 건물 결정 (대장 매핑 없는 필지용 폴백) ───
    buildings = read_parquet(BUILDINGS_IN)
    buildings["PNU"] = buildings["PNU"].astype(str)
    buildings["gis_area"] = pd.to_numeric(buildings["gis_area"], errors="coerce").fillna(0)
    
    # 정렬: gis_area 내림차순
    bldg_sorted = buildings.sort_values(by="gis_area", ascending=False)
    bldg_rep = bldg_sorted.drop_duplicates(subset=["PNU"], keep="first").copy()
    logger.info("GIS 건물 기반 대표 필지 속성 도출 (폴백용): %d건", len(bldg_rep))

    # ── 5. 필지 정보 결합 (대장 최우선, GIS 차선 폴백) ──────────────────
    # 5a. 대장 대표 주용도 매핑
    pb_slim = pb_rep[["PNU", "MAIN_PURPS_CD_NM", "MGM_BLDRGST_PK"]].copy()
    merged = parcels.merge(pb_slim, on="PNU", how="left")

    # 5b. GIS 대표 용도 매핑 (대장 매핑이 없는 경우 대비)
    bldg_slim = bldg_rep[["PNU", "gis_purpose"]].copy()
    merged = merged.merge(bldg_slim, on="PNU", how="left")

    # 5c. 주용도 최종 결정 및 범주화
    # 대장의 주용도(MAIN_PURPS_CD_NM)가 우선이고 없으면 GIS의 용도(gis_purpose)를 채택
    merged["raw_purpose"] = merged["MAIN_PURPS_CD_NM"].fillna(merged["gis_purpose"])
    merged["main_purpose"] = merged["raw_purpose"].apply(categorize_purpose)
    
    # 주용도가 끝내 없으면 '기타' 처리
    merged["main_purpose"] = merged["main_purpose"].fillna("기타")

    # 대장 매칭 여부 체크
    db_match_cnt = merged["MAIN_PURPS_CD_NM"].notna().sum()
    gis_match_cnt = (merged["MAIN_PURPS_CD_NM"].isna() & merged["gis_purpose"].notna()).sum()
    logger.info("필지 조인 요약:")
    logger.info("  - 건축물대장 매핑 성공: %d건 (%.1f%%)", db_match_cnt, db_match_cnt / len(merged) * 100)
    logger.info("  - GIS 폴백 매핑 성공:   %d건 (%.1f%%)", gis_match_cnt, gis_match_cnt / len(merged) * 100)

    # ── 6. 최종 컬럼 정리 및 저장 ───────────────────────────────────────────
    keep_cols = ["PNU", "JIBUN", "zone_norm", "main_purpose", "area_m2", "geometry"]
    available = [c for c in keep_cols if c in merged.columns]
    parcels_final = merged[available].copy()
    
    write_parquet(parcels_final, PARCELS_OUT)
    logger.info("저장 완료: %s (%d건)", PARCELS_OUT, len(parcels_final))

    # ── 7. 통계 출력 ─────────────────────────────────────────────────────
    total = len(parcels_final)
    purpose_dist = parcels_final["main_purpose"].value_counts()
    logger.info("=" * 60)
    logger.info("주용도 정규화 분포:")
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
