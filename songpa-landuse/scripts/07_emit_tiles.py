# -*- coding: utf-8 -*-
"""
07_emit_tiles.py — PMTiles 벡터 타일 생성 (tippecanoe 활용)
=============================================================

README §5.7 명세에 맞춰 GeoJSON 파일들로부터 대용량 PMTiles 타일을 생성한다.
Windows 등 tippecanoe가 설치되어 있지 않은 환경인 경우 경고와 함께 스킵 처리된다.

입력:
  - data/processed/parcels.geojson
  - data/processed/buildings.geojson

출력:
  - data/processed/parcels.pmtiles
  - data/processed/buildings.pmtiles
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

# ── 로깅 설정 ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 경로 설정 ─────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PARCELS_GEOJSON = PROCESSED_DIR / "parcels.geojson"
BUILDINGS_GEOJSON = PROCESSED_DIR / "buildings.geojson"

PARCELS_PMTILES = PROCESSED_DIR / "parcels.pmtiles"
BUILDINGS_PMTILES = PROCESSED_DIR / "buildings.pmtiles"

FRONTEND_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"


def check_tippecanoe() -> bool:
    """tippecanoe CLI 설치 여부를 진단한다."""
    path = shutil.which("tippecanoe")
    if path:
        logger.info("tippecanoe 탐지됨: %s", path)
        return True
    logger.warning("tippecanoe CLI가 시스템 PATH에 존재하지 않습니다.")
    logger.warning("PMTiles 생성 단계를 건너뜁니다. (GeoJSON 파일들이 직접 렌더링에 사용됩니다)")
    return False


def run_command(cmd: list[str]) -> bool:
    """외부 명령어를 실행한다."""
    logger.info("실행: %s", " ".join(cmd))
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error("명령어 실행 실패: %s", e)
        return False
    except Exception as e:
        logger.error("알 수 없는 에러 발생: %s", e)
        return False


def main() -> None:
    logger.info("=" * 60)
    logger.info("07_emit_tiles.py 시작 (PMTiles 생성)")
    logger.info("=" * 60)

    if not check_tippecanoe():
        logger.info("tippecanoe 미설치로 인해 단계를 완료하지 않고 성공 종료 처리합니다.")
        logger.info("=" * 60)
        return

    # ── 1. parcels.pmtiles 생성 ─────────────────────────────────────
    if PARCELS_GEOJSON.exists():
        logger.info("[1/2] 필지 PMTiles 생성")
        cmd_parcels = [
            "tippecanoe",
            "-o", str(PARCELS_PMTILES),
            "--layer=parcels",
            "--minimum-zoom=11",
            "--maximum-zoom=16",
            "--drop-densest-as-needed",
            "--no-feature-limit",
            "--no-tile-size-limit",
            "--overwrite",
            str(PARCELS_GEOJSON)
        ]
        if run_command(cmd_parcels):
            logger.info("필지 PMTiles 생성 성공: %s", PARCELS_PMTILES)
            # 프런트엔드로 복사
            FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(PARCELS_PMTILES, FRONTEND_DATA_DIR / "parcels.pmtiles")
            logger.info("  프런트엔드로 복사 완료")
    else:
        logger.error("필지 GeoJSON 파일이 없습니다: %s", PARCELS_GEOJSON)

    # ── 2. buildings.pmtiles 생성 ────────────────────────────────────
    if BUILDINGS_GEOJSON.exists():
        logger.info("[2/2] 건물 PMTiles 생성")
        cmd_buildings = [
            "tippecanoe",
            "-o", str(BUILDINGS_PMTILES),
            "--layer=buildings",
            "--minimum-zoom=13",
            "--maximum-zoom=17",
            "--drop-densest-as-needed",
            "--overwrite",
            str(BUILDINGS_GEOJSON)
        ]
        if run_command(cmd_buildings):
            logger.info("건물 PMTiles 생성 성공: %s", BUILDINGS_PMTILES)
            # 프런트엔드로 복사
            FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(BUILDINGS_PMTILES, FRONTEND_DATA_DIR / "buildings.pmtiles")
            logger.info("  프런트엔드로 복사 완료")
    else:
        logger.error("건물 GeoJSON 파일이 없습니다: %s", BUILDINGS_GEOJSON)

    logger.info("=" * 60)
    logger.info("07_emit_tiles.py 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
