# 주간 급식표 자동 메일 발송 (Google Apps Script)

매주 **일요일 오전 8시(KST)**에 `kmjy98@gmail.com`로 다음 3곳의 주간 식단을 메일로 발송합니다.

## 현재 stable 버전 (2026-04-27)

| 식당 | 출처 | 전달 방식 |
|------|------|-----------|
| 경희대 푸른솔 | https://khucoop.com/37 | 페이지 내 식단표 이미지 PNG/JPG **첨부** (Drive `meal-menu-cache` ISO 주 단위 캐시) |
| 경희대 청운관 | https://khucoop.com/36 | 페이지 내 식단표 이미지 PNG/JPG **첨부** (위와 동일 캐시) |
| 한국외대 인문관 | https://www.hufs.ac.kr/hufs/11318/subview.do | 주간 메뉴 테이블을 **메일 본문 HTML inline 표**로 삽입 |

### HUFS만 HTML inline인 이유

Sheets→PNG 변환은 다음 모든 경로가 막힘 (시도 기록):
- `docs.google.com/spreadsheets/.../export?format=png` — OAuth Bearer 토큰 거절(401)
- `Drive.Files.export(id, 'image/png')` (Advanced Service v3) — `alt=media` 누락 에러
- `https://www.googleapis.com/drive/v3/files/.../export?mimeType=image%2Fpng` — 400 "The requested conversion is not supported" (Drive REST v3은 Sheets→PNG 미지원)
- 임시 시트 `setSharing(ANYONE_WITH_LINK)` 후 anonymous fetch — `setSharing` 자체가 `Service error: Drive`로 실패

따라서 HUFS는 PNG 첨부 대신 메일 본문에 HTML 표를 inline 삽입 (`htmlBody` 옵션). 후속 시도는 `Code_experiments_*.gs` 또는 별도 디버그 함수에서 진행.

### Stable 백업

- `Code_stable_2026-04-27_HUFS-HTML-inline.gs` — 동작 확인된 stable 본체 (수정 금지)
- `appsscript_stable_2026-04-27.json` — 동작 확인된 매니페스트 (수정 금지)

### HUFS PNG 변환 시도 결과 (2026-04-27)

모두 실패 → HTML inline로 최종 stable 확정.

| 안 | 결과 |
|---|---|
| docs.google.com/.../export?format=png + Bearer | 401 (Bearer 토큰 거절) |
| Drive Advanced Service `Drive.Files.export(id,'image/png')` | "Export requires alt=media" |
| Drive REST v3 `/files/{id}/export?mimeType=image%2Fpng` | 400 "The requested conversion is not supported" (Sheets→PNG 미지원) |
| 임시 시트 `setSharing(ANYONE_WITH_LINK)` 후 anonymous fetch | `setSharing` 자체가 `Service error: Drive`로 실패 |
| Slides 임시 생성 → PNG export PoC (`debugTrySlidesPng`) | 함수 드롭다운 sync 이슈로 PoC 미실행. 코드만 남아있음 (main 영향 X) |

메일 제목: `[주간 급식표] YYYY-MM-DD 주`
본문: 각 식당명 + 출처 URL + 첨부 상태(성공/실패).

---

## 설치 절차 (5단계)

### 1. Apps Script 프로젝트 생성

1. https://script.google.com 접속 → 우상단 **새 프로젝트**.
2. 좌측 프로젝트 이름을 `Weekly Meal Menu` 등으로 변경.

### 2. 매니페스트(`appsscript.json`) 노출 및 교체

1. 좌측 톱니바퀴 ⚙️ → **프로젝트 설정** → "appsscript.json 매니페스트 파일을 편집기에 표시" 체크.
2. 좌측 파일 트리에 `appsscript.json`이 보이면, 본 폴더의 `appsscript.json` 내용을 **전체 복사**해서 덮어쓰기.

### 3. `Code.gs` 붙여넣기

1. 기본 생성된 `Code.gs` 파일을 열고 내용을 모두 지운 뒤,
2. 본 폴더의 `Code.gs` 내용을 그대로 붙여넣고 저장(Ctrl+S).

### 4. 권한 승인 (1회)

1. 상단 함수 선택 드롭다운에서 **`sendWeeklyMealMenu`** 선택 → **▶ 실행** 클릭.
2. "권한이 필요합니다" 창 → **권한 검토** → 본인 Google 계정 선택.
3. "Google에서 확인하지 않은 앱입니다" 화면이 나오면 **고급 → (안전하지 않은 페이지로) 이동** → **허용**.
4. 잠시 후 메일이 도착하면 OK. 첨부 3개 + 본문에 각 항목별 상태가 보입니다.
   - 일부 항목이 "상태: 실패 — …"로 보이더라도 나머지는 정상 발송됩니다.

