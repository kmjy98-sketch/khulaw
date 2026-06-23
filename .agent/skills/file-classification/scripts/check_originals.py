"""
Trash 폴더 내 사본 파일들의 원본 존재 여부 확인 스크립트
"""
import os
import sys
from pathlib import Path

_p = os.path.abspath(__file__)  # noqa: E402
while os.path.basename(_p) != '.agent' and os.path.dirname(_p) != _p:  # noqa: E402
    _p = os.path.dirname(_p)  # noqa: E402
sys.path.insert(0, os.path.join(_p, 'scripts'))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

TRASH_DIR = Path(vp("5.기타", "_trash", "중복"))
SEARCH_ROOT = Path(VAULT_ROOT)

def get_original_name(copy_name: str) -> str:
    """사본 파일명에서 원본 파일명 추출"""
    # "파일명의 사본.pdf" -> "파일명.pdf"
    # "파일명의 사본 (1).pdf" -> "파일명.pdf"
    # "파일명.pdf의 사본.pdf" -> "파일명.pdf"
    
    name = copy_name
    
    # 패턴들을 순서대로 처리
    # ".pdf의 사본.pdf" -> ".pdf"
    if ".pdf의 사본" in name:
        name = name.replace(".pdf의 사본.pdf", ".pdf")
        name = name.replace(".pdf의 사본 (1).pdf", ".pdf")
        name = name.replace(".pdf의 사본 (2).pdf", ".pdf")
        name = name.replace(".pdf의 사본 (3).pdf", ".pdf")
        name = name.replace(".pdf의 사본의 사본.pdf", ".pdf")
        name = name.replace(".pdf의 사본의 사본 (1).pdf", ".pdf")
    
    # "의 사본" 패턴 처리
    if "의 사본" in name:
        # 확장자 추출
        ext = Path(name).suffix
        base = name.rsplit("의 사본", 1)[0]
        if not base.endswith(ext):
            name = base + ext
        else:
            name = base
    
    # " 사본" 패턴 처리 (공백 + 사본)
    if " 사본" in name:
        ext = Path(name).suffix
        base = name.replace(" 사본" + ext, "")
        name = base + ext
    
    return name

def find_original(original_name: str, search_root: Path) -> list:
    """원본 파일 검색"""
    found = []
    for root, dirs, files in os.walk(search_root):
        # trash 폴더 제외
        if "_trash" in root:
            continue
        for f in files:
            if f == original_name:
                found.append(os.path.join(root, f))
    return found

def main():
    results = {
        "원본_존재": [],
        "원본_미발견": [],
        "변환_실패": []
    }
    
    trash_files = list(TRASH_DIR.glob("*"))
    print(f"검사 대상: {len(trash_files)}개 파일\n")
    
    for i, trash_file in enumerate(trash_files):
        if trash_file.is_dir():
            continue
            
        copy_name = trash_file.name
        original_name = get_original_name(copy_name)
        
        if original_name == copy_name:
            results["변환_실패"].append({
                "사본": copy_name,
                "비고": "원본명 추출 실패"
            })
            continue
        
        found_paths = find_original(original_name, SEARCH_ROOT)
        
        if found_paths:
            results["원본_존재"].append({
                "사본": copy_name,
                "원본명": original_name,
                "원본_위치": found_paths
            })
        else:
            results["원본_미발견"].append({
                "사본": copy_name,
                "원본명": original_name
            })
        
        if (i + 1) % 50 == 0:
            print(f"진행: {i + 1}/{len(trash_files)}")
    
    # 결과 출력
    print("\n" + "="*80)
    print(f"[결과 요약]")
    print(f"  원본 존재 (삭제 가능): {len(results['원본_존재'])}개")
    print(f"  원본 미발견 (복구 검토): {len(results['원본_미발견'])}개")
    print(f"  변환 실패: {len(results['변환_실패'])}개")
    print("="*80)
    
    # 원본 미발견 파일 목록 출력
    if results["원본_미발견"]:
        print("\n[원본 미발견 파일 목록]")
        for item in results["원본_미발견"]:
            print(f"  - {item['사본']}")
            print(f"    → 추정 원본명: {item['원본명']}")
    
    # 변환 실패 목록
    if results["변환_실패"]:
        print("\n[원본명 추출 실패]")
        for item in results["변환_실패"]:
            print(f"  - {item['사본']}")
    
    return results

if __name__ == "__main__":
    main()
