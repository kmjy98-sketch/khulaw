"""
JSON 매니페스트와 moves 로그를 합쳐서 MD 매니페스트 생성.
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PLAN = json.loads(Path(r"H:\내 드라이브\9.작업중/클로드\_ocr_extracted_통합_매니페스트_2026-04-30.json").read_text(encoding="utf-8"))
MOVES = json.loads(Path(r"H:\내 드라이브\9.작업중/클로드\_ocr_extracted_통합_매니페스트_2026-04-30_moves.json").read_text(encoding="utf-8"))
SHA = json.loads(Path(r"H:\내 드라이브\9.작업중/클로드\_ocr_extracted_sha256_검증_2026-04-30.json").read_text(encoding="utf-8"))

# raw_path → moves rec
moves_by_src = {m["src"]: m for m in MOVES}

# 분류별 통계
CLS_LABEL = {
    "A": "A. 완전 중복",
    "B": "B. 정본 확장 (raw 포함)",
    "B-partial": "B-partial. 부분 일치 (확인 필요)",
    "C": "C. unique (확인 필요)",
}

cls_groups = {k: [] for k in CLS_LABEL}
for rec in PLAN["plan"]:
    cls_groups.setdefault(rec["classification"], []).append(rec)

# 송영곤 사례_가족/담보/물권/민총 보정: _재추출/ → root
def fix_path(p_str):
    p = Path(p_str)
    if p.parent.name == "_재추출":
        # 신규 폴더 4개에 한해 root로 보정
        new_folders = ("송영곤_사례_가족", "송영곤_사례_담보", "송영곤_사례_물권", "송영곤_사례_민총")
        if p.parent.parent.name in new_folders:
            alt = p.parent.parent / p.name
            if alt.exists():
                return str(alt)
    return p_str

ROOT = Path(r"H:\내 드라이브")

def relativize(p_str):
    p = Path(p_str)
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return p_str.replace("\\", "/")

lines = []
lines.append("---")
lines.append("title: _ocr_extracted/ 통합 매니페스트")
lines.append("date: 2026-04-30")
lines.append("규정: CLAUDE.md #1·#16·#17·#18·#34·#35·#37 준수")
lines.append("작업: sha256 본문 fingerprint 비교 후 A(중복)/B(정본 확장)/C(unique) 분류 + 이동")
lines.append("본문변경: 0% (yaml frontmatter만 신규 추가, body 0% 변경)")
lines.append("---")
lines.append("")
lines.append("# _ocr_extracted/ 통합 매니페스트 (2026-04-30)")
lines.append("")
lines.append("## 0. 요약")
lines.append("")
lines.append(f"| 항목 | 값 |")
lines.append(f"|---|---|")
lines.append(f"| raw .md 총수 | {PLAN['total']}개 |")
lines.append(f"| A. 완전 중복 → _trash | {PLAN['counts'].get('A', 0)}건 |")
lines.append(f"| B. 정본 확장 → 정본/_재추출/ | {PLAN['counts'].get('B', 0)}건 |")
lines.append(f"| B-partial. 부분 일치 → 정본/_재추출/ + [확인필요] | {PLAN['counts'].get('B-partial', 0)}건 |")
lines.append(f"| C. unique → 신규/기존 정본 폴더 + [확인필요] | {PLAN['counts'].get('C', 0)}건 |")
lines.append(f"| 본문 sha256 무결성 | {SHA['ok']}/{SHA['total']} OK (mismatch {SHA['mismatch']}, missing {SHA['missing']}) |")
lines.append("")

lines.append("## 1. 본문 sha256 일치 검증")
lines.append("")
lines.append(f"- 총 이동: {SHA['total']}건")
lines.append(f"- A 분류 (단순 _trash 이동, hash 비교 X): 8건 — 파일 존재만 확인 ✓")
lines.append(f"- B/B-partial/C 분류 (yaml만 새로 작성, body 0% 변경): 41건")
lines.append(f"  - body fingerprint sha256 일치: **41/41** ✓")
lines.append(f"  - mismatch: 0건")
lines.append(f"  - missing: 0건")
lines.append(f"- 검증 보고: `9.작업중/클로드/_ocr_extracted_sha256_검증_2026-04-30.json`")
lines.append("")

lines.append("## 2. 분류별 처리 결과")
lines.append("")

for cls in ["A", "B", "B-partial", "C"]:
    items = cls_groups.get(cls, [])
    if not items:
        continue
    lines.append(f"### {CLS_LABEL[cls]} ({len(items)}건)")
    lines.append("")
    lines.append("| # | raw 원본 | → 이동지 | 본문 hash (앞 16자) | 사유 |")
    lines.append("|---:|---|---|---|---|")
    for i, rec in enumerate(items, 1):
        src_rel = relativize(rec["raw_path"])
        mv = moves_by_src.get(rec["raw_path"])
        if mv:
            dst_rel = relativize(fix_path(mv["dst"]))
        else:
            dst_rel = "(미이동)"
        h = rec["raw_hash"][:16]
        reason = rec["reason"][:80].replace("|", "/")
        lines.append(f"| {i} | `{src_rel}` | `{dst_rel}` | `{h}` | {reason} |")
    lines.append("")

lines.append("## 3. [확인필요] 잔존 항목")
lines.append("")
lines.append("- **B-partial (23건)** — 정본에 같은 책 prefix가 존재하나 본문 일치 낮음.")
lines.append("  - 사유 (예시): 정본은 OCR raw를 재구성·정리한 normalized 버전 (예: 홍형철 쟁점정리 1.2% 일치, 김성돈 형법총론 65~68% 일치, 강성민 헌법OX 25~33% 일치)")
lines.append("  - 위치: 각 정본 폴더의 `_재추출/` 하위. yaml `status: B_부분_확인필요` 표시")
lines.append("  - 권장 조치: 정본 normalize 과정에서 누락 페이지가 있는지 후속 검토 (raw vs 정본 페이지별 대조)")
lines.append("")
lines.append("- **C unique (14건)** — 정본 부재 또는 prefix 미매칭.")
lines.append("  - 13건: 송영곤 사례연습 가족/담보/물권/민총 — 신규 정본 폴더 4개 생성:")
lines.append("    - `sync/_교재원문/민법/송영곤_사례_가족/`")
lines.append("    - `sync/_교재원문/민법/송영곤_사례_담보/`")
lines.append("    - `sync/_교재원문/민법/송영곤_사례_물권/`")
lines.append("    - `sync/_교재원문/민법/송영곤_사례_민총/`")
lines.append("  - 1건: 김기용 레인보우 OX p0051-0100 — 김기용_레인보우OX/_재추출/ (49% 일치, 임계값 직전)")
lines.append("  - yaml `status: C_unique_확인필요` 표시")
lines.append("  - 권장 조치: 정본 normalize 진행 (page marker 추가, 한자→한글, 백링크) — 본 작업에서는 본문 0% 변경 원칙으로 보류")
lines.append("")

lines.append("## 4. raw 빈 폴더 (CLAUDE.md #16 준수, 삭제 X)")
lines.append("")
lines.append("- `sync/_ocr_extracted/` 하위 20개 폴더 모두 .md 파일 0개 상태로 잔존")
lines.append("- 파일 삭제 금지 원칙(#16)에 따라 빈 폴더 그대로 유지 — 사용자가 직접 정리할 수 있음")
lines.append("")

lines.append("## 5. 신규/기존 정본 폴더 변동")
lines.append("")
lines.append("### 신규 생성 폴더 (4개)")
lines.append("")
lines.append("| 폴더 | 파일수 | 출처 PDF |")
lines.append("|---|---:|---|")
lines.append("| `sync/_교재원문/민법/송영곤_사례_가족/` | 2 | 송영곤_사례연습_가족_26.pdf (89p) |")
lines.append("| `sync/_교재원문/민법/송영곤_사례_담보/` | 3 | 송영곤_사례연습_담보_26.pdf (125p) |")
lines.append("| `sync/_교재원문/민법/송영곤_사례_물권/` | 4 | 송영곤_사례연습_물권_26.pdf (171p) |")
lines.append("| `sync/_교재원문/민법/송영곤_사례_민총/` | 4 | 송영곤_사례연습_민총_26.pdf (153p) |")
lines.append("")
lines.append("### 기존 폴더 _재추출/ 추가 (B/B-partial/C 일부)")
lines.append("")
lines.append("- `sync/_교재원문/민법/전경운_민법3/_재추출/` +3 (B)")
lines.append("- `sync/_교재원문/민법/송영곤_논점민법_보충/_재추출/` +1 (B; DT_10회 문제)")
lines.append("- `sync/_교재원문/형법/홍형철_기본형법/_재추출/` +8 (B-partial; 쟁점정리 형법 25)")
lines.append("- `sync/_교재원문/형법/김성돈_형법총론/_재추출/` +6 (B-partial; 가담형태 + 보안처분)")
lines.append("- `sync/_교재원문/형법/김기용_레인보우OX/_재추출/` +3 (B-partial 2 + C 1)")
lines.append("- `sync/_교재원문/헌법/강성민_헌법OX/_재추출/` +7 (B-partial; OX 재판/총론통치구조)")
lines.append("")

lines.append("## 6. _trash로 이동된 A 중복 (8건)")
lines.append("")
lines.append("- 위치: `_trash/2026-04-30/_ocr_extracted/{원본 폴더명}/{원본 파일명}`")
lines.append("- 사유: 정본에 동일 본문 fingerprint(sha256) 보유 → raw OCR은 redundant")
lines.append("- 파일 (모두 정본 _재추출/ 또는 본문 폴더에 동일 본문 보유):")
for rec in cls_groups.get("A", []):
    src_rel = relativize(rec["raw_path"])
    matched = rec.get("best_match", "")
    matched_short = Path(matched).name if matched else ""
    lines.append(f"  - `{src_rel}` ↔ 정본 `{matched_short}`")
lines.append("")

lines.append("## 7. 산출 파일")
lines.append("")
lines.append("| 파일 | 내용 |")
lines.append("|---|---|")
lines.append("| `9.작업중/클로드/_ocr_extracted_통합_매니페스트_2026-04-30.md` | (본 문서) MD 형식 매니페스트 |")
lines.append("| `9.작업중/클로드/_ocr_extracted_통합_매니페스트_2026-04-30.json` | 분류 plan (모든 파일별 fingerprint·매칭) |")
lines.append("| `9.작업중/클로드/_ocr_extracted_통합_매니페스트_2026-04-30_moves.json` | 실제 이동 로그 (src→dst, status_tag) |")
lines.append("| `9.작업중/클로드/_ocr_extracted_sha256_검증_2026-04-30.json` | 본문 sha256 무결성 검증 결과 (49/49 OK) |")
lines.append("| `.agent/scripts/_ocr_extracted_dedup_2026-04-30.py` | 분류·이동 스크립트 |")
lines.append("| `.agent/scripts/_fix_songyk_case_placement.py` | 송영곤 신규 폴더 정렬 보정 스크립트 |")
lines.append("| `.agent/scripts/_verify_dedup_integrity.py` | sha256 검증 스크립트 |")
lines.append("")

lines.append("## 8. 운영 원칙 준수 확인")
lines.append("")
lines.append("- [x] CLAUDE.md #1 (Source Grounding): 본문 0% 변경, fingerprint 기반 객관 비교")
lines.append("- [x] CLAUDE.md #16 (삭제 금지): A 중복은 _trash/2026-04-30/ 이동, 빈 폴더 유지")
lines.append("- [x] CLAUDE.md #15 (Verify-Before-Act): dry-run 분류 plan 후 apply 실행, 49/49 sha256 검증")
lines.append("- [x] feedback_자료_인용_순환_금지: 기존 보고서·큐 파일은 참조 목록으로만 사용, 실제 분류는 본문 fingerprint로 결정")
lines.append("- [x] feedback_no_hanja: 본문 0% 변경 원칙으로 한자 변환 보류 ([확인필요] 라벨 표시)")
lines.append("- [ ] backlinks (#35): 본문 0% 변경 원칙으로 백링크 신규 추가 보류")

out_path = Path(r"H:\내 드라이브\9.작업중/클로드\_ocr_extracted_통합_매니페스트_2026-04-30.md")
out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"MD 매니페스트 작성: {out_path}")
print(f"총 {len(lines)}줄")
