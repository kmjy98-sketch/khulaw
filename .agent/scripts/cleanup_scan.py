# -*- coding: utf-8 -*-
"""cleanup_scan.py — 정리 후보 스캔 (보고 전용, #16 비삭제).

0바이트·빈 디렉터리·오래된 _trash·재생성 캐시(.pyc)·대용량 텍스트 이상치를 찾아
보고서만 생성한다. 실제 이동/삭제는 사용자 승인 후 log_file_op.py로 (#16/#16-C).
무인 스케줄(Task Scheduler 주간) 안전 — 아무것도 건드리지 않음.

산출: .agent/state/cleanup_scan_{date}.md
사용: python .agent/scripts/cleanup_scan.py [--trash-age 30]
"""
import os
import sys
from datetime import datetime, timedelta

_p = os.path.abspath(__file__)
while os.path.basename(_p) != ".agent" and os.path.dirname(_p) != _p:
    _p = os.path.dirname(_p)
sys.path.insert(0, os.path.join(_p, "scripts"))
from _vault import VAULT_ROOT, vp  # noqa: E402

ROOT = VAULT_ROOT
EXCL_DIRS = {".git", "node_modules", "__pycache__", ".obsidian", "runtime",
            "site-packages", "_retired"}
SYS_FILES = {".gitkeep", ".gitignore", ".env", "desktop.ini", "__init__.py", ".last-cleanup"}
SKIP_EXT = {".gdoc", ".gsheet", ".gslides", ".gscript"}  # #16-A 제외(구글 포인터)


def arg(name, d=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        return sys.argv[i + 1] if i + 1 < len(sys.argv) else d
    return d


def main():
    trash_age = int(arg("--trash-age", "30"))
    cutoff = (datetime.now() - timedelta(days=trash_age)).timestamp()
    zero, empty_dirs, large, old_trash = [], [], [], []
    pyc = pyc_bytes = 0
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in EXCL_DIRS]
        rel = os.path.relpath(dp, ROOT)
        relu = rel.replace("\\", "/")
        in_trash = relu == "_trash" or relu.startswith("_trash/")
        if not dn and not fn and rel != "." and not in_trash:
            empty_dirs.append(rel)
        for f in fn:
            fp = os.path.join(dp, f)
            ext = os.path.splitext(f)[1].lower()
            try:
                sz = os.path.getsize(fp)
                mt = os.path.getmtime(fp)
            except OSError:
                continue
            rp = os.path.relpath(fp, ROOT)
            if ext == ".pyc":
                pyc += 1
                pyc_bytes += sz
                continue
            if in_trash:
                if mt < cutoff:
                    old_trash.append((datetime.fromtimestamp(mt).strftime("%Y-%m-%d"), rp))
                continue
            if sz == 0 and f not in SYS_FILES and ext not in SKIP_EXT:
                zero.append(rp)
            if sz > 100 * 1024 * 1024 and ext in (".md", ".txt", ".json", ".csv", ".jsonl"):
                large.append((sz, rp))
    large.sort(reverse=True)

    date = datetime.now().strftime("%Y-%m-%d")
    out = vp(".agent", "state", "cleanup_scan_%s.md" % date)
    L = ["# 정리 후보 스캔 — %s" % date,
         "> 보고 전용(#16 비삭제). 이동은 사용자 승인 후 `log_file_op.py`.\n",
         "- 0바이트 파일: %d" % len(zero),
         "- 빈 디렉터리: %d" % len(empty_dirs),
         "- 재생성 `.pyc`: %d개 / %.1fMB" % (pyc, pyc_bytes / 1024 ** 2),
         "- %d일+ 묵은 `_trash`: %d" % (trash_age, len(old_trash)),
         "- 대용량 텍스트(>100MB): %d\n" % len(large)]

    def sec(title, items, fmt):
        L.append("## %s (%d)" % (title, len(items)))
        for it in items[:50]:
            L.append("- " + fmt(it))
        if len(items) > 50:
            L.append("- … 외 %d" % (len(items) - 50))
        L.append("")

    sec("0바이트 파일 (#16-A: _trash 이동 권고)", zero, lambda x: "`%s`" % x)
    sec("빈 디렉터리", empty_dirs, lambda x: "`%s`" % x)
    sec("%d일+ 묵은 _trash (검토 후 영구정리 후보)" % trash_age, old_trash,
        lambda x: "%s `%s`" % (x[0], x[1]))
    sec("대용량 텍스트", large, lambda x: "%.0fMB `%s`" % (x[0] / 1024 ** 2, x[1]))

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("스캔 완료 → %s" % out)
    print("0바이트=%d 빈디렉=%d pyc=%d(%.0fMB) 묵은trash=%d 대용량=%d" % (
        len(zero), len(empty_dirs), pyc, pyc_bytes / 1024 ** 2, len(old_trash), len(large)))


if __name__ == "__main__":
    main()
