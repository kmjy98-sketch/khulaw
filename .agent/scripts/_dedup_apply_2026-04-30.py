"""34파일 실제 이동 + 매니페스트 + 해시 검증 (2026-04-30)
CLAUDE.md #16: 삭제 X, _중복_2026-04-30/ 으로 mv.
"""
import os, re, hashlib, json, shutil
from collections import defaultdict
from pathlib import Path
from datetime import datetime

ROOT = Path(r"H:\내 드라이브")
SRC = ROOT / "sync/_교재원문/민법/송영곤_논점민법_보충"
DUP_DIR = SRC / "_중복_2026-04-30"
MANIFEST_MD = ROOT / "sync/_meta/중복정리_이동매니페스트_2026-04-30.md"
MANIFEST_JSON = ROOT / "sync/_meta/중복정리_이동매니페스트_2026-04-30.json"


def parse_front_matter(text: str):
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")
    if lines[0].rstrip() == "---":
        for i in range(1, len(lines)):
            if lines[i].rstrip() == "---":
                fm_text = "\n".join(lines[1:i])
                body = "\n".join(lines[i + 1 :]).lstrip("\n")
                return _yaml(fm_text), body
        return {}, text
    first = lines[0]
    if first.startswith("--- ") or first.startswith("---\t"):
        joined = []
        end_idx = -1
        for i, ln in enumerate(lines):
            joined.append(ln)
            stripped = ln.rstrip()
            if i == 0 and stripped.endswith(" ---"):
                end_idx = i; break
            if i > 0 and (stripped == "---" or stripped.endswith(" ---")):
                end_idx = i; break
        if end_idx >= 0:
            inline_block = "\n".join(joined)
            inner = inline_block[3:].rstrip()
            if inner.endswith("---"):
                inner = inner[:-3].rstrip()
            body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
            return _inline(inner), body
    return {}, text


def _yaml(fm_text: str) -> dict:
    meta = {}
    for line in fm_text.split("\n"):
        if not line.strip(): continue
        if line.startswith(" ") or line.startswith("\t"): continue
        m = re.match(r"^([^:\s][^:]*?):\s*(.*)$", line)
        if m:
            meta[m.group(1).strip()] = m.group(2).strip().strip('"').strip("'")
    return meta


def _inline(inner: str) -> dict:
    keys = ["교재","판","판_연도","과목","자료유형","서브책자","원본_chunk",
            "챕터번호","전체챕터","페이지","페이지_범위","정리일","정리_버전",
            "ocr_quality","pdf_원본"]
    nk = "|".join(keys)
    meta = {}
    for k in keys:
        m = re.search(rf"{re.escape(k)}:\s*(.*?)(?=\s+(?:{nk})\s*:|$)", inner, re.DOTALL)
        if m:
            v = m.group(1).strip().strip('"').strip("'")
            if v.endswith("---"): v = v[:-3].rstrip()
            meta[k] = v
    return meta


def classify(sub: str, jary: str = "") -> int:
    s, j = (sub or "").strip(), (jary or "").strip()
    if j == "보충자료": return 1
    if j == "필기노트": return 1
    if not s: return 9
    if "부록" in s: return 2
    main = [r"^본\d+$", r"^본책", r"^채각[A-Z]?$", r"^채총[A-Z]?$",
            r"^물권[A-Z]?$", r"^민총[A-Z]?$", r"^친상[A-Z]?$",
            r"^교본", r"^기본강의$", r"^본문"]
    for p in main:
        if re.match(p, s): return 0
    return 1


def scan():
    rows = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".md"): continue
        if fn.startswith("_"): continue
        p = SRC / fn
        if not p.is_file(): continue
        text = p.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        body_norm = body.strip()
        h = hashlib.sha256(body_norm.encode("utf-8")).hexdigest()
        try: ch = int(str(meta.get("챕터번호","")).strip())
        except: ch = 9999
        sub = meta.get("서브책자","")
        jary = meta.get("자료유형","")
        rows.append({
            "fn": fn, "path": str(p), "sub": sub, "jary": jary,
            "ch": ch, "size": p.stat().st_size,
            "hash": h, "body_len": len(body_norm),
            "prio": classify(sub, jary),
        })
    return rows


