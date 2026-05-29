# -*- coding: utf-8 -*-
"""
07_emit_geojson.py — 최종 GeoJSON 내보내기 + frontend 복사
==========================================================

입력:
  - data/interim/parcels_final.parquet
  - data/interim/buildings.parquet

처리:
  1. parcels_final → EPSG:4326 → data/processed/parcels.geojson
     (PNU, JIBUN, zone_norm, main_purpose, area_m2)
  2. buildings → EPSG:4326 → data/processed/buildings.geojson
     (BD_MGT_SN, PNU, gis_purpose, gis_area)
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

from utils.crs import to_export
from utils.io import read_parquet, write_geojson

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

PROJECT_ROOT = SCRIPT_DIR.parent

# 입력
PARCELS_IN = PROJECT_ROOT / "data" / "interim" / "parcels_final.parquet"
BUILDINGS_IN = PROJECT_ROOT / "data" / "interim" / "buildings.parquet"

# 출력 (processed)
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PARCELS_OUT = PROCESSED_DIR / "parcels.geojson"
BUILDINGS_OUT = PROCESSED_DIR / "buildings.geojson"

# 프런트엔드 복사 대상
FRONTEND_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"

# 필지에서 유지할 컬럼
PARCEL_KEEP_COLS = ["PNU", "JIBUN", "zone_norm", "main_purpose", "area_m2", "geometry"]

# 건물에서 유지할 컬럼
BUILDING_KEEP_COLS = ["BD_MGT_SN", "PNU", "gis_purpose", "gis_area", "geometry"]


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

    # ── 2. 건물 GeoJSON 생성 ─────────────────────────────────────────
    logger.info("")
    logger.info("[2/3] 건물 GeoJSON 생성")

    if not BUILDINGS_IN.exists():
        logger.warning("건물 parquet 없음(%s) — 건물 GeoJSON 생성 건너뜀", BUILDINGS_IN)
    else:
        buildings = read_parquet(BUILDINGS_IN)

        # 코드 컬럼 문자열 보장
        for col in ["BD_MGT_SN", "PNU"]:
            if col in buildings.columns:
                buildings[col] = buildings[col].astype(str)

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

    # stats.json (06에서 이미 frontend에 직접 저장하지만,
    # processed에도 사본이 있을 수 있으므로 복사)
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
