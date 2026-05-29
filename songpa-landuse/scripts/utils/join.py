"""
필지–건축물 매칭 유틸리티 (3단계 우선순위)
============================================

건축물대장의 건물과 토지(연속지적도) 필지를 연결한다.
세 가지 방법을 우선순위 순서대로 적용하여 매칭률을 극대화한다.

  1순위: 부속지번 매핑 (MGM_BLDRGST_PK ↔ PNU 직접 연결)
  2순위: GIS건물통합정보 BD_MGT_SN 매칭
  3순위: Spatial Join (건물 centroid → 필지 polygon)
"""
from __future__ import annotations

import logging
from typing import Optional

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)

# 최종 출력 컬럼 (순서 보장)
OUTPUT_COLUMNS: list[str] = [
    "PNU",
    "MGM_BLDRGST_PK",
    "main_purpose",
    "building_name",
    "match_method",
    "PLAT_AR",
    "TOTAREA",
]


def _ensure_str_keys(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """주어진 컬럼들을 문자열(str)로 변환한다.

    PNU·관리번호 등 코드 컬럼의 선행 0 보존을 위해 필수적이다.
    """
    for col in cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df


# ---------------------------------------------------------------------------
# 1순위: 부속지번 매핑
# ---------------------------------------------------------------------------

def _match_by_jibun(
    buildings: pd.DataFrame,
    jibun_mapping: pd.DataFrame,
) -> pd.DataFrame:
    """부속지번 테이블을 이용한 직접 PNU 매핑.

    건축물대장 총괄표제부의 MGM_BLDRGST_PK와
    부속지번(전유부) 테이블의 PNU를 1:1 연결한다.

    Parameters
    ----------
    buildings : pd.DataFrame
        건축물 데이터. ``MGM_BLDRGST_PK`` 컬럼 필요.
    jibun_mapping : pd.DataFrame
        부속지번 매핑 테이블. ``MGM_BLDRGST_PK``, ``PNU`` 컬럼 필요.

    Returns
    -------
    pd.DataFrame
        매칭된 행. ``match_method=1`` 컬럼 포함.
    """
    logger.info("[1순위] 부속지번 매핑 시작 (건물 %d건)", len(buildings))

    jibun_mapping = _ensure_str_keys(jibun_mapping, ["MGM_BLDRGST_PK", "PNU"])

    # 부속지번 기준으로 대표 PNU 1건만 취함 (중복 방지)
    jibun_unique = (
        jibun_mapping[["MGM_BLDRGST_PK", "PNU"]]
        .drop_duplicates(subset=["MGM_BLDRGST_PK"])
    )

    matched = buildings.merge(
        jibun_unique,
        on="MGM_BLDRGST_PK",
        how="inner",
    )
    matched["match_method"] = 1

    logger.info("  → 1순위 매칭: %d건", len(matched))
    return matched


# ---------------------------------------------------------------------------
# 2순위: GIS건물통합정보 BD_MGT_SN 매칭
# ---------------------------------------------------------------------------

def _match_by_bd_mgt_sn(
    unmatched_buildings: pd.DataFrame,
    title_df: pd.DataFrame,
    parcels: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """GIS건물통합정보의 BD_MGT_SN을 이용한 매칭.

    표제부(title_df)에서 BD_MGT_SN으로 대지위치 PNU를 추출하고,
    필지 데이터와 교차 확인하여 매칭한다.

    BD_MGT_SN 앞 19자리가 대지위치 PNU에 해당한다.

    Parameters
    ----------
    unmatched_buildings : pd.DataFrame
        1순위에서 매칭되지 않은 건물.
    title_df : pd.DataFrame
        총괄표제부 / 표제부. ``MGM_BLDRGST_PK``, ``BD_MGT_SN`` 컬럼 필요.
    parcels : gpd.GeoDataFrame
        필지(연속지적도). ``PNU`` 컬럼 필요.

    Returns
    -------
    pd.DataFrame
        매칭된 행. ``match_method=2`` 컬럼 포함.
    """
    logger.info("[2순위] BD_MGT_SN 매칭 시작 (미매칭 건물 %d건)", len(unmatched_buildings))

    title_df = _ensure_str_keys(title_df, ["MGM_BLDRGST_PK", "BD_MGT_SN"])

    # BD_MGT_SN 앞 19자리 → 대지위치 PNU로 활용
    title_with_pnu = title_df[["MGM_BLDRGST_PK", "BD_MGT_SN"]].copy()
    title_with_pnu["PNU"] = title_with_pnu["BD_MGT_SN"].str[:19]

    # 유효한 PNU만 필터 (실제 필지 목록과 교차)
    valid_pnus = set(parcels["PNU"].astype(str).unique())
    title_with_pnu = title_with_pnu[title_with_pnu["PNU"].isin(valid_pnus)]

    # 대표 1건만 취함
    title_unique = title_with_pnu[["MGM_BLDRGST_PK", "PNU"]].drop_duplicates(
        subset=["MGM_BLDRGST_PK"]
    )

    matched = unmatched_buildings.merge(
        title_unique,
        on="MGM_BLDRGST_PK",
        how="inner",
    )
    matched["match_method"] = 2

    logger.info("  → 2순위 매칭: %d건", len(matched))
    return matched


# ---------------------------------------------------------------------------
# 3순위: Spatial Join (centroid → polygon)
# ---------------------------------------------------------------------------

def _match_by_spatial_join(
    unmatched_buildings: gpd.GeoDataFrame,
    parcels: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """건물 중심점(centroid)과 필지 폴리곤의 공간 조인.

    앞 두 단계에서 매칭되지 않은 건물에 대해
    geometry 기반으로 소속 필지를 찾는다.

    Parameters
    ----------
    unmatched_buildings : gpd.GeoDataFrame
        1·2순위 미매칭 건물. geometry 컬럼 필요.
    parcels : gpd.GeoDataFrame
        필지 폴리곤. ``PNU`` 컬럼과 geometry 필요.

    Returns
    -------
    pd.DataFrame
        매칭된 행. ``match_method=3`` 컬럼 포함.
    """
    logger.info("[3순위] Spatial Join 시작 (미매칭 건물 %d건)", len(unmatched_buildings))

    if unmatched_buildings.empty:
        logger.info("  → 미매칭 건물 없음 — 건너뜀")
        return pd.DataFrame(columns=unmatched_buildings.columns.tolist() + ["PNU"])

    # 건물 centroid 생성
    bldg_points = unmatched_buildings.copy()
    bldg_points["geometry"] = bldg_points.geometry.centroid

    # CRS 통일
    if bldg_points.crs != parcels.crs:
        logger.debug("CRS 통일: 건물 → 필지 CRS(%s)", parcels.crs)
        bldg_points = bldg_points.to_crs(parcels.crs)

    # Spatial join (point in polygon)
    joined = gpd.sjoin(
        bldg_points,
        parcels[["PNU", "geometry"]],
        how="inner",
        predicate="within",
    )

    # 중복 제거: 한 건물이 여러 필지에 걸치면 첫 번째만 취함
    joined = joined.drop_duplicates(subset=["MGM_BLDRGST_PK"])
    joined["match_method"] = 3

    # sjoin이 추가한 index_right 컬럼 정리
    if "index_right" in joined.columns:
        joined = joined.drop(columns=["index_right"])

    logger.info("  → 3순위 매칭: %d건", len(joined))
    return joined


# ---------------------------------------------------------------------------
# 통합 매칭 함수
# ---------------------------------------------------------------------------

def build_parcel_building_map(
    parcels_gdf: gpd.GeoDataFrame,
    buildings_gdf: gpd.GeoDataFrame,
    jibun_mapping_df: pd.DataFrame,
    title_df: pd.DataFrame,
    plat_ar_col: str = "PLAT_AR",
    totarea_col: str = "TOTAREA",
    purpose_col: str = "MAIN_PURPS_CD_NM",
    name_col: str = "BLD_NM",
) -> pd.DataFrame:
    """필지-건축물 매칭을 3단계 우선순위로 수행한다.

    Parameters
    ----------
    parcels_gdf : gpd.GeoDataFrame
        연속지적도 필지. ``PNU``, ``geometry`` 컬럼 필수.
    buildings_gdf : gpd.GeoDataFrame
        건축물 정보. ``MGM_BLDRGST_PK``, ``geometry`` 컬럼 필수.
    jibun_mapping_df : pd.DataFrame
        부속지번 매핑 테이블. ``MGM_BLDRGST_PK``, ``PNU`` 컬럼 필수.
    title_df : pd.DataFrame
        총괄표제부 / 표제부. ``MGM_BLDRGST_PK``, ``BD_MGT_SN`` 컬럼 필수.
    plat_ar_col : str
        대지면적 컬럼명 (기본: ``PLAT_AR``).
    totarea_col : str
        연면적 컬럼명 (기본: ``TOTAREA``).
    purpose_col : str
        주용도 컬럼명 (기본: ``MAIN_PURPS_CD_NM``).
    name_col : str
        건물명 컬럼명 (기본: ``BLD_NM``).

    Returns
    -------
    pd.DataFrame
        컬럼: ``PNU``, ``MGM_BLDRGST_PK``, ``main_purpose``,
        ``building_name``, ``match_method`` (1|2|3),
        ``PLAT_AR``, ``TOTAREA``.

    Notes
    -----
    - 모든 코드/ID 컬럼은 ``str`` 타입으로 보존된다 (선행 0 유지).
    - 우선순위가 높은 방법의 결과가 낮은 방법보다 우선한다.
    """
    logger.info(
        "=== 필지-건축물 매칭 시작: 필지 %d건, 건물 %d건 ===",
        len(parcels_gdf),
        len(buildings_gdf),
    )

    # 코드 컬럼 문자열 변환
    parcels_gdf = _ensure_str_keys(
        parcels_gdf.copy(), ["PNU"]
    )
    buildings_gdf = _ensure_str_keys(
        buildings_gdf.copy(), ["MGM_BLDRGST_PK"]
    )

    # 건물 데이터에서 필요 컬럼 추출
    bldg_cols = ["MGM_BLDRGST_PK"]
    if purpose_col in buildings_gdf.columns:
        bldg_cols.append(purpose_col)
    if name_col in buildings_gdf.columns:
        bldg_cols.append(name_col)
    if plat_ar_col in buildings_gdf.columns:
        bldg_cols.append(plat_ar_col)
    if totarea_col in buildings_gdf.columns:
        bldg_cols.append(totarea_col)
    if "geometry" in buildings_gdf.columns:
        bldg_cols.append("geometry")

    buildings_slim = buildings_gdf[list(dict.fromkeys(bldg_cols))].copy()

    # --- 1순위: 부속지번 ---
    m1 = _match_by_jibun(buildings_slim, jibun_mapping_df)
    matched_pks = set(m1["MGM_BLDRGST_PK"])

    # --- 2순위: BD_MGT_SN ---
    unmatched_2 = buildings_slim[~buildings_slim["MGM_BLDRGST_PK"].isin(matched_pks)]
    m2 = _match_by_bd_mgt_sn(unmatched_2, title_df, parcels_gdf)
    matched_pks.update(m2["MGM_BLDRGST_PK"])

    # --- 3순위: Spatial Join ---
    unmatched_3 = buildings_slim[~buildings_slim["MGM_BLDRGST_PK"].isin(matched_pks)]
    # Spatial join을 위해 GeoDataFrame으로 변환
    if not isinstance(unmatched_3, gpd.GeoDataFrame) and "geometry" in unmatched_3.columns:
        unmatched_3 = gpd.GeoDataFrame(unmatched_3, geometry="geometry", crs=buildings_gdf.crs)
    elif isinstance(unmatched_3, gpd.GeoDataFrame):
        pass  # 이미 GeoDataFrame
    else:
        logger.warning("3순위 Spatial Join 불가 — geometry 컬럼 없음")
        unmatched_3 = gpd.GeoDataFrame()

    m3 = _match_by_spatial_join(unmatched_3, parcels_gdf) if not unmatched_3.empty else pd.DataFrame()

    # --- 결과 병합 ---
    result = pd.concat([m1, m2, m3], ignore_index=True)

    # 컬럼 정리 및 이름 표준화
    rename_map = {}
    if purpose_col in result.columns and purpose_col != "main_purpose":
        rename_map[purpose_col] = "main_purpose"
    if name_col in result.columns and name_col != "building_name":
        rename_map[name_col] = "building_name"
    if rename_map:
        result = result.rename(columns=rename_map)

    # 누락 컬럼 보완
    for col in OUTPUT_COLUMNS:
        if col not in result.columns:
            result[col] = None

    result = result[OUTPUT_COLUMNS].copy()

    # 최종 타입 보정
    result["PNU"] = result["PNU"].astype(str)
    result["MGM_BLDRGST_PK"] = result["MGM_BLDRGST_PK"].astype(str)
    result["match_method"] = result["match_method"].astype(int)

    # 통계 로깅
    total = len(result)
    for method in [1, 2, 3]:
        cnt = (result["match_method"] == method).sum()
        pct = cnt / total * 100 if total > 0 else 0
        logger.info("  매칭 방법 %d: %d건 (%.1f%%)", method, cnt, pct)

    unmatched_total = len(buildings_gdf) - total
    logger.info(
        "=== 매칭 완료: %d/%d건 성공, %d건 미매칭 ===",
        total,
        len(buildings_gdf),
        unmatched_total,
    )

    return result
