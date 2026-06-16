# 하이브리드 재편 (2026-06-16): 활성강의(송영곤·김기용·강성민) 책→_강의/{강의}/ 합침
# 폴더 단위 이동. dry-run 기본 / --apply 로 실행 + 로그
import sys, shutil, csv, json
from pathlib import Path
from datetime import datetime

R = Path(r'H:\내 드라이브')
APPLY = '--apply' in sys.argv
TASK = 'hybrid_reorg_2026-06-16'

# (src_folder_rel, dst_folder_rel)
M = [
 # 송영곤 (민사) — 책 → _강의/{강의}/교재/
 ('1.민사/논점민법강의',   '1.민사/_강의/30.송영곤_기본민법/교재/논점민법강의'),
 ('1.민사/송영곤사례연습', '1.민사/_강의/31.송영곤_사례/교재/송영곤사례연습'),
 ('1.민사/민사법사례연습2','1.민사/_강의/32.송영곤_사례연습2/교재/민사법사례연습2'),
 ('1.민사/민사법쟁점노트', '1.민사/_강의/33.송영곤_쟁노/교재/민사법쟁점노트'),
 ('1.민사/논점민소',       '1.민사/_강의/34.송영곤_민소/교재/논점민소'),
 ('1.민사/민소사례',       '1.민사/_강의/34.송영곤_민소/교재/민소사례'),
 # 김기용 (형사)
 ('2.형사/김기용형총',     '2.형사/_강의/10.김기용_형법교안/교재/김기용형총'),
 # 강성민 (공법) — 강의폴더 신설
 ('3.공법/강성민헌법OX',                 '3.공법/_강의/10.강성민_헌법/교재/강성민헌법OX'),
 ('3.공법/91.보관/강성민_헌법단권화노트', '3.공법/_강의/10.강성민_헌법/정리/강성민_헌법단권화노트'),
 ('3.공법/91.보관/강성민_헌법ox',         '3.공법/_강의/10.강성민_헌법/강의자료/강성민_헌법ox'),
]

def count_files(p):
    return sum(1 for f in p.rglob('*') if f.is_file())
def total_size(p):
    return sum(f.stat().st_size for f in p.rglob('*') if f.is_file())

lines=[]; rows=[]; ok=0; bad=0
for src_rel, dst_rel in M:
    s=R/src_rel; d=R/dst_rel
    if not s.exists():
        lines.append(f'  [MISS] {src_rel}'); bad+=1; continue
    if d.exists():
        lines.append(f'  [DST존재] {dst_rel}'); bad+=1; continue
    nf=count_files(s); sz=total_size(s)/1e6
    lines.append(f'  [이동] {nf:>3}개 {sz:7.1f}MB  {src_rel}  ->  {dst_rel}')
    ok+=1
    if APPLY:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(s), str(d))
        nf2=count_files(d); verified=(nf==nf2)
        ts=datetime.now().isoformat(timespec='seconds')
        rows.append([ts,'move_folder',src_rel,dst_rel,int(sz*1e6),f'(folder:{nf2}files)',TASK,'하이브리드 강의중심 합침',str(verified)])

hdr=f'하이브리드 재편 계획 (APPLY={APPLY})  이동 {ok} / 문제 {bad}'
Path('.agent/scripts/_hybrid_plan.txt').write_text(hdr+chr(10)+chr(10)+chr(10).join(lines), encoding='utf-8')

if APPLY and rows:
    L=R/'.agent/file_ops_log'
    with open(L/'master.csv','a',newline='',encoding='utf-8') as f: csv.writer(f).writerows(rows)
    cols=['timestamp','operation','source_path','dest_path','size_bytes','sha256','task_id','reason','verified']
    with open(L/'master.jsonl','a',encoding='utf-8') as f:
        for r in rows: f.write(json.dumps(dict(zip(cols,r)),ensure_ascii=False)+chr(10))
    with open(L/'master.md','a',encoding='utf-8') as f:
        for r in rows: f.write(f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[8]} |'+chr(10))
print(f'APPLY={APPLY} ok={ok} bad={bad} logged={len(rows)}')
