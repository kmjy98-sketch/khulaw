# -*- coding: utf-8 -*-
"""백업 전 인벤토리 — E:\\법학볼트 전수 파일수·용량·0바이트 점검·sha256 표본.
복원 검증 baseline(백업 후 대조 기준). 백업체계 §검증.

산출:
  .agent/state/backup_manifest_{date}.csv   (1행=1파일: relpath,size,mtime)
  .agent/state/backup_manifest_{date}.json  (요약: 총계·top폴더별·0바이트목록·sha표본·제외규칙)

제외(.git=GitHub관리 / 캐시·휴지통=재생성가능 / 비밀=보안):
  .git, __pycache__, .agent/temp_toc, .agent/temp_pdf_extract, _trash,
  .env*, *.key, *.pem, *.p12, .mcp.json, mcp.json, credentials*, token*, secrets/

사용:
  python .agent/scripts/backup_inventory.py [--date 2026-06-23] [--sample 12]
"""
import os
import sys
import json
import csv
import hashlib
import fnmatch
from datetime import datetime

_p = os.path.abspath(__file__)
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, 'scripts'))
from _vault import VAULT_ROOT, vp  # noqa: E402

ROOT = VAULT_ROOT
STATE = vp(".agent", "state")

# 디렉터리 제외(이름 정확일치 또는 상대경로 prefix)
EXCLUDE_DIRNAMES = {".git", "__pycache__", "_trash", "node_modules", ".obsidian"}
EXCLUDE_RELPREFIX = (os.path.join(".agent", "temp_toc"),
                     os.path.join(".agent", "temp_pdf_extract"))
# 비밀 파일 글롭(백업에서 제외 — 보안)
EXCLUDE_FILEGLOBS = (".env", ".env.*", "*.key", "*.pem", "*.p12",
                     ".mcp.json", "mcp.json", "credentials*", "token*")


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) else default
    return default


def is_secret(fn):
    return any(fnmatch.fnmatch(fn.lower(), g.lower()) for g in EXCLUDE_FILEGLOBS)


def main():
    date = arg("--date") or datetime.now().strftime("%Y-%m-%d")
    n_sample = int(arg("--sample", "12"))

    files = []          # (relpath, size, mtime)
    zero_byte = []
    secrets_skipped = 0
    per_top = {}        # top folder -> [count, bytes]

    for dp, dn, fn in os.walk(ROOT):
        # 디렉터리 가지치기
        dn[:] = [d for d in dn if d not in EXCLUDE_DIRNAMES]
        rel_dir = os.path.relpath(dp, ROOT)
        if rel_dir != "." and any(rel_dir == p or rel_dir.startswith(p + os.sep)
                                  for p in EXCLUDE_RELPREFIX):
            dn[:] = []
            continue
        for f in fn:
            if is_secret(f):
                secrets_skipped += 1
                continue
            fp = os.path.join(dp, f)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            rel = os.path.relpath(fp, ROOT)
            files.append((rel, st.st_size, int(st.st_mtime)))
            top = rel.split(os.sep)[0] if os.sep in rel else "(root)"
            slot = per_top.setdefault(top, [0, 0])
            slot[0] += 1
            slot[1] += st.st_size
            if st.st_size == 0:
                zero_byte.append(rel)

    files.sort()
    total_bytes = sum(s for _, s, _ in files)

    # sha256 표본 — 큰 파일 위주로 고르게(정렬 후 등간격)
    sample = []
    big = sorted(files, key=lambda x: -x[1])[:max(n_sample * 3, 30)]
    step = max(1, len(big) // n_sample)
    for rel, size, _ in big[::step][:n_sample]:
        h = hashlib.sha256()
        try:
            with open(os.path.join(ROOT, rel), "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            sample.append({"path": rel, "size": size, "sha256": h.hexdigest()})
        except OSError:
            pass

    os.makedirs(STATE, exist_ok=True)
    csv_path = os.path.join(STATE, f"backup_manifest_{date}.csv")
    json_path = os.path.join(STATE, f"backup_manifest_{date}.json")

    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["relpath", "size_bytes", "mtime_epoch"])
        w.writerows(files)

    summary = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "vault_root": ROOT,
        "date": date,
        "total_files": len(files),
        "total_bytes": total_bytes,
        "total_gib": round(total_bytes / 1024**3, 2),
        "zero_byte_count": len(zero_byte),
        "zero_byte_files": zero_byte[:200],
        "secrets_skipped": secrets_skipped,
        "exclude_dirnames": sorted(EXCLUDE_DIRNAMES),
        "exclude_relprefix": list(EXCLUDE_RELPREFIX),
        "exclude_fileglobs": list(EXCLUDE_FILEGLOBS),
        "per_top_folder": {k: {"files": v[0], "gib": round(v[1] / 1024**3, 3)}
                           for k, v in sorted(per_top.items(),
                                              key=lambda kv: -kv[1][1])},
        "sha256_sample": sample,
    }
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"files={len(files)}  total={summary['total_gib']}GiB  "
          f"zero_byte={len(zero_byte)}  secrets_skipped={secrets_skipped}")
    print(f"CSV  -> {csv_path}")
    print(f"JSON -> {json_path}")
    if zero_byte:
        print(f"[주의] 0바이트 {len(zero_byte)}건(placeholder 누락 신호 가능) — JSON 참조")


if __name__ == "__main__":
    main()
