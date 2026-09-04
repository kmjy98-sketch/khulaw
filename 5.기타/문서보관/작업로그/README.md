# .agent/state

이 폴더의 실제 상태 파일은 대부분 개인 학습 상태, 캐시, 인덱스, 검증 결과다.

Git 포함 원칙:

- 포함: `*.schema.json`, `*template*.json`, `README.md`, `schemas/`, `templates/`
- 제외: `learning.json`, `srs_log.json`, `progress.sqlite`, `*.jsonl`, 캐시, 실제 인덱스, 개인 학습 상태

Web/Pro에서 상태 파일이 필요하면 실제 파일을 Git에 넣지 말고 템플릿 또는 스키마로 재현한다.
