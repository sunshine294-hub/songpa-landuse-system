# -*- coding: utf-8 -*-
"""
run_all.py — 전처리 파이프라인 일괄 실행 (01 → 07) (Windows CP949 호환버전)
========================================================================

Python 스크립트로 작성된 일괄 실행기.
subprocess.run()으로 각 단계를 순차 실행하며,
어느 단계 실패 시 즉시 중단한다.
각 단계의 소요 시간을 측정하고 최종 요약을 출력한다.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 실행할 스크립트 목록 (순서대로)
# ---------------------------------------------------------------------------
STEPS: list[tuple[str, str]] = [
    ("01_load_admin.py",        "행정동 경계 로드"),
    ("02_load_parcels.py",      "연속지적도 + 토지특성 조인"),
    ("03_load_buildings.py",    "건축물 통합 + 표제부 + 부속지번 조인"),
    ("04_load_oa.py",           "집계구 경계 + 인구·가구 통계"),
    ("05_build_parcel_attrs.py", "필지별 대표 주용도 산정"),
    ("06_generate_stats.py",    "통계 JSON 산출"),
    ("07_emit_geojson.py",      "GeoJSON 내보내기 + frontend 복사"),
]


def _format_duration(seconds: float) -> str:
    """초 단위 시간을 읽기 쉬운 형식으로 변환한다."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def main() -> int:
    """전체 파이프라인 실행. 종료 코드를 반환한다."""
    print("=" * 70)
    print("  송파구 토지이용 전처리 파이프라인 일괄 실행")
    print("=" * 70)
    print()

    results: list[tuple[str, str, float, bool]] = []
    pipeline_start = time.time()

    for i, (script_name, description) in enumerate(STEPS, start=1):
        script_path = SCRIPT_DIR / script_name

        # 스크립트 존재 여부 확인
        if not script_path.exists():
            print(f"  [{i}/{len(STEPS)}] [SKIP] {script_name} - 파일 없음")
            print(f"         ({script_path})")
            print()
            results.append((script_name, description, 0.0, True))
            continue

        print(f"  [{i}/{len(STEPS)}] [RUN] {description}")
        print(f"         {script_name}")
        print()

        step_start = time.time()

        try:
            # sys.executable을 사용해 현재 실행 중인 파이썬 인터프리터로 서브스크립트를 띄웁니다.
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(SCRIPT_DIR),
                check=False,
            )
        except Exception as exc:
            elapsed = time.time() - step_start
            print(f"\n  [ERROR] {script_name} 실행 중 예외 발생: {exc}")
            results.append((script_name, description, elapsed, False))
            break

        elapsed = time.time() - step_start

        if result.returncode != 0:
            print(f"\n  [FAIL] {script_name} 실패 (exit code {result.returncode})")
            print(f"     소요 시간: {_format_duration(elapsed)}")
            results.append((script_name, description, elapsed, False))
            break

        print(f"\n  [SUCCESS] {script_name} 완료 ({_format_duration(elapsed)})")
        print("-" * 70)
        results.append((script_name, description, elapsed, True))

    pipeline_elapsed = time.time() - pipeline_start

    # ── 최종 요약 ────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("  최종 실행 결과 요약")
    print("=" * 70)
    print()
    print(f"  {'단계':<30s}  {'소요시간':>10s}  {'결과':>6s}")
    print(f"  {'-'*30}  {'-'*10}  {'-'*6}")

    all_ok = True
    for script_name, description, elapsed, success in results:
        status = "OK" if success else "FAIL"
        if not success:
            all_ok = False
        time_str = _format_duration(elapsed) if elapsed > 0 else "skip"
        print(f"  {description:<30s}  {time_str:>10s}  {status:>6s}")

    print(f"  {'-'*30}  {'-'*10}  {'-'*6}")
    print(f"  {'총 소요 시간':<30s}  {_format_duration(pipeline_elapsed):>10s}")
    print()

    if all_ok:
        print("  [SUCCESS] 전체 파이프라인이 성공적으로 완료되었습니다!")
    else:
        print("  [FAIL] 파이프라인이 중단되었습니다. 위 에러를 확인하세요.")

    print("=" * 70)

    return 0 if all_ok else 1


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(main())