def main():
    rows = scan()
    by_hash = defaultdict(list)
    for r in rows: by_hash[r["hash"]].append(r)
    groups = [g for g in by_hash.values() if len(g) > 1]

    moves = []
    for g in groups:
        sorted_g = sorted(g, key=lambda x: (x["prio"], -x["size"], x["ch"], x["fn"]))
        canon = sorted_g[0]
        for o in sorted_g[1:]:
            moves.append({
                "group_hash": canon["hash"],
                "canonical": canon["fn"],
                "src_path": o["path"],
                "src_fn": o["fn"],
                "src_size_before": o["size"],
                "src_body_hash_before": o["hash"],
                "src_body_len_before": o["body_len"],
            })

    print(f"이동 대상: {len(moves)}개")
    DUP_DIR.mkdir(parents=True, exist_ok=True)

    failed = []
    for m in moves:
        src = Path(m["src_path"])
        dst = DUP_DIR / m["src_fn"]
        if dst.exists():
            failed.append({"fn": m["src_fn"], "reason": "destination already exists"})
            continue
        # 이동 전 해시
        text_before = src.read_text(encoding="utf-8")
        _, body_before = parse_front_matter(text_before)
        h_before = hashlib.sha256(body_before.strip().encode("utf-8")).hexdigest()

        shutil.move(str(src), str(dst))

        # 이동 후 해시
        text_after = dst.read_text(encoding="utf-8")
        _, body_after = parse_front_matter(text_after)
        h_after = hashlib.sha256(body_after.strip().encode("utf-8")).hexdigest()

        m["dst_path"] = str(dst)
        m["src_body_hash_after_move"] = h_after
        m["body_unchanged"] = (h_before == h_after == m["src_body_hash_before"])
        m["dst_size_after"] = dst.stat().st_size
        m["size_unchanged"] = (m["dst_size_after"] == m["src_size_before"])

    # 매니페스트 JSON
    manifest = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "src_folder": str(SRC),
        "dup_folder": str(DUP_DIR),
        "n_moves": len(moves),
        "n_failed": len(failed),
        "criterion": "C(서브책자: 본책>보충>부록) → D(size 최대) → A(ch 최소)",
        "moves": moves,
        "failed": failed,
    }
    MANIFEST_JSON.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_JSON.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 매니페스트 MD
    md = []
    md.append("# 중복정리 이동 매니페스트 (2026-04-30)\n")
    md.append(f"- 시간: {manifest['timestamp']}")
    md.append(f"- 원본: `{SRC}`")
    md.append(f"- 이동지: `{DUP_DIR}`")
    md.append(f"- 이동 성공: **{len(moves) - len(failed)}**")
    md.append(f"- 이동 실패: {len(failed)}\n")
    md.append("**기준**: C(서브책자) → D(size) → A(ch)\n")

    # 본문 무결성
    all_ok = all(m.get("body_unchanged") for m in moves)
    md.append(f"\n## 본문 무결성 검증\n")
    md.append(f"- 모든 이동 파일의 body sha256(이동 전 == 이동 후 == DryRun): **{'OK' if all_ok else 'FAIL'}**\n")

    md.append("\n## 그룹별 이동 내역\n")
    by_group = defaultdict(list)
    canon_by_group = {}
    for m in moves:
        by_group[m["group_hash"]].append(m)
        canon_by_group[m["group_hash"]] = m["canonical"]
    for i, (gh, items) in enumerate(by_group.items(), 1):
        md.append(f"\n### 그룹 {i} (hash `{gh[:12]}…`)\n")
        md.append(f"- 정본 유지: `{canon_by_group[gh]}`")
        md.append(f"- 이동 ({len(items)}개):")
        for it in items:
            tag = "OK" if it.get("body_unchanged") else "FAIL"
            md.append(f"  - [{tag}] `{it['src_fn']}` ({it['src_size_before']}B → `{Path(it.get('dst_path','')).name}`)")

    if failed:
        md.append("\n## 실패\n")
        for f in failed:
            md.append(f"- `{f['fn']}`: {f['reason']}")

    MANIFEST_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"매니페스트 MD: {MANIFEST_MD}")
    print(f"매니페스트 JSON: {MANIFEST_JSON}")
    print(f"본문 무결성: {'OK' if all_ok else 'FAIL'}")


if __name__ == "__main__":
    main()
