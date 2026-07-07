# _RETIRED 2026-06-26 (#49 묘비명 대장)

정규식 기반 위키/분할/dedup 도구 일괄 은퇴. 사유: #50-C(정규식 신뢰 금지·LLM 의미생성)·#16-D(분할=PDF플러그인, 추출=LlamaParse) 신설로 정규식 생성기 폐기. 후속: 원문 분할·위키화는 LLM, 책 분할은 PDF 플러그인. 복원 시 log_file_op.py로 원위치 이동(가역).

| 파일 | 사유 | 후속 |
|---|---|---|
| wiki_원문분할.py | 정규식 원문분할(잘림·기계청크 원흉) | LLM 대단원 분할(#50-B/C) |
| wiki_transformer.py | 정규식 백링크(파기이송→파기[[이송]] 파손) | LLM 의미 백링크(#35·#50-C) |
| _ocr_extracted_dedup_2026-04-30.py | 특수문자 맹인 dedup(§·한자·①무시), 대상 폴더 빈 채 폐기 | 불요 |
| wiki_topic_inventory.py | 폐기되는 영문 wiki 구조 의존 정규식 인벤토리 | #50 재구조화 후 불요 |
| rename_chunks_batch1.py | 정규식 청크 리네이머 | 청크 폐기와 함께 불요 |
| rename_chunks_batch2.py | 〃 | 〃 |
| rename_chunks_batch3.py | 〃 | 〃 |
| rename_chunks_batch3_yoondonghwan.py | 〃 | 〃 |
| rename_chunks_final.py | 〃 | 〃 |
| rename_chunks_test1.py | 〃 | 〃 |
| rename_chunks_test2.py | 〃 | 〃 |

이동 로그: `.agent/file_ops_log/master.{csv,jsonl,md}` (task_id=restructure-20260626, #16-C).
