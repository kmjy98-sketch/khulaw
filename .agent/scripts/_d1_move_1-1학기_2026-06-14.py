# -*- coding: utf-8 -*-
"""
D1: 1-1학기 4과목 폴더 통째 이동 (검증 포함)
- 백업(전체 복사) -> 소스 sha256 해시 -> os.rename 이동(삭제 없음) -> 타깃 재해시 검증
- CLAUDE.md #16(삭제 금지): os.rename만 사용. 실패 시 즉시 중단(copy+delete 폴백 금지).
작성: 2026-06-14
"""
import os, sys, hashlib, json, shutil, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

ROOT = r"H:\내 드라이브"
DATE = "2026-06-14"
BACKUP_ROOT = os.path.join(ROOT, "5.기타", "_백업", DATE, "D1_1-1학기_이전")
TARGET_PARENT = os.path.join(ROOT, "6.1-1학기")
MANIFEST_DIR = os.path.join(ROOT, "sync", "_meta")

# (원본 상대경로, 신규 상대경로, 백업 하위명=원본명 유지)
PAIRS = [
    (r"1.민사\10.강혜림_민법1", r"6.1-1학기\민법1_강혜림", "10.강혜림_민법1"),
    (r"1.민사\20.전경운_민법3", r"6.1-1학기\민법3_전경운", "20.전경운_민법3"),
    (r"2.형사\20.서보학_형법1", r"6.1-1학기\형법1_서보학", "20.서보학_형법1"),
    (r"3.공법\10.이진_헌법원리1", r"6.1-1학기\헌법1_이진", "10.이진_헌법원리1"),
]

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def hash_tree(base):
    """base 하위 모든 파일: {상대경로: {sha256, size}}"""
    out = {}
    for dp, _, files in os.walk(base):
        for fn in files:
            fp = os.path.join(dp, fn)
            rel = os.path.relpath(fp, base).replace("\\", "/")
            out[rel] = {"sha256": sha256_file(fp), "size": os.path.getsize(fp)}
    return out

def log(msg):
    print(msg, flush=True)

def main():
    # 0. 사전 검증
    log("=== Phase 0: 사전 검증 ===")
    for src_rel, dst_rel, _ in PAIRS:
        src = os.path.join(ROOT, src_rel)
        dst = os.path.join(ROOT, dst_rel)
        if not os.path.isdir(src):
            log(f"ABORT: 원본 없음 {src}"); return 1
        if os.path.exists(dst):
            log(f"ABORT: 타깃 이미 존재 {dst}"); return 1
    if os.path.exists(BACKUP_ROOT):
        log(f"ABORT: 백업 폴더 이미 존재 {BACKUP_ROOT}"); return 1
    os.makedirs(TARGET_PARENT, exist_ok=True)
    os.makedirs(BACKUP_ROOT, exist_ok=False)
    os.makedirs(MANIFEST_DIR, exist_ok=True)
    log("사전 검증 통과.")

    manifest = {"date": DATE, "pairs": []}

    # 1. 백업(전체 복사)
    log("\n=== Phase 1: 백업 전체 복사 ===")
    for src_rel, dst_rel, bk in PAIRS:
        src = os.path.join(ROOT, src_rel)
        bdst = os.path.join(BACKUP_ROOT, bk)
        log(f"  copy {src_rel} -> 5.기타/_백업/{DATE}/D1_1-1학기_이전/{bk}")
        shutil.copytree(src, bdst)
    log("백업 복사 완료.")

    # 2. 소스 해시 (이동 전 기준값)
    log("\n=== Phase 2: 소스 sha256 해시 ===")
    src_hashes = {}
    for src_rel, dst_rel, bk in PAIRS:
        src = os.path.join(ROOT, src_rel)
        h = hash_tree(src)
        src_hashes[src_rel] = h
        log(f"  {src_rel}: {len(h)} files hashed")

    # 2b. 백업 해시 검증 (백업 == 소스)
    log("\n=== Phase 2b: 백업 무결성 검증 ===")
    for src_rel, dst_rel, bk in PAIRS:
        bdst = os.path.join(BACKUP_ROOT, bk)
        bh = hash_tree(bdst)
        sh = src_hashes[src_rel]
        if bh != sh:
            log(f"ABORT: 백업 해시 불일치 {bk} (src {len(sh)} / backup {len(bh)})"); return 1
        log(f"  {bk}: 백업 == 소스 OK ({len(bh)} files)")

    # 3. 이동 (os.rename, 삭제 없음)
    log("\n=== Phase 3: 이동 (os.rename) ===")
    for src_rel, dst_rel, bk in PAIRS:
        src = os.path.join(ROOT, src_rel)
        dst = os.path.join(ROOT, dst_rel)
        os.rename(src, dst)
        log(f"  moved {src_rel} -> {dst_rel}")

    # 4. 타깃 재해시 + 검증
    log("\n=== Phase 4: 타깃 재해시 100% 일치 검증 ===")
    all_ok = True
    for src_rel, dst_rel, bk in PAIRS:
        dst = os.path.join(ROOT, dst_rel)
        dh = hash_tree(dst)
        sh = src_hashes[src_rel]
        match = (dh == sh)
        all_ok = all_ok and match
        # 차이 상세
        missing = sorted(set(sh) - set(dh))
        extra = sorted(set(dh) - set(sh))
        mism = [k for k in sh if k in dh and sh[k]["sha256"] != dh[k]["sha256"]]
        manifest["pairs"].append({
            "src": src_rel.replace("\\", "/"),
            "dst": dst_rel.replace("\\", "/"),
            "backup": f"5.기타/_백업/{DATE}/D1_1-1학기_이전/{bk}",
            "file_count": len(sh),
            "match": match,
            "missing": missing, "extra": extra, "mismatch": mism,
        })
        status = "OK 100%" if match else f"FAIL (missing {len(missing)}, extra {len(extra)}, mismatch {len(mism)})"
        log(f"  {dst_rel}: {len(dh)} files -> {status}")

    # 5. 매니페스트 저장
    mpath = os.path.join(MANIFEST_DIR, f"D1_1-1학기_통째이동_매니페스트_{DATE}.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    log(f"\n매니페스트 저장: 9.작업중/클로드/D1_1-1학기_통째이동_매니페스트_{DATE}.json")

    log("\n=== 결과 ===")
    log("ALL MATCH 100%" if all_ok else "검증 실패 — 매니페스트 확인 필요")
    return 0 if all_ok else 2

if __name__ == "__main__":
    sys.exit(main())
