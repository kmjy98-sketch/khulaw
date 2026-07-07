"""중복 chunk 정본 선정 DryRun (2026-04-30)
대상: 송영곤_논점민법_보충, 윤동환_민법의맥
기준: C(서브책자 본책>보충>부록) → D(사이즈 큰 것) → A(ch 작은 것)
출력: 9.작업중/클로드/중복정리_DryRun_보고_2026-04-30.md
"""
import os, re, hashlib, json
from collections import defaultdict
from pathlib import Path

ROOT = Path(r"H:\내 드라이브")
TARGETS = [
    ROOT / "sync/_교재원문/민법/송영곤_논점민법_보충",
    ROOT / "sync/_교재원문/민법/윤동환_민법의맥",
]
REPORT = ROOT / "9.작업중/클로드/중복정리_DryRun_보고_2026-04-30.md"


def parse_front_matter(text: str):
    """Strict line-level YAML front matter.
    또한 인라인(한 줄에 모든 필드 + 끝에 ' ---') 형식도 처리한다.
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.split("\n")

    # CASE A: 정상 멀티라인 YAML (---\n...\n---\n)
    # 첫 줄이 정확히 '---'이고 이후 줄에 정확히 '---' 줄이 나와야 한다.
    if lines[0].rstrip() == "---":
        for i in range(1, len(lines)):
            if lines[i].rstrip() == "---":
                fm_text = "\n".join(lines[1:i])
                body = "\n".join(lines[i + 1 :]).lstrip("\n")
                return _parse_yaml_fields(fm_text), body
        # 닫는 --- 없음 → FM 없음
        return {}, text

    # CASE B: 인라인 YAML (--- tags: ... 원본_chunk: ... ---\n# 본문)
    # 첫 줄이 '---'으로 시작하지만 단독이 아닌 경우
    first = lines[0]
    if first.startswith("--- ") or first.startswith("---\t"):
        # 같은 줄 또는 이후 줄에서 ' ---' 끝나는 위치 찾기
        # 가장 단순: 첫 번째 \n 이전까지 검사. 없으면 멀티라인 인라인 가능
        # 여기 데이터: 한 줄 안에 끝나거나 5줄 이내에 끝남.
        joined = []
        end_idx = -1
        for i, ln in enumerate(lines):
            joined.append(ln)
            stripped = ln.rstrip()
            if i == 0 and stripped.endswith(" ---"):
                end_idx = i
                break
            if i > 0 and (stripped == "---" or stripped.endswith(" ---")):
                end_idx = i
                break
        if end_idx >= 0:
            inline_block = "\n".join(joined)
            # 앞 '--- ' 제거, 끝 ' ---' 제거
            inner = inline_block
            if inner.startswith("---"):
                inner = inner[3:]
            inner = inner.rstrip()
            if inner.endswith("---"):
                inner = inner[:-3].rstrip()
            body = "\n".join(lines[end_idx + 1 :]).lstrip("\n")
            # 인라인은 키:값이 공백으로 이어붙어 있어 정확 파싱 어려움 → 키별 정규식
            meta = _parse_inline_yaml(inner)
            return meta, body

    return {}, text


def _parse_yaml_fields(fm_text: str) -> dict:
    meta = {}
    for line in fm_text.split("\n"):
        if not line.strip():
            continue
        if line.startswith(" ") or line.startswith("\t"):
            continue  # list continuation
        m = re.match(r"^([^:\s][^:]*?):\s*(.*)$", line)
        if m:
            k = m.group(1).strip()
            v = m.group(2).strip().strip('"').strip("'")
            meta[k] = v
    return meta


def _parse_inline_yaml(inner: str) -> dict:
    """인라인 YAML에서 알려진 키 추출."""
    meta = {}
    keys = ["교재", "판", "판_연도", "과목", "자료유형", "서브책자",
            "원본_chunk", "챕터번호", "전체챕터", "페이지", "페이지_범위",
            "정리일", "정리_버전", "ocr_quality", "pdf_원본"]
    for k in keys:
        # 키: 값 (다음 키 또는 끝까지)
        # 다음 키 후보들로 lookahead
        next_keys = "|".join(keys)
        pat = rf"{re.escape(k)}:\s*(.*?)(?=\s+(?:{next_keys})\s*:|$)"
        m = re.search(pat, inner, re.DOTALL)
        if m:
            v = m.group(1).strip().strip('"').strip("'")
            # 끝에 ' ---' 잔재 제거
            if v.endswith("---"):
                v = v[:-3].rstrip()
            meta[k] = v
    return meta


def classify_sub(sub: str, jaryotype: str = "") -> tuple[int, str]:
    """returns (priority, label). priority: 0=본책, 1=보충, 2=부록, 9=불명"""
    s = (sub or "").strip()
    j = (jaryotype or "").strip()

    # 자료유형 우선 시그널
    if j == "보충자료":
        return 1, "보충(자료유형=보충자료)"
    if j == "필기노트":
        return 1, "보충(필기노트)"

    if not s:
        return 9, "불명(서브책자 없음)"

    # 부록
    if "부록" in s:
        return 2, "부록"

    # 본책 패턴 (윤동환 민법의맥)
    # 본1, 본2, 본3, 채각A/B, 채총A/B, 물권A/B, 민총, 친상, 교본, 기본강의(메인)
    main_patterns = [
        r"^본\d+$", r"^본책", r"^채각[A-Z]?$", r"^채총[A-Z]?$",
        r"^물권[A-Z]?$", r"^민총[A-Z]?$", r"^친상[A-Z]?$",
        r"^교본", r"^기본강의$", r"^본문",
    ]
    for p in main_patterns:
        if re.match(p, s):
            return 0, f"본책(패턴 {p})"

    # 회차_필기, 필기 → 보충
    if re.search(r"\d+회차?_?필기", s) or "필기" in s:
        return 1, "보충(필기)"

    # 보충자료 키워드
    if "보충자료" in s or "보충" in s:
        return 1, "보충(키워드)"

    # 송영곤 보충 폴더 — sub가 '1-1_[…]_보충자료…' 등
    if "송영곤" in s or "변호사" in s or re.match(r"^\d+(-\d+)?[\[_]", s):
        return 1, "보충(송영곤 보충자료 추정)"

    # fallback
    return 1, "보충(기본 fallback)"


def scan_folder(folder: Path):
    rows = []
    if not folder.is_dir():
        return rows
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith(".md"):
            continue
        if fn.startswith("_"):
            continue
        p = folder / fn
        if not p.is_file():
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            rows.append({"fn": fn, "err": str(e)})
            continue
        meta, body = parse_front_matter(text)
        body_norm = body.strip()
        h = hashlib.sha256(body_norm.encode("utf-8")).hexdigest()
        sz = p.stat().st_size
        ch_raw = meta.get("챕터번호", "")
        try:
            ch = int(str(ch_raw).strip())
        except:
            ch = 9999
        sub = meta.get("서브책자", "")
        jary = meta.get("자료유형", "")
        prio, label = classify_sub(sub, jary)
        rows.append({
            "fn": fn,
            "sub": sub,
            "jaryotype": jary,
            "ch": ch,
            "size": sz,
            "body_len": len(body_norm),
            "hash": h,
            "prio": prio,
            "prio_label": label,
        })
    return rows


def pick_canonical(group: list[dict]) -> tuple[dict, list[dict], str]:
    """returns (canonical, others, reason)"""
    # sort: prio asc, size desc, ch asc, fn asc
    sorted_g = sorted(group, key=lambda x: (x["prio"], -x["size"], x["ch"], x["fn"]))
    canon = sorted_g[0]
    others = sorted_g[1:]

    # reason
    prios = sorted(set(x["prio"] for x in group))
    sizes = sorted(set(x["size"] for x in group), reverse=True)
    chs = sorted(set(x["ch"] for x in group))

    parts = []
    if len(prios) > 1:
        parts.append(f"c) prio={canon['prio']}({canon['prio_label']}) 우선")
    elif len(sizes) > 1:
        parts.append(f"d) size={canon['size']}B 최대")
    elif len(chs) > 1:
        parts.append(f"a) ch={canon['ch']} 최소")
    else:
        parts.append("동률(파일명 사전순)")

    if len(parts) == 1 and len(prios) == 1:
        # add secondary
        if len(sizes) > 1:
            parts.append(f"size={canon['size']}B 최대")
        if len(chs) > 1:
            parts.append(f"ch={canon['ch']} 최소")

    return canon, others, "; ".join(parts)


def process(folder: Path):
    rows = scan_folder(folder)
    by_hash = defaultdict(list)
    for r in rows:
        if "hash" in r:
            by_hash[r["hash"]].append(r)

    dup_groups = [g for g in by_hash.values() if len(g) > 1]
    dup_groups.sort(key=lambda g: -len(g))

    return rows, dup_groups


def main():
    out_lines = []
    out_lines.append("# 중복 chunk 정본 선정 DryRun 보고 (2026-04-30)\n")
    out_lines.append("> 본문 0% 변경. 실제 mv 미실행. 사용자 승인 후 진행.\n")
    out_lines.append(f"\n**기준**: C(서브책자: 본책>보충>부록) → D(사이즈 큰 것) → A(ch 작은 것)\n")
    out_lines.append(f"**해시**: SHA-256 (front matter 제외, body strip 후)\n")

    total_files = 0
    total_dup_groups = 0
    total_move = 0

    section_blocks = []

    for folder in TARGETS:
        rows, dup_groups = process(folder)
        n_files = len([r for r in rows if "hash" in r])
        n_groups = len(dup_groups)
        n_move = sum(len(g) - 1 for g in dup_groups)
        total_files += n_files
        total_dup_groups += n_groups
        total_move += n_move

        block = []
        block.append(f"\n---\n\n## {folder.name}\n")
        block.append(f"- 총 .md: **{n_files}개**")
        block.append(f"- 중복 그룹: **{n_groups}개**")
        block.append(f"- 이동 예정 파일: **{n_move}개**")
        block.append(f"- 정본 유지: **{n_files - n_move}개**\n")

        # 자료유형/서브책자 분포
        prio_dist = defaultdict(int)
        for r in rows:
            if "prio" in r:
                prio_dist[r["prio_label"]] += 1
        block.append("\n### 분류 분포\n")
        block.append("| 분류 | 파일수 |")
        block.append("|---|---|")
        for label, cnt in sorted(prio_dist.items(), key=lambda x: -x[1]):
            block.append(f"| {label} | {cnt} |")

        # 중복 그룹 상세
        if dup_groups:
            block.append("\n### 중복 그룹 상세\n")
            for i, g in enumerate(dup_groups, 1):
                canon, others, reason = pick_canonical(g)
                block.append(f"\n#### 그룹 {i} — {len(g)}개 (hash `{canon['hash'][:12]}…`)\n")
                block.append(f"**정본 선정 근거**: {reason}\n")
                block.append("| 역할 | 파일명 | 서브책자 | 자료유형 | ch | size | prio |")
                block.append("|---|---|---|---|---:|---:|---|")
                block.append(
                    f"| **정본** | `{canon['fn']}` | {canon['sub'] or '—'} | {canon['jaryotype'] or '—'} "
                    f"| {canon['ch']} | {canon['size']} | {canon['prio_label']} |"
                )
                for o in others:
                    block.append(
                        f"| 이동 | `{o['fn']}` | {o['sub'] or '—'} | {o['jaryotype'] or '—'} "
                        f"| {o['ch']} | {o['size']} | {o['prio_label']} |"
                    )
        else:
            block.append("\n### 중복 그룹 없음\n")

        section_blocks.append("\n".join(block))

    out_lines.append("\n## 요약\n")
    out_lines.append("| 폴더 | .md 수 | 중복 그룹 | 이동 예정 | 정본 유지 |")
    out_lines.append("|---|---:|---:|---:|---:|")
    for folder in TARGETS:
        rows, dup_groups = process(folder)
        n_files = len([r for r in rows if "hash" in r])
        n_groups = len(dup_groups)
        n_move = sum(len(g) - 1 for g in dup_groups)
        out_lines.append(
            f"| {folder.name} | {n_files} | {n_groups} | {n_move} | {n_files - n_move} |"
        )
    out_lines.append(
        f"| **합계** | **{total_files}** | **{total_dup_groups}** | **{total_move}** | **{total_files - total_move}** |"
    )

    out_lines.append("\n## 다음 단계\n")
    out_lines.append("1. 사용자 검토 후 승인")
    out_lines.append(
        f"2. 승인 시 이동 예정 파일을 `sync/_교재원문/민법/{{폴더}}/_중복_2026-04-30/`로 mv"
    )
    out_lines.append("3. 본문 0% 변경, 정본만 원위치 유지")

    out_lines.extend(section_blocks)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(out_lines), encoding="utf-8")

    print(f"OK -> {REPORT}")
    print(f"total files: {total_files}, dup groups: {total_dup_groups}, move: {total_move}")


if __name__ == "__main__":
    main()
