# -*- coding: utf-8 -*-
"""
판례색인 청크만 재처리 (이미 있는 파일도 덮어씀)
"""
import os, json, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # noqa: E402
from _vault import VAULT_ROOT, vp  # noqa: E402

# batch3_ocr_correct.py 임포트
sys.path.insert(0, vp(".agent", "scripts"))
import batch3_ocr_correct as ocr

BASE = VAULT_ROOT

def main():
    chunks = ocr.load_chunk_list()
    done = 0

    for c in chunks:
        src_path, dst_path = ocr.get_paths(c)
        filename = os.path.basename(src_path)

        # 판례색인 파일만 재처리
        if '판례색인' not in filename:
            continue

        if not os.path.exists(src_path):
            print(f'[MISSING] {src_path}', flush=True)
            continue

        try:
            ocr.process_chunk(src_path, dst_path, filename)
            done += 1
            print(f'[OK] {filename}', flush=True)
        except Exception as e:
            print(f'[ERR] {filename}: {e}', flush=True)

    print(f'\n재처리완료: {done}개', flush=True)

if __name__ == '__main__':
    main()
