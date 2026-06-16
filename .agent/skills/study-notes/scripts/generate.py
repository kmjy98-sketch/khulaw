import os
import sys
import argparse
import json
from datetime import datetime

# study-notes/scripts/generate.py
# 수집된 컨텍스트와 템플릿을 기반으로 LLM이 참고할 프롬프팅 구조를 만들거나 빈 템플릿을 복사함.
# 에이전트(LLM)가 직접 노트를 채우게 함.

STATE_DIR = r"H:\내 드라이브\.agent\state"
CONTEXT_FILE = os.path.join(STATE_DIR, "study-notes-context.json")
TEMPLATE_DIR = r"H:\내 드라이브\.agent\skills\study-notes\templates"

def main():
    parser = argparse.ArgumentParser(description="노트 생성기 (프롬프트 준비)")
    parser.add_argument("--mode", required=True, choices=["concept", "case", "exam"], help="노트 생성 모드")
    parser.add_argument("--out", required=True, help="생성할 노트 파일 경로 (.md)")
    args = parser.parse_args()

    if not os.path.exists(CONTEXT_FILE):
        print(f"Error: Context file not found. Please run collect.py first.")
        sys.exit(1)

    template_file = os.path.join(TEMPLATE_DIR, f"{args.mode}.md")
    if not os.path.exists(template_file):
        print(f"Error: Template not found for mode {args.mode}")
        sys.exit(1)

    # 템플릿 읽기
    with open(template_file, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # 제목(subject) 치환 로직
    basename = os.path.basename(args.out)
    subject = os.path.splitext(basename)[0]
    template_content = template_content.replace("{subject}", subject)

    # 출력 폴더 생성
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # 기본 템플릿 포맷을 타겟 경로에 생성
    # LLM(에이전트)이 이 파일을 읽고 컨텍스트와 함께 내용을 채우도록 설계
    with open(args.out, 'w', encoding='utf-8') as f:
        f.write(template_content)

    print(f"Template for {args.mode} note generated successfully.")
    print(f"Path: {args.out}")
    print("Agent should now fill in the details based on the context in study-notes-context.json.")

if __name__ == "__main__":
    main()
