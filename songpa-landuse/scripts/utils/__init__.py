"""
songpa-landuse 전처리 유틸리티 패키지
======================================

각 모듈의 주요 공개 함수·상수를 패키지 레벨에서 바로 임포트할 수 있다.

    from scripts.utils import to_internal, normalize_zone, read_geojson
"""

# CRS 변환
from .crs import (
    CRS_EXPORT,
    CRS_INTERNAL,
    to_export,
    to_internal,
)

# 용도지역·건축물 용도 정규화
from .normalize import (
    PURPOSE_TOP12,
    ZONE_MAP,
    categorize_purpose,
    normalize_zone,
)

# 파일 I/O
from .io import (
    read_geojson,
    read_parquet,
    write_geojson,
    write_parquet,
)

# 필지-건축물 매칭
from .join import (
    build_parcel_building_map,
)

__all__ = [
    # crs
    "CRS_INTERNAL",
    "CRS_EXPORT",
    "to_internal",
    "to_export",
    # normalize
    "ZONE_MAP",
    "normalize_zone",
    "PURPOSE_TOP12",
    "categorize_purpose",
    # io
    "read_geojson",
    "write_geojson",
    "read_parquet",
    "write_parquet",
    # join
    "build_parcel_building_map",
]
