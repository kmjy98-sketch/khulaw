# 94.교재 정리 — 책 중심 재편 (2026-06-15)
# dry-run 기본 / --apply 시 실행 + master.{csv,jsonl,md} 로그
import sys, shutil, hashlib, csv, json
from pathlib import Path
from datetime import datetime

R = Path(r'H:\내 드라이브')
APPLY = '--apply' in sys.argv
TODAY = '2026-06-15'
TRASH = f'_trash/{TODAY}/94교재정리'
TASK = 'gyojae_reorg_2026-06-15'

def resolve(rel):
    """clean 경로 우선, 없으면 glob 패턴(끝 *suffix)로 폴더 내 탐색"""
    p = R / rel
    if p.exists():
        return p
    # 패턴: 부모폴더 + '*' + 마지막토큰
    par = (R / rel).parent
    suf = Path(rel).name  # e.g. '*_02.pdf'
    if suf.startswith('*') and par.exists():
        hits = sorted(par.glob(suf))
        if len(hits) == 1:
            return hits[0]
    return p  # 없는 채로 반환(존재검사에서 잡힘)

# (src_rel, dst_rel)  — dst가 TRASH 폴더면 중복폐기
M = []
def mv(src, dst): M.append((src, dst))

# ===== 1.민사 =====
# 요건사실론(새 책): 분할 2부 → 직속 / 통권 → 도서관
mv('1.민사/94.교재/_분할_1/송영곤_요건사실론/송영곤_요건사실론_01.pdf', '1.민사/요건사실론/요건사실론_01.pdf')
mv('1.민사/94.교재/_분할_1/송영곤_요건사실론/*_02.pdf',                  '1.민사/요건사실론/요건사실론_02.pdf')
mv('1.민사/94.교재/송영곤 요건사실론.pdf',                              '10.도서관/송영곤_요건사실론_원본.pdf')
# 신민사법기록형연습1(새 책): 분할 3부 → 직속 / 통권 → 도서관
mv('1.민사/94.교재/_분할/송영곤_기록형연습1_23/송영곤_신민사법기록형연습1_기본편_23_01.pdf', '1.민사/신민사법기록형연습1/신민사법기록형연습1_기본편_01.pdf')
mv('1.민사/94.교재/_분할/송영곤_기록형연습1_23/*_02.pdf',                                  '1.민사/신민사법기록형연습1/신민사법기록형연습1_기본편_02.pdf')
mv('1.민사/94.교재/_분할/송영곤_기록형연습1_23/*_03.pdf',                                  '1.민사/신민사법기록형연습1/신민사법기록형연습1_기본편_03.pdf')
mv('1.민사/94.교재/송영곤_신민사법기록형연습1_기본편_23.pdf', '10.도서관/송영곤_신민사법기록형연습1_원본_23.pdf')
# 신민사법선택형 7편본 → trash (독립 13장분할 + 도서관 5편본이 이미 완전)
for x in ['가족법','물권법','물적담보','민법총칙','인적담보','채권법1','채권법2']:
    mv(f'1.민사/94.교재/송영곤_신민사법선택형연습1_{x}_26.pdf', f'{TRASH}/송영곤_신민사법선택형연습1_{x}_26.pdf')

# ===== 2.형사 =====
mv('2.형사/94.교재/compact형법총론OX_26.pdf',      f'{TRASH}/compact형법총론OX_26.pdf')        # 이미 도서관
mv('2.형사/94.교재/compact형법총론OX_공범론_26.pdf', f'{TRASH}/compact형법총론OX_공범론_26.pdf')  # 독립4 장분할 중복
mv('2.형사/94.교재/compact형법총론OX_미수범_26.pdf', f'{TRASH}/compact형법총론OX_미수범_26.pdf')
mv('2.형사/94.교재/compact형법총론OX_책임론_26.pdf', f'{TRASH}/compact형법총론OX_책임론_26.pdf')
mv('2.형사/94.교재/작은변사기형법_25.pdf',          f'{TRASH}/작은변사기형법_25.pdf')           # 이미 도서관
mv('2.형사/94.교재/반반형법_24.pdf', '10.도서관/반반형법_원본_24.pdf')   # 구판 통권
mv('2.형사/94.교재/반반형법_25.pdf', '10.도서관/반반형법_원본_25.pdf')
mv('2.형사/94.교재/서보학_새로쓴형법총론.pdf', '2.형사/새로쓴형법총론/서보학_새로쓴형법총론.pdf')  # 새 책
mv('2.형사/94.교재/이인규_진도별변시사시기출형법사례연습_총론_25.pdf',                    '2.형사/이인규형법사례연습/이인규_형법사례연습_총론_25.pdf')
mv('2.형사/94.교재/이인규_진도별변시사시기출형법사례연습_개인적법익_25.pdf',              '2.형사/이인규형법사례연습/이인규_형법사례연습_개인적법익_25.pdf')
mv('2.형사/94.교재/이인규_진도별변시사시기출형법사례연습_사회적법익_국가기능_특별형법_25.pdf', '2.형사/이인규형법사례연습/이인규_형법사례연습_사회국가특별_25.pdf')

