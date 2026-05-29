"""
CRS (좌표참조계) 변환 유틸리티
===============================

내부 면적 계산용 EPSG:5179 (UTM-K)와
GeoJSON 내보내기용 EPSG:4326 (WGS84) 간 변환.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import geopandas as gpd

logger = logging.getLogger(__name__)

# 내부 분석용 좌표계 (UTM-K, 미터 단위 → 면적 계산에 적합)
CRS_INTERNAL = "EPSG:5179"

# 외부 배포용 좌표계 (WGS84, 경위도 → GeoJSON 표준)
CRS_EXPORT = "EPSG:4326"


def to_internal(gdf: "gpd.GeoDataFrame") -> "gpd.GeoDataFrame":
    """GeoDataFrame을 EPSG:5179 (UTM-K)로 변환한다.

    면적·거리 계산 전에 반드시 호출하여
    미터 단위 좌표계로 통일한다.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        변환 대상 GeoDataFrame. CRS가 설정되어 있어야 한다.

    Returns
    -------
    gpd.GeoDataFrame
        EPSG:5179 좌표계로 변환된 GeoDataFrame.

    Raises
    ------
    ValueError
        입력 GeoDataFrame에 CRS가 설정되어 있지 않은 경우.
    """
    if gdf.crs is None:
        raise ValueError(
            "입력 GeoDataFrame에 CRS가 설정되어 있지 않습니다. "
            "좌표계를 먼저 지정해 주세요."
        )

    src_crs = gdf.crs.to_epsg() or str(gdf.crs)

    if gdf.crs.to_epsg() == 5179:
        logger.debug("이미 EPSG:5179 — 변환 건너뜀")
        return gdf

    logger.info("CRS 변환: %s → %s (UTM-K)", src_crs, CRS_INTERNAL)
    return gdf.to_crs(CRS_INTERNAL)


def to_export(gdf: "gpd.GeoDataFrame") -> "gpd.GeoDataFrame":
    """GeoDataFrame을 EPSG:4326 (WGS84)로 변환한다.

    GeoJSON 파일 내보내기 전에 호출하여
    표준 경위도 좌표계로 통일한다.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        변환 대상 GeoDataFrame. CRS가 설정되어 있어야 한다.

    Returns
    -------
    gpd.GeoDataFrame
        EPSG:4326 좌표계로 변환된 GeoDataFrame.

    Raises
    ------
    ValueError
        입력 GeoDataFrame에 CRS가 설정되어 있지 않은 경우.
    """
    if gdf.crs is None:
        raise ValueError(
            "입력 GeoDataFrame에 CRS가 설정되어 있지 않습니다. "
            "좌표계를 먼저 지정해 주세요."
        )

    src_crs = gdf.crs.to_epsg() or str(gdf.crs)

    if gdf.crs.to_epsg() == 4326:
        logger.debug("이미 EPSG:4326 — 변환 건너뜀")
        return gdf

    logger.info("CRS 변환: %s → %s (WGS84)", src_crs, CRS_EXPORT)
    return gdf.to_crs(CRS_EXPORT)
