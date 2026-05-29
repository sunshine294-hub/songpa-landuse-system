# -*- coding: utf-8 -*-
"""
00_check_env.py — 개발 및 실행 환경 유효성 진단
==============================================
필요한 Python 라이브러리와 외부 의존성(tippecanoe 등)이 정상적으로
설치되어 있는지 진단하고 시스템 사양을 확인한다.
"""
import sys
import shutil
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_LIBS = [
    "geopandas",
    "shapely",
    "pyproj",
    "pandas",
    "pyarrow",
    "lxml",
    "openpyxl"
]

def main():
    logger.info("=" * 60)
    logger.info("환경 진단 시작 (songpa-landuse)")
    logger.info("=" * 60)
    
    # 1. 파이썬 버전 체크
    logger.info(f"Python 버전: {sys.version}")
    
    # 2. 필수 라이브러리 체크
    missing_libs = []
    for lib in REQUIRED_LIBS:
        try:
            __import__(lib)
            logger.info(f"  [OK] {lib}")
        except ImportError:
            logger.error(f"  [FAIL] {lib}가 설치되어 있지 않습니다.")
            missing_libs.append(lib)
            
    # 3. tippecanoe 설치 여부 확인
    tippecanoe_path = shutil.which("tippecanoe")
    if tippecanoe_path:
        logger.info(f"  [OK] tippecanoe 설치됨: {tippecanoe_path}")
    else:
        logger.warning("  [WARN] tippecanoe를 시스템 PATH에서 찾을 수 없습니다. (PMTiles 타일 생성 시 필요)")
        
    logger.info("=" * 60)
    if missing_libs:
        logger.error(f"진단 실패: 다음 라이브러리를 설치해주세요: pip install {' '.join(missing_libs)}")
        sys.exit(1)
    else:
        logger.info("진단 완료: 모든 필수 라이브러리가 준비되었습니다.")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()
