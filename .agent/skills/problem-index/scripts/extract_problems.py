#!/usr/bin/env python3
"""
DT 선택형 PDF에서 문제와 정답을 추출하여 problem_index.json에 등록

Usage: 
  python extract_problems.py <pdf_path> [--dry-run] [--output <json_path>]

출력 형식:
[
  {
    "id": "DT1_Q1",
    "file": "4-1_민법_송영곤_기본민강_DT선택형1차_(선택).pdf",
    "page": 2,
    "question_num": 1,
    "question_text": "甲이 태아인 상태에서...",
    "answer": "X",  # O/X 문제
    "answer": 1,    # 선택형 문제 (①=1)
    "answer_source": "해설 페이지 참조",
    "verified": true
  }
]
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import date

# Windows 콘솔 인코딩
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    from pypdf import PdfReader
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pypdf", "-q"])
    from pypdf import PdfReader


def find_workspace_root() -> Path | None:
    candidates = [Path.cwd().resolve(), Path(__file__).resolve()]
    seen: set[Path] = set()
    for candidate in candidates:
        for parent in [candidate, *candidate.parents]:
            if parent in seen:
                continue
            seen.add(parent)
            if (parent / ".agent").exists():
                return parent
    return None


def get_problem_index_path() -> Path:
    workspace_root = find_workspace_root()
    if workspace_root is not None:
        return workspace_root / ".agent" / "state" / "problem_index.json"
    return Path(".agent/state/problem_index.json")


def workspace_relative(path: Path, workspace_root: Path | None) -> str:
    resolved = path.resolve()
    if workspace_root is not None:
        try:
            return str(resolved.relative_to(workspace_root.resolve())).replace("/", "\\")
        except ValueError:
            pass
    return str(resolved)


def extract_text_by_page(pdf_path: str) -> list:
    """PDF에서 페이지별 텍스트 추출"""
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page_num": i + 1, "text": text})
    return pages


def normalize_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def strip_explanation(text: str) -> str:
    cleaned = re.split(r'해설|정답', text, maxsplit=1)[0]
    return normalize_whitespace(cleaned)


def extract_choice_options(question_text: str) -> list[str]:
    normalized = strip_explanation(question_text)
    if "①" not in normalized or "..." in normalized:
        return []

    parts = re.split(r'(①|②|③|④|⑤)', normalized)
    choices = []
    for index in range(1, len(parts), 2):
        if index + 1 >= len(parts):
            continue
        content = re.split(r'정답', parts[index + 1], maxsplit=1)[0]
        content = normalize_whitespace(content)
        if content:
            choices.append(content)
        if len(choices) >= 5:
            break
    return choices[:5]


def find_problems_and_answers(pages: list) -> list:
    """
    PDF 텍스트에서 문제와 정답 추출
    
    패턴:
    - O/X 문제: "l..." + "해설 (X)" 또는 "해설 (◯)"
    - 선택형: "l..." + "①②③④⑤" + "정답 ①"
    """
    problems = []
    question_num = 0
    
    # 전체 텍스트 합치기 (페이지 경계 처리)
    full_text = "\n".join([p["text"] for p in pages])
    
    # O/X 문제 패턴: "l문제텍스트...해설 (X)" 또는 "해설 (◯)"
    ox_pattern = r'l([^l]+?)해설\s*\(([X◯OoXx])\)'
    
    # 선택형 문제 패턴: "l문제텍스트...①...②...③...④...⑤...정답 ①"
    choice_pattern = r'l([^l]+?①[^l]+?)정답\s*([①②③④⑤])'
    
    # O/X 문제 추출
    for match in re.finditer(ox_pattern, full_text, re.DOTALL):
        question_num += 1
        question_text = strip_explanation(match.group(1))
        answer_raw = match.group(2)
        
        # 정답 정규화
        answer = "O" if answer_raw in ['◯', 'O', 'o'] else "X"
        
        problems.append({
            "question_num": question_num,
            "question_text": question_text,
            "answer": answer,
            "type": "ox"
        })
    
    # 선택형 문제 추출
    for match in re.finditer(choice_pattern, full_text, re.DOTALL):
        question_num += 1
        question_text = strip_explanation(match.group(1))
        answer_raw = match.group(2)
        
        # 선지 번호 변환
        choice_map = {'①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5}
        answer = choice_map.get(answer_raw, 0)
        
        problems.append({
            "question_num": question_num,
            "question_text": question_text,
            "answer": answer,
            "type": "choice",
            "choices": extract_choice_options(question_text),
        })
    
    return problems


def create_problem_entries(problems: list, pdf_path: str) -> list:
    """problem_index.json 형식의 엔트리 생성"""
    pdf_file = Path(pdf_path)
    filename = pdf_file.name
    workspace_root = find_workspace_root()
    file_ref = workspace_relative(pdf_file, workspace_root)
    source_path = str(pdf_file.resolve())
    
    # 파일명에서 DT 회차 추출
    dt_match = re.search(r'DT.*?(\d+)', filename)
    dt_num = dt_match.group(1) if dt_match else "1"
    
    entries = []
    for i, prob in enumerate(problems, 1):
        question_text = normalize_whitespace(prob["question_text"])
        preview = question_text[:80] + ("..." if len(question_text) > 80 else "")
        entry = {
            "id": f"DT{dt_num}_Q{i}",
            "file": file_ref,
            "display_label": filename,
            "source_path": source_path,
            "page": None,  # 페이지 정보는 추가 분석 필요
            "question_num": i,
            "answer": prob["answer"],
            "answer_source": f"{filename}#해설편",
            "verified": True,
            "last_verified": str(date.today()),
            "question_type": prob["type"],
            "question_text": question_text,
            "question_preview": preview,
        }
        if prob["type"] == "choice":
            entry["choices"] = prob.get("choices", [])
        entries.append(entry)
    
    return entries


def update_problem_index(entries: list, pdf_path: str, dry_run: bool = False):
    """problem_index.json에 추출된 문제 엔트리 등록"""
    index_path = get_problem_index_path()
    
    if not index_path.exists():
        print(f"인덱스 파일 없음: {index_path}")
        return False
    
    with open(index_path, 'r', encoding='utf-8-sig') as f:
        index = json.load(f)
    
    pdf_file = Path(pdf_path)
    filename = pdf_file.name
    workspace_root = find_workspace_root()
    file_ref = workspace_relative(pdf_file, workspace_root)
    source_path = str(pdf_file.resolve())
    
    # DT 회차 추출하여 해당 쟁점 찾기
    dt_match = re.search(r'(\d+)(?:회|차)', filename)
    dt_num = int(dt_match.group(1)) if dt_match else 1
    
    updated_topics = []
    
    # 민법 subjects에서 해당 lecture의 topics 찾기
    for subj_name, subj_data in index.get("subjects", {}).items():
        topics = subj_data.get("topics", {})
        
        for topic_name, topic_data in topics.items():
            lecture = topic_data.get("lecture", 0)
            
            # lecture가 리스트인 경우 처리
            is_match = False
            if isinstance(lecture, list):
                is_match = dt_num in lecture
            else:
                is_match = lecture == dt_num
            
            if is_match:
                problems = topic_data.get("problems", {"dt": [], "case": []})
                
                # 기존 파일 기반 엔트리 제거 (새 문제별 엔트리로 대체)
                problems["dt"] = [
                    p for p in problems.get("dt", [])
                    if not (
                        isinstance(p, dict)
                        and (
                            p.get("file") == file_ref
                            or p.get("display_label") == filename
                            or p.get("source_path") == source_path
                        )
                    )
                    and not (isinstance(p, str) and filename in p)
                ]
                
                # 새 문제별 엔트리 추가
                problems["dt"].extend(entries)
                topic_data["problems"] = problems
                updated_topics.append(topic_name)
    
    if not dry_run and updated_topics:
        index["last_updated"] = str(date.today())
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        print(f"\n[업데이트됨] {len(entries)}개 문제 → {', '.join(updated_topics)}")
    else:
        print(f"\n[DRY-RUN] {len(entries)}개 문제를 다음 쟁점에 등록 예정: {', '.join(updated_topics)}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="DT PDF에서 문제/정답 추출")
    parser.add_argument("pdf_path", help="PDF 파일 경로")
    parser.add_argument("--dry-run", action="store_true", help="미리보기만")
    parser.add_argument("--output", "-o", help="출력 JSON 경로")
    parser.add_argument("--update-index", action="store_true", help="problem_index.json에 등록")
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"파일 없음: {pdf_path}")
        return
    
    print(f"[추출] {pdf_path.name}")
    print("=" * 50)
    
    # 텍스트 추출
    pages = extract_text_by_page(str(pdf_path))
    print(f"  총 페이지: {len(pages)}")
    
    # 문제/정답 추출
    problems = find_problems_and_answers(pages)
    print(f"  추출된 문제: {len(problems)}개")
    
    # O/X vs 선택형 분류
    ox_count = sum(1 for p in problems if p["type"] == "ox")
    choice_count = sum(1 for p in problems if p["type"] == "choice")
    print(f"    - O/X 문제: {ox_count}개")
    print(f"    - 선택형: {choice_count}개")
    
    # 엔트리 생성
    entries = create_problem_entries(problems, str(pdf_path))
    
    # 미리보기
    print("\n[미리보기 - 처음 5개]")
    for entry in entries[:5]:
        ans_str = entry["answer"] if isinstance(entry["answer"], str) else f"#{entry['answer']}"
        print(f"  {entry['id']}: {entry['question_preview']} → {ans_str}")
    
    if len(entries) > 5:
        print(f"  ... 외 {len(entries) - 5}개")
    
    # problem_index.json 업데이트
    if args.update_index:
        update_problem_index(entries, str(pdf_path), args.dry_run)
    
    # 파일로 저장
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        print(f"\n[저장됨] {output_path}")


if __name__ == "__main__":
    main()
