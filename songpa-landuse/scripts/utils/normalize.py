# -*- coding: utf-8 -*-
"""
용도지역 정규화 + 건축물 주용도 카테고리 유틸리티
==================================================
"""
import re
import logging

logger = logging.getLogger(__name__)

# ── 용도지역 정규화 매핑 (README §2.5 준수) ─────────────────────
ZONE_MAP: dict[str, str] = {
    "제1종전용주거지역": "1종전용주거", "1종전용": "1종전용주거",
    "제2종전용주거지역": "2종전용주거", "2종전용": "2종전용주거",
    "제1종일반주거지역": "1종일반주거", "1종일반": "1종일반주거",
    "제2종일반주거지역": "2종일반주거", "2종일반": "2종일반주거",
    "제3종일반주거지역": "3종일반주거", "3종일반": "3종일반주거",
    "준주거지역": "준주거",
    "중심상업지역": "중심상업", "일반상업지역": "일반상업",
    "근린상업지역": "근린상업", "유통상업지역": "유통상업",
    "전용공업지역": "전용공업", "일반공업지역": "일반공업",
    "준공업지역": "준공업",
    "보전녹지지역": "보전녹지", "생산녹지지역": "생산녹지",
    "자연녹지지역": "자연녹지",
}

# ── 건축물 주용도 상위 12개 카테고리 (README §2.6) ───────────────
PURPOSE_TOP12 = [
    "공동주택", "단독주택", "제1종근린생활시설", "제2종근린생활시설",
    "업무시설", "교육연구시설", "판매시설", "노유자시설",
    "숙박시설", "문화및집회시설", "자동차관련시설", "공장",
]


def normalize_zone(raw: str | None) -> str:
    """용도지역 원본명을 한글 단축명으로 변환. 매핑 실패 시 '기타'."""
    if raw is None or not isinstance(raw, str):
        return "기타"
    cleaned = re.sub(r"\s+", "", raw.strip())
    if cleaned in ZONE_MAP:
        return ZONE_MAP[cleaned]
    # 부분 매칭
    for key, val in ZONE_MAP.items():
        if cleaned in key or key in cleaned:
            return val
    return "기타"


def categorize_purpose(raw: str | None) -> str:
    """건축물 주용도를 상위 12개 + 기타로 분류."""
    if raw is None or not isinstance(raw, str):
        return "기타"
    cleaned = raw.strip()
    for p in PURPOSE_TOP12:
        if p in cleaned or cleaned in p:
            return p
    return "기타"
