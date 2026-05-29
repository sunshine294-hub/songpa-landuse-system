"""
03_load_buildings.py — 건물 데이터 로드 및 필지-건물 매핑
=========================================================
GIS 건물통합정보 SHP, 건축물대장 표제부 Excel, 부속지번 Excel을
결합하여 건물 데이터와 필지-건물 매핑 테이블을 생성한다.

입력:
  - AL_D010_11_20260509.shp            (GIS 건물통합정보, EPSG:5186)
  - 03. 표제부_2026-05-26 15_00_37.xlsx  (건축물대장 표제부)
  - 05. 부속지번_2026-05-27 17_50_45.xlsx (부속지번)

출력:
  - data/interim/buildings.parquet       (GIS 건물 지오메트리 + 속성)
  - data/interim/parcel_building.parquet (PNU ↔ MGM_BLDRGST_PK 매핑)

매핑 우선순위:
  1순위: 부속지번 (MGM_BLDRGST_PK → PNU)
  2순위: GIS 건물 PNU (A2)
  3순위: Spatial join (건물 중심점 → 필지 폴리곤)
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

# ── sys.path 설정 (유틸리티 임포트) ───────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from utils.crs import to_internal

# ── 로깅 설정 ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 경로 설정 ─────────────────────────────────────────────────────
PROJECT_ROOT = SCRIPT_DIR.parent

# 환경 변수 또는 폴백 경로 설정
import os
DATA_SRC_ENV = os.environ.get("DATA_SRC")
if DATA_SRC_ENV:
    DATA_SRC = Path(DATA_SRC_ENV)
else:
    DATA_SRC = Path(r"c:\Users\gangg\antigravity\prom")
    if not DATA_SRC.exists():
        DATA_SRC = PROJECT_ROOT.parent

# 입력 파일
GIS_BLDG_SHP = (
    DATA_SRC
    / "AL_D010_11_20260509_GIS건물통합정보"
    / "AL_D010_11_20260509.shp"
)
PYOJEBU_XLSX = DATA_SRC / "03. 표제부_2026-05-26 15_00_37.xlsx"
BUSOKJIBUN_XLSX = DATA_SRC / "05. 부속지번_2026-05-27 17_50_45.xlsx"

# 필지 Parquet (02_load_parcels.py 출력물, spatial join용)
PARCELS_PARQUET = PROJECT_ROOT / "data" / "interim" / "parcels.parquet"

# 출력 디렉토리
OUT_DIR = PROJECT_ROOT / "data" / "interim"

# 송파구 코드 접두사
SONGPA_PREFIX = "11710"


# =====================================================================
# 1. GIS 건물통합정보 로드
# =====================================================================
def load_gis_buildings() -> gpd.GeoDataFrame:
    """GIS 건물통합정보 SHP를 로드하고 송파구만 필터링한다.

    컬럼 매핑:
      A1 → BD_MGT_SN  (건물관리번호, str 25+)
      A2 → PNU        (str 19)
      A9 → gis_purpose (용도)
      A14 → gis_area   (면적, float)
    """
    logger.info("GIS 건물통합정보 SHP 로드: %s", GIS_BLDG_SHP)
    if not GIS_BLDG_SHP.exists():
        raise FileNotFoundError(f"GIS 건물 SHP 파일 없음: {GIS_BLDG_SHP}")

    gdf = gpd.read_file(GIS_BLDG_SHP, encoding="euc-kr")
    logger.info("  전체 레코드: %d, CRS: %s", len(gdf), gdf.crs)

    # ID/코드 컬럼 str 보장
    gdf["A1"] = gdf["A1"].astype(str)
    gdf["A2"] = gdf["A2"].astype(str)

    # 송파구 필터 (A2=PNU가 '11710'으로 시작)
    mask = gdf["A2"].str.startswith(SONGPA_PREFIX)
    gdf = gdf.loc[mask].copy()
    logger.info("  송파구 필터링: %d건", len(gdf))

    if len(gdf) == 0:
        raise ValueError("송파구 GIS 건물 데이터가 없습니다.")

    # 컬럼 리네임
    rename_map = {
        "A1": "BD_MGT_SN",
        "A2": "PNU",
        "A9": "gis_purpose",
        "A14": "gis_area",
    }
    gdf = gdf.rename(columns=rename_map)

    # gis_area를 float로 변환
    gdf["gis_area"] = pd.to_numeric(gdf["gis_area"], errors="coerce")

    # 지오메트리 유효성 검증
    invalid_count = (~gdf.geometry.is_valid).sum()
    if invalid_count > 0:
        logger.warning("  유효하지 않은 지오메트리 %d건 → buffer(0) 수정", invalid_count)
        gdf["geometry"] = gdf.geometry.buffer(0)

    logger.info("  BD_MGT_SN 예시: %s", gdf["BD_MGT_SN"].iloc[0])
    logger.info("  PNU 예시: %s", gdf["PNU"].iloc[0])

    return gdf


# =====================================================================
# 2. 건축물대장 표제부 로드
# =====================================================================
def load_pyojebu() -> pd.DataFrame:
    """건축물대장 표제부 Excel을 로드하고 송파구를 필터링한다.

    모든 컬럼을 dtype=str로 읽어 선행 0을 보존한 뒤,
    숫자 컬럼만 별도로 float 변환한다.
    """
    logger.info("표제부 Excel 로드: %s", PYOJEBU_XLSX)
    if not PYOJEBU_XLSX.exists():
        raise FileNotFoundError(f"표제부 Excel 파일 없음: {PYOJEBU_XLSX}")

    # dtype=str로 읽어 모든 값의 선행 0 보존
    df = pd.read_excel(PYOJEBU_XLSX, dtype=str)
    logger.info("  전체 레코드: %d, 컬럼 수: %d", len(df), len(df.columns))

    # 컬럼명 확인 로그
    logger.info("  컬럼 목록 (처음 10개): %s", list(df.columns[:10]))

    # 송파구 필터: '시군구코드' starts with '11710'
    # dtype=str로 읽었으므로 str.startswith 바로 사용
    mask_sgg = df["시군구코드"].str.startswith(SONGPA_PREFIX)
    df = df.loc[mask_sgg].copy()
    logger.info("  시군구코드 필터 (%s*): %d건", SONGPA_PREFIX, len(df))

    # 대장구분코드 필터: '1' (일반 = 주 표제부)
    mask_type = df["대장구분코드"] == "1"
    df = df.loc[mask_type].copy()
    logger.info("  대장구분코드='1'(일반) 필터: %d건", len(df))

    if len(df) == 0:
        raise ValueError("송파구 표제부 데이터가 없습니다.")

    # 핵심 컬럼 리네임
    rename_map = {
        "관리건축물대장PK": "MGM_BLDRGST_PK",
        "주용도코드명":     "MAIN_PURPS_CD_NM",
        "총동연면적(㎡)":    "TOTAREA",
        "대지면적(㎡)":      "PLAT_AR",
        "건물명":          "BULD_NM",
        "사용승인일":       "USE_APR_DAY",
    }
    df = df.rename(columns=rename_map)

    # MGM_BLDRGST_PK는 str 유지 (dtype=str로 읽었으므로 이미 str)
    logger.info("  MGM_BLDRGST_PK dtype: %s, 예시: %s",
                df["MGM_BLDRGST_PK"].dtype, df["MGM_BLDRGST_PK"].iloc[0])

    # 숫자 컬럼 변환
    df["TOTAREA"] = pd.to_numeric(df["TOTAREA"], errors="coerce")
    df["PLAT_AR"] = pd.to_numeric(df["PLAT_AR"], errors="coerce")

    # 필요한 컬럼만 선택
    cols_keep = [
        "MGM_BLDRGST_PK", "MAIN_PURPS_CD_NM", "TOTAREA",
        "PLAT_AR", "BULD_NM", "USE_APR_DAY",
    ]
    df = df[cols_keep].copy()

    logger.info("  표제부 로드 완료: %d건", len(df))
    return df


# =====================================================================
# 3. 부속지번 로드 및 PNU 생성
# =====================================================================
def load_busokjibun() -> pd.DataFrame:
    """부속지번 Excel에서 MGM_BLDRGST_PK ↔ PNU 매핑을 생성한다.

    PNU 구성:
      시군구코드(5) + 법정동코드(5) + '00' + 대지구분코드(1) + 번(4) + 지(4) = 21자리
      예: 11710 + 10100 + 00 + 0 + 0001 + 0000 = 1171010100001000010000
    """
    logger.info("부속지번 Excel 로드: %s", BUSOKJIBUN_XLSX)
    if not BUSOKJIBUN_XLSX.exists():
        raise FileNotFoundError(f"부속지번 Excel 파일 없음: {BUSOKJIBUN_XLSX}")

    # dtype=str로 읽어 선행 0 보존
    df = pd.read_excel(BUSOKJIBUN_XLSX, dtype=str)
    logger.info("  전체 레코드: %d, 컬럼 수: %d", len(df), len(df.columns))
    logger.info("  컬럼 목록: %s", list(df.columns))

    # 핵심 컬럼 확인
    required_cols = ["관리건축물대장PK", "부속시군구코드", "부속법정동코드",
                     "부속대지구분코드", "부속번", "부속지"]
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"부속지번에 필수 컬럼 '{col}' 없음. 컬럼: {list(df.columns)}")

    # MGM_BLDRGST_PK 리네임
    df = df.rename(columns={"관리건축물대장PK": "MGM_BLDRGST_PK"})

    # PNU 생성: 시군구(5)+법정동(5)+대지구분(1)+번(4)+부(4) = 19자리
    df["PNU"] = (
        df["부속시군구코드"].str.zfill(5)
        + df["부속법정동코드"].str.zfill(5)
        + df["부속대지구분코드"].str.zfill(1)
        + df["부속번"].str.zfill(4)
        + df["부속지"].str.zfill(4)
    )

    logger.info("  PNU 생성 완료. 예시: %s", df["PNU"].iloc[0] if len(df) > 0 else "N/A")
    logger.info("  PNU 길이 분포: %s", df["PNU"].str.len().value_counts().to_dict())

    # MGM_BLDRGST_PK → PNU 매핑 (1:N 가능 — 하나의 건물이 여러 필지에 걸침)
    mapping = df[["MGM_BLDRGST_PK", "PNU"]].drop_duplicates()
    logger.info("  부속지번 매핑: %d건 (유니크)", len(mapping))

    return mapping


# =====================================================================
# 4. 3-Priority 매핑 빌드
# =====================================================================
def build_parcel_building_mapping(
    gdf_bldg: gpd.GeoDataFrame,
    df_pyojebu: pd.DataFrame,
    df_busok_map: pd.DataFrame,
) -> pd.DataFrame:
    """필지-건물 매핑 테이블을 3단계 우선순위로 생성한다.

    Priority 1: 부속지번 매핑 (MGM_BLDRGST_PK → PNU)
    Priority 2: GIS 건물 PNU (A2 → PNU)
    Priority 3: Spatial join (건물 중심점 → 필지 폴리곤)

    Parameters
    ----------
    gdf_bldg : GeoDataFrame
        GIS 건물 데이터 (BD_MGT_SN, PNU, geometry 포함)
    df_pyojebu : DataFrame
        표제부 데이터 (MGM_BLDRGST_PK, MAIN_PURPS_CD_NM 등)
    df_busok_map : DataFrame
        부속지번 매핑 (MGM_BLDRGST_PK, PNU)

    Returns
    -------
    DataFrame
        매핑 테이블 (PNU, MGM_BLDRGST_PK, match_method, + 표제부 속성)
    """
    logger.info("필지-건물 매핑 빌드 (3-priority)")

    # 표제부의 모든 MGM_BLDRGST_PK 목록
    all_pk = set(df_pyojebu["MGM_BLDRGST_PK"].unique())
    logger.info("  표제부 건물 수: %d", len(all_pk))

    results = []
    matched_pks: set[str] = set()

    # ── Priority 1: 부속지번 매핑 ─────────────────────────────────
    logger.info("  [P1] 부속지번 매핑 적용")
    p1 = df_busok_map.merge(
        df_pyojebu, on="MGM_BLDRGST_PK", how="inner"
    )
    p1["match_method"] = 1
    matched_pks.update(p1["MGM_BLDRGST_PK"].unique())
    results.append(p1)
    logger.info("    P1 매칭: %d건 (%d 유니크 PK)",
                len(p1), p1["MGM_BLDRGST_PK"].nunique())

    # ── Priority 2: GIS 건물 PNU ──────────────────────────────────
    logger.info("  [P2] GIS 건물 PNU 매핑")
    # GIS 건물의 BD_MGT_SN 25자리 중 일부가 MGM_BLDRGST_PK와 매칭될 수 있음
    # 표제부와 GIS를 PNU 기반으로 연결
    remaining_pk = all_pk - matched_pks
    logger.info("    P1 이후 미매칭 PK: %d건", len(remaining_pk))

    if remaining_pk:
        df_remaining = df_pyojebu[
            df_pyojebu["MGM_BLDRGST_PK"].isin(remaining_pk)
        ].copy()

        # GIS 건물에서 PNU별 대표 건물 추출 (가장 큰 gis_area 기준)
        gis_pnu = gdf_bldg[["PNU", "BD_MGT_SN", "gis_area"]].copy()
        gis_pnu = gis_pnu.drop_duplicates(subset=["PNU"])

        # BD_MGT_SN → MGM_BLDRGST_PK 매핑 시도
        # BD_MGT_SN이 MGM_BLDRGST_PK를 포함하는 경우
        # GIS의 PNU를 사용하여 부속지번에서 매칭되지 않은 건물 연결
        # 표제부에 PNU가 없으므로, GIS PNU 기반 간접 매핑
        # 부속지번에서 이미 PNU→PK가 있으므로, GIS PNU를 통해 남은 PK 매핑
        busok_pnu_set = set(df_busok_map["PNU"].unique())
        gis_only_pnu = gis_pnu[~gis_pnu["PNU"].isin(busok_pnu_set)]

        # GIS 건물의 PNU로 남은 표제부 건물 매핑
        # 부속지번에 없는 PNU를 가진 GIS 건물 → 해당 PNU의 표제부 매핑
        if len(gis_only_pnu) > 0 and len(df_remaining) > 0:
            # BD_MGT_SN의 앞 자리가 MGM_BLDRGST_PK와 일치하는지 확인
            gis_pk_map = gdf_bldg[["BD_MGT_SN", "PNU"]].copy()
            gis_pk_map = gis_pk_map.rename(columns={"BD_MGT_SN": "GIS_BD_MGT_SN"})

            # MGM_BLDRGST_PK로 직접 매핑 시도
            # 고성능 해시 기반 접두사 검색 적용
            remaining_set = set(str(pk) for pk in remaining_pk)
            pk_lengths = sorted(list(set(len(str(pk)) for pk in remaining_pk)))

            p2_matches = []
            for _, gis_row in gdf_bldg.iterrows():
                sn = str(gis_row["BD_MGT_SN"])
                pnu = gis_row["PNU"]
                for l in pk_lengths:
                    if len(sn) >= l:
                        prefix = sn[:l]
                        if prefix in remaining_set:
                            p2_matches.append({
                                "MGM_BLDRGST_PK": prefix,
                                "PNU": pnu,
                            })

            if p2_matches:
                p2_df = pd.DataFrame(p2_matches).drop_duplicates()
                p2 = p2_df.merge(df_pyojebu, on="MGM_BLDRGST_PK", how="inner")
                p2["match_method"] = 2
                matched_pks.update(p2["MGM_BLDRGST_PK"].unique())
                results.append(p2)
                logger.info("    P2 매칭: %d건 (%d 유니크 PK)",
                            len(p2), p2["MGM_BLDRGST_PK"].nunique())
            else:
                logger.info("    P2 매칭: 0건")
    else:
        logger.info("    P2 스킵 (P1에서 모두 매칭됨)")

    # ── Priority 3: Spatial Join ──────────────────────────────────
    remaining_pk = all_pk - matched_pks
    logger.info("  [P3] Spatial Join (미매칭 PK: %d건)", len(remaining_pk))

    if remaining_pk and PARCELS_PARQUET.exists():
        df_remaining = df_pyojebu[
            df_pyojebu["MGM_BLDRGST_PK"].isin(remaining_pk)
        ].copy()

        # 필지 지오메트리 로드
        gdf_parcels = gpd.read_parquet(PARCELS_PARQUET)
        logger.info("    필지 데이터 로드: %d건", len(gdf_parcels))

        # GIS 건물과 표제부 PK 매핑이 안 된 건물의 중심점으로 spatial join
        # 고성능 해시 기반 접두사 검색 적용
        remaining_set = set(str(pk) for pk in remaining_pk)
        pk_lengths = sorted(list(set(len(str(pk)) for pk in remaining_pk)))

        remaining_gis = []
        matched_pk_in_gis = set()
        for _, gis_row in gdf_bldg.iterrows():
            sn = str(gis_row["BD_MGT_SN"])
            for l in pk_lengths:
                if len(sn) >= l:
                    prefix = sn[:l]
                    if prefix in remaining_set and prefix not in matched_pk_in_gis:
                        row = gis_row.copy()
                        row["MGM_BLDRGST_PK"] = prefix
                        remaining_gis.append(row)
                        matched_pk_in_gis.add(prefix)

        if remaining_gis:
            gdf_remaining = gpd.GeoDataFrame(remaining_gis, crs=gdf_bldg.crs)

            # 건물 중심점 생성
            gdf_centroids = gdf_remaining.copy()
            gdf_centroids["geometry"] = gdf_centroids.geometry.centroid

            # 좌표계 통일 (필지와 건물 모두 동일 CRS로)
            if gdf_centroids.crs != gdf_parcels.crs:
                gdf_centroids = gdf_centroids.to_crs(gdf_parcels.crs)

            # Spatial join: 건물 중심점이 포함된 필지 찾기
            sj = gpd.sjoin(
                gdf_centroids[["MGM_BLDRGST_PK", "geometry"]],
                gdf_parcels[["PNU", "geometry"]],
                how="left",
                predicate="within",
            )

            p3 = sj[sj["PNU"].notna()][["MGM_BLDRGST_PK", "PNU"]].copy()
            p3 = p3.drop_duplicates()
            p3 = p3.merge(df_pyojebu, on="MGM_BLDRGST_PK", how="inner")
            p3["match_method"] = 3
            matched_pks.update(p3["MGM_BLDRGST_PK"].unique())
            results.append(p3)
            logger.info("    P3 매칭: %d건 (%d 유니크 PK)",
                        len(p3), p3["MGM_BLDRGST_PK"].nunique())
        else:
            logger.info("    P3: GIS 건물 매칭 대상 없음")
    elif not PARCELS_PARQUET.exists():
        logger.warning("    P3 스킵: 필지 Parquet 없음 (%s). 02_load_parcels.py를 먼저 실행하세요.",
                       PARCELS_PARQUET)
    else:
        logger.info("    P3 스킵 (이미 모두 매칭됨)")

    # ── 결과 합산 ─────────────────────────────────────────────────
    final_remaining = all_pk - matched_pks
    logger.info("  최종 미매칭 PK: %d건", len(final_remaining))

    if results:
        df_mapping = pd.concat(results, ignore_index=True)
    else:
        df_mapping = pd.DataFrame(columns=[
            "PNU", "MGM_BLDRGST_PK", "MAIN_PURPS_CD_NM",
            "TOTAREA", "PLAT_AR", "BULD_NM", "USE_APR_DAY", "match_method",
        ])

    # 모든 ID 컬럼 str 보장
    df_mapping["PNU"] = df_mapping["PNU"].astype(str)
    df_mapping["MGM_BLDRGST_PK"] = df_mapping["MGM_BLDRGST_PK"].astype(str)
    df_mapping["match_method"] = df_mapping["match_method"].astype(int)

    return df_mapping


# =====================================================================
# 메인
# =====================================================================
def main() -> None:
    """메인 실행 함수."""
    logger.info("=" * 60)
    logger.info("03_load_buildings.py 시작")
    logger.info("=" * 60)

    # 출력 디렉토리 생성
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1) GIS 건물통합정보 로드 ──────────────────────────────────
    gdf_bldg = load_gis_buildings()

    # ── 2) 표제부 로드 ────────────────────────────────────────────
    df_pyojebu = load_pyojebu()

    # ── 3) 부속지번 로드 → PNU 매핑 ──────────────────────────────
    df_busok_map = load_busokjibun()

    # ── 4) 3-Priority 매핑 빌드 ───────────────────────────────────
    df_mapping = build_parcel_building_mapping(
        gdf_bldg, df_pyojebu, df_busok_map
    )

    # ── 5) 매핑 통계 ──────────────────────────────────────────────
    logger.info("매핑 방법별 분포:")
    method_dist = df_mapping["match_method"].value_counts().sort_index()
    method_labels = {1: "부속지번", 2: "GIS PNU", 3: "Spatial Join"}
    for method, cnt in method_dist.items():
        label = method_labels.get(method, f"Unknown({method})")
        pct = cnt / len(df_mapping) * 100 if len(df_mapping) > 0 else 0
        logger.info("  %d (%s): %d건 (%.1f%%)", method, label, cnt, pct)

    # 주용도 분포 (상위 10개)
    if "MAIN_PURPS_CD_NM" in df_mapping.columns:
        purpose_dist = df_mapping["MAIN_PURPS_CD_NM"].value_counts().head(10)
        logger.info("주용도 분포 (상위 10개):")
        for purpose, cnt in purpose_dist.items():
            logger.info("  %s: %d건", purpose, cnt)

    # ── 6) 저장 ───────────────────────────────────────────────────
    # 6a) GIS 건물 지오메트리 + 속성
    out_bldg = OUT_DIR / "buildings.parquet"
    gdf_bldg.to_parquet(out_bldg)
    logger.info("저장 완료: %s (%d건)", out_bldg, len(gdf_bldg))

    # 6b) 필지-건물 매핑 테이블
    out_map = OUT_DIR / "parcel_building.parquet"
    df_mapping.to_parquet(out_map, index=False)
    logger.info("저장 완료: %s (%d건)", out_map, len(df_mapping))

    logger.info("=" * 60)
    logger.info("03_load_buildings.py 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("치명적 오류 발생")
        sys.exit(1)
