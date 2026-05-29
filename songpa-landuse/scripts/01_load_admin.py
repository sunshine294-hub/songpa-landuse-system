"""
01_load_admin.py — 행정동 경계 데이터 로드 및 전처리
=====================================================
읍면동(UMD) 행정경계 SHP에서 송파구(11710)를 추출하고,
행정동 경계(bnd_dong) SHP도 함께 로드하여 GeoJSON으로 저장한다.

입력:
  - LSMD_ADM_SECT_UMD_11_202605.shp  (EPSG:5186, encoding=euc-kr)
  - bnd_dong_11240_2025_2Q.shp        (EPSG:5179)

출력:
  - data/processed/admin_emd.geojson   (송파구 읍면동 경계, EPSG:4326)
  - data/processed/dong_boundary.geojson (행정동 경계 참조용, EPSG:4326)
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd

# ── 로깅 설정 ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 경로 설정 ─────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_SRC = Path(r"c:\Users\gangg\antigravity\prom")

# 입력 파일
UMD_SHP = (
    DATA_SRC
    / "LSMD_ADM_SECT_UMD_서울"
    / "LSMD_ADM_SECT_UMD_11_202605.shp"
)
DONG_SHP = (
    DATA_SRC
    / "bnd_dong_11240_2025_2Q"
    / "bnd_dong_11240_2025_2Q.shp"
)

# 출력 디렉토리
OUT_DIR = PROJECT_ROOT / "data" / "processed"

# 송파구 코드 접두사
SONGPA_PREFIX = "11710"
EXPECTED_DONG_COUNT = 27


def load_admin_emd() -> gpd.GeoDataFrame:
    """읍면동 행정경계 SHP를 로드하고 송파구만 필터링한다."""
    logger.info("읍면동 SHP 로드: %s", UMD_SHP)
    if not UMD_SHP.exists():
        raise FileNotFoundError(f"UMD SHP 파일 없음: {UMD_SHP}")

    gdf = gpd.read_file(UMD_SHP, encoding="euc-kr")
    logger.info("  전체 레코드: %d, CRS: %s", len(gdf), gdf.crs)
    logger.info("  컬럼: %s", list(gdf.columns))

    # EMD_CD를 str로 확인 (선행 0 보존)
    gdf["EMD_CD"] = gdf["EMD_CD"].astype(str)

    # 송파구 필터 (EMD_CD가 '11710'으로 시작)
    mask = gdf["EMD_CD"].str.startswith(SONGPA_PREFIX)
    gdf_songpa = gdf.loc[mask].copy()
    logger.info("  송파구 필터링: %d건 (EMD_CD startswith '%s')",
                len(gdf_songpa), SONGPA_PREFIX)

    if len(gdf_songpa) == 0:
        raise ValueError("송파구 데이터가 없습니다. EMD_CD 값을 확인하세요.")

    # 컬럼명 변경: EMD_NM → EMD_KOR_NM
    gdf_songpa = gdf_songpa.rename(columns={"EMD_NM": "EMD_KOR_NM"})

    # 지오메트리 유효성 검증 (buffer(0)으로 자가교차 수정)
    invalid_count = (~gdf_songpa.geometry.is_valid).sum()
    if invalid_count > 0:
        logger.warning("  유효하지 않은 지오메트리 %d건 → buffer(0) 수정", invalid_count)
        gdf_songpa["geometry"] = gdf_songpa.geometry.buffer(0)

    # EPSG:5186 → EPSG:4326 변환
    gdf_songpa = gdf_songpa.to_crs("EPSG:4326")
    logger.info("  좌표계 변환 완료: %s", gdf_songpa.crs)

    return gdf_songpa


def load_dong_boundary() -> gpd.GeoDataFrame:
    """행정동 경계 SHP를 로드한다."""
    logger.info("행정동 경계 SHP 로드: %s", DONG_SHP)
    if not DONG_SHP.exists():
        raise FileNotFoundError(f"행정동 경계 SHP 파일 없음: {DONG_SHP}")

    gdf = gpd.read_file(DONG_SHP)
    logger.info("  전체 레코드: %d, CRS: %s", len(gdf), gdf.crs)
    logger.info("  컬럼: %s", list(gdf.columns))

    # 코드 컬럼 str 보장
    gdf["ADM_CD"] = gdf["ADM_CD"].astype(str)
    gdf["BASE_DATE"] = gdf["BASE_DATE"].astype(str)

    # 지오메트리 유효성 검증
    invalid_count = (~gdf.geometry.is_valid).sum()
    if invalid_count > 0:
        logger.warning("  유효하지 않은 지오메트리 %d건 → buffer(0) 수정", invalid_count)
        gdf["geometry"] = gdf.geometry.buffer(0)

    # EPSG:5179 → EPSG:4326 변환
    gdf = gdf.to_crs("EPSG:4326")
    logger.info("  좌표계 변환 완료: %s", gdf.crs)

    return gdf


def main() -> None:
    """메인 실행 함수."""
    logger.info("=" * 60)
    logger.info("01_load_admin.py 시작")
    logger.info("=" * 60)

    # 출력 디렉토리 생성
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1) 읍면동 행정경계 ────────────────────────────────────────
    gdf_emd = load_admin_emd()

    out_emd = OUT_DIR / "admin_emd.geojson"
    gdf_emd.to_file(out_emd, driver="GeoJSON")
    logger.info("저장 완료: %s (%d건)", out_emd, len(gdf_emd))

    # 기대값 확인
    if len(gdf_emd) != EXPECTED_DONG_COUNT:
        logger.warning(
            "⚠️  읍면동 수 불일치: 기대=%d, 실제=%d",
            EXPECTED_DONG_COUNT, len(gdf_emd),
        )
    else:
        logger.info("✅ 읍면동 수 일치: %d건", len(gdf_emd))

    # 동 목록 출력
    logger.info("읍면동 목록:")
    for _, row in gdf_emd.iterrows():
        logger.info("  %s: %s", row["EMD_CD"], row["EMD_KOR_NM"])

    # ── 2) 행정동 경계 (참조용) ───────────────────────────────────
    gdf_dong = load_dong_boundary()

    out_dong = OUT_DIR / "dong_boundary.geojson"
    gdf_dong.to_file(out_dong, driver="GeoJSON")
    logger.info("저장 완료: %s (%d건)", out_dong, len(gdf_dong))

    logger.info("=" * 60)
    logger.info("01_load_admin.py 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("치명적 오류 발생")
        sys.exit(1)
