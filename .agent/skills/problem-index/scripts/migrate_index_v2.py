#!/usr/bin/env python3
"""
problem_index.json v1.0 → v2.0 마이그레이션 스크립트
Usage: python migrate_index_v2.py [--dry-run]

v1.0 (문자열 배열) → v2.0 (객체 배열) 변환
"""

import json
import argparse
import re
from pathlib import Path
from datetime import date

def load_index():
    """problem_index.json 로드"""
    index_path = Path(__file__).parent.parent.parent.parent / "state" / "problem_index.json"
    if not index_path.exists():
        print(f"인덱스 파일 없음: {index_path}")
        return None, index_path
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f), index_path

def save_index(index, index_path):
    """problem_index.json 저장"""
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

def find_matching_answer_file(problem_file: str, all_files: list) -> str:
    """문제 파일에 대응하는 해설 파일 찾기"""
    problem_name = Path(problem_file).stem
    
    # 패턴: "문제" -> "해설" 변환
    answer_patterns = [
        problem_name.replace("문제", "해설"),
        problem_name.replace("_문제", "_해설"),
        problem_name.replace("-문제", "-해설"),
    ]
    
    for ans_pattern in answer_patterns:
        for f in all_files:
            f_stem = Path(f).stem if isinstance(f, str) else f
            if ans_pattern in f_stem:
                return f
    
    return None

def migrate_problems(problems_dict: dict, all_problem_files: list) -> dict:
    """
    problems dict를 v2.0 형식으로 변환
    
    v1.0: {"dt": ["file1.pdf", "file2.pdf"], "case": [...]}
    v2.0: {"dt": [{"file": "...", "answer": null, ...}], "case": [...]}
    """
    migrated = {}
    
    for ptype, items in problems_dict.items():
        migrated[ptype] = []
        
        for item in items:
            if isinstance(item, dict):
                # 이미 v2.0 형식
                migrated[ptype].append(item)
            elif isinstance(item, str):
                # v1.0 형식 → v2.0으로 변환
                
                # 해설 파일은 건너뜀 (문제 파일의 answer_source로 처리)
                if "해설" in item:
                    continue
                
                # 해설 파일 찾기
                answer_source = find_matching_answer_file(item, all_problem_files)
                
                entry = {
                    "file": item,
                    "answer": None,
                    "answer_source": answer_source,
                    "verified": answer_source is not None,
                    "last_verified": str(date.today()) if answer_source else None
                }
                migrated[ptype].append(entry)
    
    return migrated

def migrate_index(index: dict, dry_run: bool = False) -> dict:
    """전체 인덱스를 v2.0으로 마이그레이션"""
    
    if index.get("version") == "2.0":
        print("이미 v2.0 형식입니다.")
        return index
    
    stats = {"subjects": 0, "topics": 0, "problems_migrated": 0}
    
    for subject_name, subject_data in index.get("subjects", {}).items():
        stats["subjects"] += 1
        topics = subject_data.get("topics", {})
        
        for topic_name, topic_data in topics.items():
            stats["topics"] += 1
            problems = topic_data.get("problems", {})
            
            if not problems:
                continue
            
            # 전체 문제 파일 목록 수집 (해설 매칭용)
            all_files = []
            for ptype, items in problems.items():
                for item in items:
                    if isinstance(item, str):
                        all_files.append(item)
                    elif isinstance(item, dict):
                        all_files.append(item.get("file", ""))
            
            # 마이그레이션
            migrated = migrate_problems(problems, all_files)
            
            # 변환된 문제 수 카운트
            for ptype, items in migrated.items():
                stats["problems_migrated"] += len(items)
            
            if not dry_run:
                topic_data["problems"] = migrated
    
    if not dry_run:
        index["version"] = "2.0"
        index["last_updated"] = str(date.today())
    
    return index, stats

def main():
    parser = argparse.ArgumentParser(description="problem_index.json v1.0 → v2.0 마이그레이션")
    parser.add_argument("--dry-run", action="store_true", help="미리보기만 (저장 안함)")
    args = parser.parse_args()
    
    index, index_path = load_index()
    if not index:
        return
    
    print(f"[마이그레이션] {index_path}")
    print(f"현재 버전: {index.get('version', '1.0')}")
    print("=" * 50)
    
    migrated_index, stats = migrate_index(index, args.dry_run)
    
    print(f"\n[결과]")
    print(f"  과목 수: {stats['subjects']}")
    print(f"  쟁점 수: {stats['topics']}")
    print(f"  마이그레이션된 문제 수: {stats['problems_migrated']}")
    
    if not args.dry_run:
        save_index(migrated_index, index_path)
        print(f"\n[성공] v2.0으로 업그레이드 완료: {index_path}")
    else:
        print(f"\n[DRY-RUN] 저장하지 않음")

if __name__ == "__main__":
    main()
