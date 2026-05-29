# -*- coding: utf-8 -*-
"""
07_emit_geojson.py — 최종 GeoJSON 내보내기 + frontend 복사 (건물 주용도 포함)
========================================================================

입력:
  - data/interim/parcels_final.parquet
  - data/interim/buildings.parquet
  - data/interim/parcel_building.parquet (건물-대장 매핑 활용)

처리:
  1. parcels_final → EPSG:4326 → data/processed/parcels.geojson
     (PNU, JIBUN, zone_norm, main_purpose, area_m2)
  2. buildings에 대장 매핑을 활용해 'main_purpose' 속성 결합
     → EPSG:4326 → data/processed/buildings.geojson
     (BD_MGT_SN, PNU, gis_purpose, gis_area, main_purpose)
  3. 모든 processed GeoJSON + stats.json → frontend/public/data/ 복사
"""
from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import geopandas as gpd
import pandas as pd

from utils.crs import to_export
from utils.io import read_parquet, write_geojson
from utils.normalize import categorize_purpose

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
PROJECT_ROOT = SCRIPT_DIR.parent

# 입력
PARCELS_IN = PROJECT_ROOT / "data" / "interim" / "parcels_final.parquet"
BUILDINGS_IN = PROJECT_ROOT / "data" / "interim" / "buildings.parquet"
PB_IN = PROJECT_ROOT / "data" / "interim" / "parcel_building.parquet"

# 출력 (processed)
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PARCELS_OUT = PROCESSED_DIR / "parcels.geojson"
BUILDINGS_OUT = PROCESSED_DIR / "buildings.geojson"

# 프런트엔드 복사 대상
FRONTEND_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"

# 필지에서 유지할 컬럼
PARCEL_KEEP_COLS = ["PNU", "JIBUN", "zone_norm", "main_purpose", "area_m2", "geometry"]

# 건물에서 유지할 컬럼 (main_purpose 컬럼을 추가해 스타일링이 작동하도록 보장)
BUILDING_KEEP_COLS = ["BD_MGT_SN", "PNU", "gis_purpose", "gis_area", "main_purpose", "geometry"]


# ---------------------------------------------------------------------------
# 유틸 함수
# ---------------------------------------------------------------------------
def _safe_select_columns(gdf: gpd.GeoDataFrame, cols: list[str]) -> gpd.GeoDataFrame:
    """지정 컬럼 중 실제 존재하는 것만 선택한다."""
    available = [c for c in cols if c in gdf.columns]
    missing = [c for c in cols if c not in gdf.columns and c != "geometry"]
    if missing:
        logger.warning("누락 컬럼 (무시됨): %s", missing)
    return gdf[available].copy()


def _log_file_size(path: Path) -> None:
    """파일 크기를 로깅한다."""
    if path.exists():
        size_mb = path.stat().st_size / (1024 * 1024)
        logger.info("  %s: %.2f MB", path.name, size_mb)


def _copy_to_frontend(src: Path, dst_dir: Path) -> None:
    """파일을 프런트엔드 data 디렉터리로 복사한다."""
    if not src.exists():
        logger.warning("복사 대상 파일 없음: %s", src)
        return

    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    logger.info("  복사: %s → %s", src.name, dst)


# ---------------------------------------------------------------------------
# 메인 처리
# ---------------------------------------------------------------------------
def main() -> None:
    """GeoJSON 내보내기 및 frontend 복사."""

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. 필지 GeoJSON 생성 ─────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("[1/3] 필지 GeoJSON 생성")

    if not PARCELS_IN.exists():
        raise FileNotFoundError(f"필지 parquet 파일 없음: {PARCELS_IN}")

    parcels = read_parquet(PARCELS_IN)
    parcels["PNU"] = parcels["PNU"].astype(str)

    # 필요 컬럼만 유지
    parcels = _safe_select_columns(parcels, PARCEL_KEEP_COLS)

    # EPSG:4326 변환
    parcels = to_export(parcels)

    # GeoJSON 저장
    write_geojson(parcels, PARCELS_OUT)
    _log_file_size(PARCELS_OUT)

    # ── 2. 건물 GeoJSON 생성 (대장 주용도 병합) ────────────────────────
    logger.info("")
    logger.info("[2/3] 건물 GeoJSON 생성 (주용도 병합)")

    if not BUILDINGS_IN.exists():
        logger.warning("건물 parquet 없음(%s) — 건물 GeoJSON 생성 건너뜀", BUILDINGS_IN)
    else:
        buildings = read_parquet(BUILDINGS_IN)

        # 코드 컬럼 문자열 보장
        for col in ["BD_MGT_SN", "PNU"]:
            if col in buildings.columns:
                buildings[col] = buildings[col].astype(str)

        # 대장 매핑 정보와 조인하여 main_purpose 산출
        if PB_IN.exists():
            pb = pd.read_parquet(PB_IN)
            pb["MGM_BLDRGST_PK"] = pb["MGM_BLDRGST_PK"].astype(str)
            pb_slim = pb[["MGM_BLDRGST_PK", "MAIN_PURPS_CD_NM"]].drop_duplicates(subset=["MGM_BLDRGST_PK"], keep="first")
            
            # BD_MGT_SN 앞 25자리를 키로 조인 시도
            buildings["_pk_candidate"] = buildings["BD_MGT_SN"].str[:25]
            buildings = buildings.merge(pb_slim, left_on="_pk_candidate", right_on="MGM_BLDRGST_PK", how="left")
            
            # 주용도 결정: 대장 주용도(MAIN_PURPS_CD_NM) -> 없으면 GIS 용도(gis_purpose) -> 범주화
            buildings["raw_purpose"] = buildings["MAIN_PURPS_CD_NM"].fillna(buildings["gis_purpose"])
            buildings["main_purpose"] = buildings["raw_purpose"].apply(categorize_purpose).fillna("기타")
            
            buildings = buildings.drop(columns=["_pk_candidate", "MGM_BLDRGST_PK", "MAIN_PURPS_CD_NM", "raw_purpose"], errors="ignore")
            logger.info("  건물 주용도 정규화 완료")
        else:
            logger.warning("  PB 매핑 파일 없음. gis_purpose만으로 main_purpose 부여")
            buildings["main_purpose"] = buildings["gis_purpose"].apply(categorize_purpose).fillna("기타")

        # 필요 컬럼만 유지
        buildings = _safe_select_columns(buildings, BUILDING_KEEP_COLS)

        # EPSG:4326 변환
        buildings = to_export(buildings)

        # GeoJSON 저장
        write_geojson(buildings, BUILDINGS_OUT)
        _log_file_size(BUILDINGS_OUT)

    # ── 3. 프런트엔드 복사 ───────────────────────────────────────────
    logger.info("")
    logger.info("[3/3] 프런트엔드 data/ 복사")

    # processed 디렉터리의 모든 GeoJSON
    for geojson_path in PROCESSED_DIR.glob("*.geojson"):
        _copy_to_frontend(geojson_path, FRONTEND_DATA_DIR)

    # stats.json 복사 상태 점검
    stats_json = FRONTEND_DATA_DIR / "stats.json"
    if stats_json.exists():
        logger.info("  stats.json 이미 존재: %.2f MB",
                     stats_json.stat().st_size / (1024 * 1024))

    # ── 4. 최종 요약 ────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("최종 파일 크기:")
    for f in sorted(FRONTEND_DATA_DIR.glob("*")):
        if f.is_file():
            size_mb = f.stat().st_size / (1024 * 1024)
            logger.info("  %s: %.2f MB", f.name, size_mb)
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    main()
