#!/usr/bin/env python3
"""
파일명 마이그레이션 스크립트
(유형-순서)파일명 → 유형-순서_파일명 형식으로 변환

Usage:
    python migrate_filenames.py [--dry-run] [--dir <경로>]
    
Options:
    --dry-run   실제 변경 없이 미리보기만
    --dir       대상 디렉토리 (기본: VAULT_ROOT)
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

_p = os.path.abspath(__file__)  # noqa: E402
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:  # noqa: E402
    _p = os.path.dirname(_p)  # noqa: E402
sys.path.insert(0, os.path.join(_p, 'scripts'))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

# Windows 인코딩 문제 해결
sys.stdout.reconfigure(encoding='utf-8')

def parse_old_format(filename: str) -> tuple:
    """
    구 형식 파싱: (유형-순서)과목_강사_... 또는 (유형-순서)과목_...
    Returns: (type_num, seq_num, rest) or None
    """
    # 패턴: (숫자-숫자)나머지
    pattern = r'^\((\d+)-(\d+)\)(.+)$'
    match = re.match(pattern, filename)
    if match:
        type_num, seq_num, rest = match.groups()
        return (type_num, seq_num, rest)
    return None

def convert_year_format(rest: str) -> str:
    """
    연도 형식 변환: _제목(2024) → _제목_24 (2자리)
    """
    # 마지막 (YYYY) 패턴을 _YY로 변환
    def year_to_2digit(match):
        year = match.group(1)
        return f"_{year[2:]}"  # 2024 → 24
    
    pattern = r'\((\d{4})\)$'
    return re.sub(pattern, year_to_2digit, rest)

def new_format(type_num: str, seq_num: str, rest: str) -> str:
    """
    새 형식 생성: 유형-순서_나머지
    """
    # 연도 형식도 변환
    rest = convert_year_format(rest)
    return f"{type_num}-{seq_num}_{rest}"

def find_files_to_migrate(root_dir: Path) -> list:
    """
    마이그레이션 대상 파일 찾기
    """
    to_migrate = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 숨김 폴더, _trash 등 제외
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and not d.startswith('_')]
        
        for filename in filenames:
            parsed = parse_old_format(filename)
            if parsed:
                type_num, seq_num, rest = parsed
                old_path = Path(dirpath) / filename
                new_name = new_format(type_num, seq_num, rest)
                new_path = Path(dirpath) / new_name
                
                to_migrate.append({
                    'old_path': str(old_path),
                    'new_path': str(new_path),
                    'old_name': filename,
                    'new_name': new_name
                })
    
    return to_migrate

def migrate_files(files: list, dry_run: bool = True) -> dict:
    """
    파일명 마이그레이션 실행
    """
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    for item in files:
        old_path = Path(item['old_path'])
        new_path = Path(item['new_path'])
        
        if new_path.exists():
            results['skipped'].append({
                **item,
                'reason': '대상 파일 이미 존재'
            })
            continue
        
        if dry_run:
            print(f"[DRY-RUN] {item['old_name']}")
            print(f"       → {item['new_name']}")
            results['success'].append(item)
        else:
            try:
                old_path.rename(new_path)
                print(f"[OK] {item['old_name']} → {item['new_name']}")
                results['success'].append(item)
            except Exception as e:
                results['failed'].append({
                    **item,
                    'error': str(e)
                })
                print(f"[FAIL] {item['old_name']}: {e}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='파일명 마이그레이션 (괄호 제거)')
    parser.add_argument('--dry-run', action='store_true', help='미리보기만 (실제 변경 없음)')
    parser.add_argument('--dir', type=str, default=VAULT_ROOT, help='대상 디렉토리')
    parser.add_argument('--output', type=str, help='결과 JSON 저장 경로')
    parser.add_argument('--batch', type=int, default=0, help='배치 크기 (0=전체, N=N개씩 처리)')
    parser.add_argument('--resume', type=str, help='이전 결과 JSON에서 이어서 진행')
    parser.add_argument('--start', type=int, default=0, help='시작 인덱스 (--resume과 함께 사용)')
    
    args = parser.parse_args()
    
    root_dir = Path(args.dir)
    
    # 이어서 진행 모드
    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.exists():
            print(f"오류: 파일 없음 - {resume_path}")
            sys.exit(1)
        
        with open(resume_path, 'r', encoding='utf-8') as f:
            prev_data = json.load(f)
        
        files = prev_data.get('pending', [])
        print(f"이어서 진행: {len(files)}개 남음 (시작: {args.start})")
    else:
        if not root_dir.exists():
            print(f"오류: 디렉토리 없음 - {root_dir}")
            sys.exit(1)
        
        print(f"스캔 중: {root_dir}")
        files = find_files_to_migrate(root_dir)
        
        if not files:
            print("마이그레이션 대상 파일 없음")
            return
        
        # 파일 리스트 저장
        list_path = Path(args.output or vp('.agent', 'temp', 'migrate_list.json'))
        with open(list_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total': len(files),
                'pending': files,
                'completed': [],
                'failed': []
            }, f, ensure_ascii=False, indent=2)
        print(f"파일 리스트 저장: {list_path}")
        print(f"총 {len(files)}개 파일")
    
    # 배치 처리
    batch_size = args.batch if args.batch > 0 else len(files)
    start_idx = args.start
    end_idx = min(start_idx + batch_size, len(files))
    batch = files[start_idx:end_idx]
    
    if not batch:
        print("처리할 파일 없음")
        return
    
    print("-" * 50)
    print(f"모드: {'DRY-RUN' if args.dry_run else '실제 변경'}")
    print(f"배치: {start_idx + 1} ~ {end_idx} / {len(files)}")
    print("-" * 50)
    
    results = migrate_files(batch, dry_run=args.dry_run)
    
    print("-" * 50)
    print(f"완료: {len(results['success'])}개")
    print(f"스킵: {len(results['skipped'])}개")
    print(f"실패: {len(results['failed'])}개")
    
    # 상태 업데이트
    if not args.dry_run:
        list_path = Path(args.resume or args.output or vp('.agent', 'temp', 'migrate_list.json'))
        
        # 현재 상태 로드
        if list_path.exists():
            with open(list_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
        else:
            state = {'completed': [], 'failed': [], 'pending': files}
        
        # 완료/실패 업데이트
        state['completed'].extend(results['success'])
        state['failed'].extend(results['failed'])
        state['pending'] = files[end_idx:]  # 남은 파일
        state['last_batch'] = {
            'timestamp': datetime.now().isoformat(),
            'start': start_idx,
            'end': end_idx,
            'success': len(results['success']),
            'failed': len(results['failed'])
        }
        
        with open(list_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        print(f"\n상태 저장: {list_path}")
        print(f"남은 파일: {len(state['pending'])}개")
        
        if state['pending']:
            next_start = end_idx
            print(f"\n다음 배치 실행:")
            print(f"  python migrate_filenames.py --resume {list_path} --start {next_start} --batch {batch_size}")

if __name__ == '__main__':
    main()