# ===== 3.공법 =====
IJIN = '3.공법/_강의/1-1_지난학기/10.이진_헌법원리1'
mv('3.공법/94.교재/1주_헌법기초이론_오리엔테이션_게시용_2.pdf', f'{IJIN}/강의자료/1주_헌법기초이론_오리엔테이션_게시용.pdf')
mv('3.공법/94.교재/2주_헌법기초이론_헌법사_헌법개정_게시용.pdf', f'{IJIN}/강의자료/2주_헌법기초이론_헌법사_헌법개정_게시용.pdf')
mv('3.공법/94.교재/4주_헌법기초이론_게시용.pdf',               f'{IJIN}/강의자료/4주_헌법기초이론_게시용.pdf')
mv('3.공법/94.교재/강의안_기본권의발달과개념.pdf',             f'{IJIN}/강의안_기본권의발달과개념.pdf')  # 별도파일(단독)
mv('3.공법/94.교재/[5+1] 2027 해커스변호사 변호사시험 기출문제집 헌법 사례형 - 최신개정판ㅣ변호사시험 등 각종 국가고_3c_r6_d2.pdf', f'{TRASH}/해커스헌_사례형_다운로드중복_27.pdf')  # =원본_27
mv('3.공법/94.교재/유니온헌법기출편_27.pdf',                  f'{TRASH}/유니온헌법기출편_27.pdf')  # =원본_27
mv('3.공법/94.교재/유니온헌법선택형기출_모의편_27.pdf', '3.공법/유니온헌모의편/유니온헌_모의편_27.pdf')  # 별권 새 책
mv('3.공법/94.교재/헌법300_원본_26.pdf', '10.도서관/헌법300_원본_26.pdf')
mv('3.공법/94.교재/헌법변사기_25.pdf', '3.공법/헌법변사기/헌법변사기_25.pdf')  # 새 책
# 구 subject 폴더의 통권 원본 → 도서관(책 중심: subject는 장분할만)
mv('3.공법/해커스헌사례/해커스헌_원본_27.pdf', '10.도서관/해커스헌_원본_27.pdf')
mv('3.공법/유니온헌객/유니온헌_원본_27.pdf',   '10.도서관/유니온헌_원본_27.pdf')

# ---- 실행/검증 ----
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

rows=[]; lines=[]; miss=0; ok=0
for src_rel, dst_rel in M:
    s=resolve(src_rel); d=R/dst_rel
    tag='TRASH' if '/_trash/' in dst_rel.replace('\\','/') else ('도서관' if dst_rel.startswith('10.도서관') else '이동')
    if not s.exists():
        lines.append(f'  [MISS] {src_rel}'); miss+=1; continue
    if d.exists():
        lines.append(f'  [DST존재] {dst_rel}'); miss+=1; continue
    mb=s.stat().st_size/1e6
    lines.append(f'  [{tag}] {mb:6.1f}MB  {s.relative_to(R)}  ->  {dst_rel}')
    ok+=1
    if APPLY:
        d.parent.mkdir(parents=True, exist_ok=True)
        h1=sha(s); sz=s.stat().st_size
        shutil.move(str(s), str(d))
        h2=sha(d); verified = (h1==h2)
        ts=datetime.now().isoformat(timespec='seconds')
        rows.append([ts,'move',str(s.relative_to(R)),dst_rel,sz,h2,TASK,'94교재 책중심 정리',str(verified)])

hdr=f'94.교재 정리 계획  (APPLY={APPLY})  이동가능 {ok} / 문제 {miss}'
Path('.agent/scripts/_gyojae_plan.txt').write_text(hdr+chr(10)+chr(10)+chr(10).join(lines), encoding='utf-8')

if APPLY and rows:
    L=R/'.agent/file_ops_log'
    with open(L/'master.csv','a',newline='',encoding='utf-8') as f:
        csv.writer(f).writerows(rows)
    with open(L/'master.jsonl','a',encoding='utf-8') as f:
        cols=['timestamp','operation','source_path','dest_path','size_bytes','sha256','task_id','reason','verified']
        for r in rows: f.write(json.dumps(dict(zip(cols,r)),ensure_ascii=False)+chr(10))
    with open(L/'master.md','a',encoding='utf-8') as f:
        for r in rows: f.write(f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[8]} |'+chr(10))
print(f'APPLY={APPLY} ok={ok} miss={miss} logged={len(rows)}')
