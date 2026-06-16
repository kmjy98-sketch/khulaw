"""Round 3: Cell 0c 함수 분기 시뮬 (subprocess.run 모킹)."""
import json, os, sys, subprocess, types
from pathlib import Path

NB = Path(r"H:\내 드라이브\ocr_extract_v2.ipynb")
nb = json.loads(NB.read_text(encoding="utf-8"))
src = "".join(nb["cells"][8]["source"])

# 마지막 자동 실행 라인 제거 → 함수만 정의해서 호출 통제
# "seed_in_from_drive()" 와 그 다음 print 두 줄 제거
import re
src_def_only = re.sub(r"\nseed_in_from_drive\(\)\nprint.*$", "", src, count=1)

# subprocess.run 모킹 — 실제 실행 안 함, 명령어만 캡처
captured_calls = []
def fake_run(args, **kw):
    captured_calls.append(list(args))
    print(f"   [MOCK subprocess.run] {' '.join(args)}")
    return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

# 모듈 컨텍스트 구성
mod = types.ModuleType("cell0c_test")
mod.os = os
mod.subprocess = types.SimpleNamespace(
    run=fake_run,
    CompletedProcess=subprocess.CompletedProcess,
    TimeoutExpired=subprocess.TimeoutExpired,
)
import time as _time
mod.time = _time
# 외부 의존 변수 사전 주입 (Cell 6에서 정의되는 값들)
mod.DRIVE_ROOT = "/fake/drive"
mod._IS_COLAB = False

# 함수 정의 실행
exec(src_def_only, mod.__dict__)

print("=== 시나리오 A: _IS_COLAB=False ===")
mod._IS_COLAB = False
mod.DRIVE_ROOT = "/fake/drive"
mod.DRIVE_HF = "/fake/drive/.auto-memory/hf_cache"
mod.LOCAL_HF = "/root/.cache/huggingface"
mod.seed_in_from_drive()
mod.seed_to_drive()
print()

print("=== 시나리오 B: _IS_COLAB=True, Drive 캐시 0MB ===")
mod._IS_COLAB = True
# _dir_size_mb 는 실제 디스크 walk → 가짜 경로면 0 반환
mod.DRIVE_HF = "/nonexistent/drive/hf"
mod.LOCAL_HF = "/nonexistent/local/hf"
mod.seed_in_from_drive()
print()

# _rsync_or_cp 자체를 캡처 함수로 대체 (파일시스템 부작용 0)
captured_calls.clear()
def fake_rsync(src, dst, label):
    captured_calls.append((label, src, dst))
    print(f"   [MOCK rsync] label={label} src={src} dst={dst}")
    return True
mod._rsync_or_cp = fake_rsync

print("=== 시나리오 C: _IS_COLAB=True, Drive 캐시 200MB(mock) ===")
captured_calls.clear()
mod._dir_size_mb = lambda p: 200.0 if p == mod.DRIVE_HF else 0.0
mod.seed_in_from_drive()
print(f"   캡처된 호출: {captured_calls}")

print()
print("=== 시나리오 D: seed_to_drive (로컬 1500MB / Drive 0MB, mock) ===")
captured_calls.clear()
mod._dir_size_mb = lambda p: 1500.0 if p == mod.LOCAL_HF else 0.0
mod.seed_to_drive()
print(f"   캡처된 호출: {captured_calls}")

print()
print("=== 시나리오 E: seed_to_drive (변화 없음 1500/1495) ===")
captured_calls.clear()
mod._dir_size_mb = lambda p: 1500.0 if p == mod.LOCAL_HF else 1495.0
mod.seed_to_drive()
print(f"   캡처된 호출 수: {len(captured_calls)} (0이어야 정상)")

print("\n=== Round 3 done ===")