### 5. 트리거 설치 (1회)

1. 함수 선택 드롭다운에서 **`installWeeklyTrigger`** 선택 → **▶ 실행**.
2. 좌측 ⏰ **트리거** 메뉴에서 매주 일요일 8시(KST) 트리거가 생긴 것을 확인.

이제 매주 일요일 오전 8시에 자동 발송됩니다.

---

## 검증·운영 팁

- **수동 테스트**: 언제든 `sendWeeklyMealMenu`를 실행하면 그 시점 기준 주간 급식표가 도착합니다.
- **사이트 셀렉터 점검**: 발송 결과가 이상할 때 `debugProbeSources` 함수를 실행하면, KHU 페이지에서 발견한 `org_image` 태그와 HUFS 페이지에서 추출한 폼 파라미터가 로그(`보기 → 로그`)에 찍힙니다.
- **트리거 제거**: `removeAllTriggers` 실행 → `sendWeeklyMealMenu` 핸들러에 걸린 모든 트리거 삭제.
- **수신자 변경**: `Code.gs` 상단 `CONFIG.recipient` 수정 후 저장.
- **다른 식당 추가/삭제**: `CONFIG.sources` 배열 수정. KHU계열은 `type:'khu'`, HUFS는 `type:'hufs'` + `cafId`(인문관=`h101`, 교수회관=`h102`).

## 원리 요약

- **KHU (imweb)**: 페이지 HTML에서 `class=" org_image"` 가진 `<img>` 태그(페이지당 1개)의 `src`를 추출 → `UrlFetchApp.fetch`로 PNG/JPG를 받아 그대로 첨부.
- **HUFS**: 초기 페이지의 숨은 form input(`year`, `month`, `selWeekFirstDay`, `selWeekLastDay`)을 파싱 → AJAX 엔드포인트 `POST /cafeteria/hufs/1/getMenu`에 동일 파라미터 + `selCafId=h101` 전송 → 응답 HTML 테이블을 2D 배열로 파싱 → `SpreadsheetApp.create()`로 임시 Sheets에 표 그리기 → `?format=png` export URL을 OAuth 토큰으로 호출하여 PNG 받기 → 임시 Sheets는 `setTrashed(true)`로 정리.

## 알려진 한계·주의점

- **KHU 사이트 구조 변경**: `org_image` 클래스나 `cdn.imweb.me/thumbnail/...` 호스트가 바뀌면 추출이 실패합니다. `debugProbeSources`로 진단 가능.
- **HUFS 주간 범위**: HUFS 폼은 같은 달 내로 범위를 잘라서 보냅니다 (예: 4/26~4/30 이후의 5/1·5/2는 미포함). 월 경계 주에는 이번 주의 5월 분이 빠질 수 있습니다 — 페이지 자체 동작과 동일.
- **HUFS 메뉴 미공개**: 메뉴 미등록 셀은 "—"로 채워집니다. 전 주 메뉴가 비어 있으면 표가 거의 비어 보일 수 있습니다.
- **이미지 품질**: imweb 측은 `cdn.imweb.me/thumbnail/...` 경로로 서빙하므로 원본보다 다소 압축된 썸네일일 수 있습니다.
- **PNG export 권한**: 임시 Sheets PNG export는 `ScriptApp.getOAuthToken()`로 자기 자신에 대한 인증 호출입니다. `spreadsheets`, `drive` 스코프 승인이 필수.
- **첨부 합산 25MB 제한**: Gmail 첨부 합계 25MB 초과 시 발송 실패. 정상 메뉴 이미지는 수백KB 수준이라 거의 문제 없음.
- **외국어 미사용 원칙(#37)**: 본 스크립트의 사이트 응답 자체에는 한자가 일부 섞일 수 있으나(원문 그대로), 노트가 아닌 메일 첨부이므로 그대로 전달합니다.

## 파일 구성

```
meal-menu-apps-script/
├── Code.gs            # 본체 스크립트
├── appsscript.json    # 매니페스트 (시간대, OAuth 스코프)
├── README.md          # 이 문서
└── .clasp.json        # (선택) clasp CLI 사용자용 템플릿
```

### clasp CLI로 배포하는 경우 (선택)

```bash
npm i -g @google/clasp
clasp login
clasp create --type standalone --title "Weekly Meal Menu"   # scriptId 자동 생성
# scriptId를 .clasp.json에 채워넣고
clasp push
```

`.clasp.json` 템플릿의 `<<SCRIPT_ID>>`를 실제 ID로 교체하면 `clasp push`로 동기화 가능합니다.
