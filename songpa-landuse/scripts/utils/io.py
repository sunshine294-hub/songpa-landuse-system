"""
GeoJSON / Parquet 파일 I/O 유틸리티
====================================

GeoDataFrame 읽기·쓰기를 Path 기반으로 래핑하며,
부모 디렉터리 자동 생성·로깅·에러 처리를 제공한다.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import geopandas as gpd

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------

def read_geojson(path: PathLike) -> gpd.GeoDataFrame:
    """GeoJSON 파일을 GeoDataFrame으로 읽는다.

    Parameters
    ----------
    path : str | Path
        읽을 GeoJSON 파일 경로.

    Returns
    -------
    gpd.GeoDataFrame

    Raises
    ------
    FileNotFoundError
        파일이 존재하지 않을 때.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"GeoJSON 파일을 찾을 수 없습니다: {path}")

    logger.info("GeoJSON 읽기: %s", path)
    gdf = gpd.read_file(path, driver="GeoJSON")
    logger.info("  → %d rows, CRS=%s", len(gdf), gdf.crs)
    return gdf


def write_geojson(gdf: gpd.GeoDataFrame, path: PathLike) -> None:
    """GeoDataFrame을 GeoJSON 파일로 저장한다.

    부모 디렉터리가 없으면 자동으로 생성한다.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        저장할 GeoDataFrame.
    path : str | Path
        출력 GeoJSON 파일 경로.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("GeoJSON 쓰기: %s (%d rows)", path, len(gdf))
    gdf.to_file(path, driver="GeoJSON")
    logger.info("  → 저장 완료: %.1f KB", path.stat().st_size / 1024)


# ---------------------------------------------------------------------------
# Parquet (GeoParquet)
# ---------------------------------------------------------------------------

def read_parquet(path: PathLike) -> gpd.GeoDataFrame:
    """GeoParquet 파일을 GeoDataFrame으로 읽는다.

    Parameters
    ----------
    path : str | Path
        읽을 Parquet 파일 경로.

    Returns
    -------
    gpd.GeoDataFrame

    Raises
    ------
    FileNotFoundError
        파일이 존재하지 않을 때.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Parquet 파일을 찾을 수 없습니다: {path}")

    logger.info("Parquet 읽기: %s", path)
    gdf = gpd.read_parquet(path)
    logger.info("  → %d rows, CRS=%s", len(gdf), gdf.crs)
    return gdf


def write_parquet(gdf: gpd.GeoDataFrame, path: PathLike) -> None:
    """GeoDataFrame을 GeoParquet 파일로 저장한다.

    부모 디렉터리가 없으면 자동으로 생성한다.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        저장할 GeoDataFrame.
    path : str | Path
        출력 Parquet 파일 경로.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Parquet 쓰기: %s (%d rows)", path, len(gdf))
    gdf.to_parquet(path)
    logger.info("  → 저장 완료: %.1f KB", path.stat().st_size / 1024)
