"""
02_load_parcels.py — 필지(지적) 및 토지특성 데이터 로드
=======================================================
연속지적도(LDREG) SHP와 토지특성(AL_D194) SHP를 PNU 기준으로 결합하고,
용도지역 정규화 및 면적 계산 후 Parquet으로 저장한다.

입력:
  - LSMD_CONT_LDREG_11710_202605.shp  (EPSG:5186, 송파구 필지)
  - AL_D194_11710_20260520.shp         (EPSG:5186, 토지특성, encoding=euc-kr)

출력:
  - data/interim/parcels.parquet       (필지 + 토지특성 결합, EPSG:5186)
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

# ── sys.path 설정 (유틸리티 임포트) ───────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils.normalize import normalize_zone
from utils.crs import to_internal

# ── 로깅 설정 ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 경로 설정 ─────────────────────────────────────────────────────
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_SRC = Path(r"c:\Users\gangg\antigravity\prom")

# 입력 파일
PARCEL_SHP = (
    DATA_SRC
    / "LSMD_CONT_LDREG_서울_송파구"
    / "LSMD_CONT_LDREG_11710_202605.shp"
)
LAND_CHAR_SHP = (
    DATA_SRC
    / "AL_D194_11710_20260520"
    / "AL_D194_11710_20260520.shp"
)

# 출력 디렉토리
OUT_DIR = PROJECT_ROOT / "data" / "interim"

# 기대 필지 수
EXPECTED_PARCEL_RANGE = (31_000, 32_000)


def load_parcels() -> gpd.GeoDataFrame:
    """연속지적도 SHP를 로드한다."""
    logger.info("필지 SHP 로드: %s", PARCEL_SHP)
    if not PARCEL_SHP.exists():
        raise FileNotFoundError(f"필지 SHP 파일 없음: {PARCEL_SHP}")

    gdf = gpd.read_file(PARCEL_SHP)
    logger.info("  레코드 수: %d, CRS: %s", len(gdf), gdf.crs)
    logger.info("  컬럼: %s", list(gdf.columns))

    # PNU를 str로 확인 (선행 0 보존)
    gdf["PNU"] = gdf["PNU"].astype(str)
    logger.info("  PNU 예시: %s", gdf["PNU"].iloc[0] if len(gdf) > 0 else "N/A")

    return gdf


def load_land_characteristics() -> pd.DataFrame:
    """토지특성 SHP를 로드하고 컬럼을 리네임한다.

    Returns
    -------
    DataFrame
        지오메트리 제외, PNU·zone_raw·jimok·plat_area 컬럼 포함
    """
    logger.info("토지특성 SHP 로드: %s", LAND_CHAR_SHP)
    if not LAND_CHAR_SHP.exists():
        raise FileNotFoundError(f"토지특성 SHP 파일 없음: {LAND_CHAR_SHP}")

    gdf = gpd.read_file(LAND_CHAR_SHP, encoding="euc-kr")
    logger.info("  레코드 수: %d, CRS: %s", len(gdf), gdf.crs)
    logger.info("  컬럼: %s", list(gdf.columns))

    # 컬럼 리네임: A1→PNU, A14→zone_raw, A11→jimok, A12→plat_area
    rename_map = {
        "A1": "PNU",
        "A14": "zone_raw",
        "A11": "jimok",
        "A12": "plat_area",
    }
    gdf = gdf.rename(columns=rename_map)

    # PNU를 str로 보장
    gdf["PNU"] = gdf["PNU"].astype(str)

    # 지오메트리 제외하고 DataFrame으로 반환 (필지 SHP의 지오메트리를 사용)
    cols_to_keep = ["PNU", "zone_raw", "jimok", "plat_area"]
    df = pd.DataFrame(gdf[cols_to_keep])

    logger.info("  리네임 후 컬럼: %s", list(df.columns))
    logger.info("  zone_raw 예시: %s", df["zone_raw"].iloc[0] if len(df) > 0 else "N/A")

    return df


def main() -> None:
    """메인 실행 함수."""
    logger.info("=" * 60)
    logger.info("02_load_parcels.py 시작")
    logger.info("=" * 60)

    # 출력 디렉토리 생성
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1) 필지 로드 ──────────────────────────────────────────────
    gdf_parcel = load_parcels()

    # ── 2) 토지특성 로드 ──────────────────────────────────────────
    df_land = load_land_characteristics()

    # ── 3) PNU 기준 Left Join ─────────────────────────────────────
    logger.info("필지 + 토지특성 결합 (PNU left join)")
    gdf_merged = gdf_parcel.merge(df_land, on="PNU", how="left")
    logger.info("  결합 결과: %d건", len(gdf_merged))

    # 토지특성 매칭 통계
    matched = gdf_merged["zone_raw"].notna().sum()
    unmatched = gdf_merged["zone_raw"].isna().sum()
    logger.info("  토지특성 매칭: %d건 (%.1f%%)", matched, matched / len(gdf_merged) * 100)
    logger.info("  토지특성 미매칭: %d건 (%.1f%%)", unmatched, unmatched / len(gdf_merged) * 100)

    # ── 4) 용도지역 정규화 ────────────────────────────────────────
    logger.info("용도지역 정규화 (zone_raw → zone_norm)")
    gdf_merged["zone_norm"] = gdf_merged["zone_raw"].apply(normalize_zone)

    zone_dist = gdf_merged["zone_norm"].value_counts()
    logger.info("  용도지역 분포:")
    for zone, cnt in zone_dist.items():
        logger.info("    %s: %d건", zone, cnt)

    # ── 5) 면적 계산 (EPSG:5179 투영 좌표계) ──────────────────────
    logger.info("면적 계산 (EPSG:5179)")
    gdf_5179 = to_internal(gdf_merged)
    gdf_merged["area_m2"] = gdf_5179.geometry.area
    logger.info("  면적 통계: min=%.1f, max=%.1f, mean=%.1f m²",
                gdf_merged["area_m2"].min(),
                gdf_merged["area_m2"].max(),
                gdf_merged["area_m2"].mean())

    # ── 6) 저장 ───────────────────────────────────────────────────
    out_path = OUT_DIR / "parcels.parquet"
    gdf_merged.to_parquet(out_path)
    logger.info("저장 완료: %s (%d건)", out_path, len(gdf_merged))

    # 기대값 확인
    lo, hi = EXPECTED_PARCEL_RANGE
    if lo <= len(gdf_merged) <= hi:
        logger.info("✅ 필지 수 범위 확인: %d건 (기대: %d~%d)", len(gdf_merged), lo, hi)
    else:
        logger.warning(
            "⚠️  필지 수 범위 이탈: %d건 (기대: %d~%d)",
            len(gdf_merged), lo, hi,
        )

    logger.info("=" * 60)
    logger.info("02_load_parcels.py 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("치명적 오류 발생")
        sys.exit(1)
