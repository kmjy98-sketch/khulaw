const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, WidthType, ShadingType, VerticalAlign, BorderStyle,
} = require("docx");

// ---- layout ----
const KFONT = { ascii: "맑은 고딕", eastAsia: "맑은 고딕", hAnsi: "맑은 고딕" };
const CW = 9746; // content width (A4 11906 - 2*1080)
const border = { style: BorderStyle.SINGLE, size: 1, color: "B7B7B7" };
const borders = { top: border, bottom: border, left: border, right: border };

// inline **bold** parser -> TextRun[]
function rich(str, base = {}) {
  const parts = String(str).split(/\*\*(.+?)\*\*/g);
  const runs = [];
  parts.forEach((seg, i) => {
    if (seg === "") return;
    runs.push(new TextRun({ ...base, text: seg, bold: i % 2 === 1 ? true : !!base.bold }));
  });
  return runs.length ? runs : [new TextRun({ ...base, text: "" })];
}

function body(str, opts = {}) {
  return new Paragraph({ spacing: { after: 90, line: 268 }, children: rich(str, { size: 20 }), ...opts });
}
function item(str, ref, opts = {}) {
  return new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60, line: 264 }, children: rich(str, { size: 20 }), ...opts });
}
function sectionHeading(str) {
  return new Paragraph({
    spacing: { before: 260, after: 130 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 2 } },
    children: rich(str, { size: 26, bold: true }),
  });
}
function subHeading(str) {
  return new Paragraph({ spacing: { before: 140, after: 60 }, children: rich(str, { size: 22, bold: true }) });
}

function cell(content, w, { header = false, align = AlignmentType.LEFT } = {}) {
  const arr = Array.isArray(content) ? content : [content];
  const children = arr.map((s) =>
    new Paragraph({ alignment: align, spacing: { after: 0, line: 248 }, children: rich(s, { size: 19, bold: header }) })
  );
  return new TableCell({
    borders,
    width: { size: w, type: WidthType.DXA },
    shading: header ? { fill: "DCE6F1", type: ShadingType.CLEAR } : undefined,
    margins: { top: 55, bottom: 55, left: 95, right: 95 },
    verticalAlign: VerticalAlign.CENTER,
    children,
  });
}
function mkTable(widths, rows) {
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((r) => new TableRow({ children: r.cells.map((c, i) => cell(c, widths[i], { header: r.header, align: r.aligns ? r.aligns[i] : AlignmentType.LEFT })), tableHeader: !!r.header })),
  });
}

// ---- content ----
const kids = [];

// Title
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 }, children: rich("AI 활용 내역서", { size: 34, bold: true }) }));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 }, children: rich("로스쿨 AI 챌린지", { size: 22, bold: true, color: "444444" }) }));
kids.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: rich("사안: (주)페이핀 ‘핀링크 유럽’ 출시에 따른 다국적(EU·국내) 금융·개인정보 규제 자문", { size: 18, color: "666666" }) }));

// 1
kids.push(sectionHeading("1. 문제 분석 및 수행 절차 설계"));
kids.push(subHeading("문제의 이해"));
kids.push(body("본 과제는 국내 전자금융업자 (주)페이핀이 독일·프랑스·스페인 한인 교민을 대상으로 ‘핀링크 유럽’을 출시하면서 발생한 다국적 규제 리스크 전반에 대한 사내 법률 자문이다. 세 문항은 규율 법역(法域)과 쟁점이 구분된다."));
kids.push(item("**1문 — EU 금융규제**: 무인가 결제서비스 제공 및 BaFin 경고 서한 대응", "bul"));
kids.push(item("**2문 — EU 개인정보**: GDPR 위반 전수 진단·제재수준, 데이터 유출사고 대응, AWS 위탁 처리", "bul"));
kids.push(item("**3문 — 국내 규제**: 스크래핑 방식 계좌정보 수집의 적법성, 마이데이터 규제, 혁신금융서비스 만료 후 지위", "bul"));
kids.push(body("핵심 난점은 **동일한 행위라도 적용 법령이 EU·국내로 갈린다**는 점이다. 따라서 자문서가 공통으로 요구한 행위 유형 ― ① 크로스보더 송금, ② 계좌 잔액·거래내역 조회, ③ 유출 사고 ― 을 큰 목차로 두고, **행위 × 법역 매트릭스**로 쟁점을 배치하는 것을 설계의 축으로 삼았다."));
kids.push(subHeading("수행 절차 (6단계)"));
kids.push(item("**사실관계 구조화** — 회사·라이선스 현황, EU 진출 경위, 개인정보 처리 흐름(프랑크푸르트 저장 → 서울 복사), 사고 경위, 국내 스크래핑 방식을 쟁점 단위로 분해", "proc"));
kids.push(item("**쟁점–법령 매핑** — 행위별 적용 법령을 EU(PSD2·GDPR)와 국내(신용정보법·전자금융거래법·금융혁신지원특별법)로 분류", "proc"));
kids.push(item("**근거법령·판례 1차 리서치** — 조문번호·제재수준·관련 판례 후보 도출", "proc"));
kids.push(item("**자문서 초안 작성** — ‘위반 진단 → 근거법령 → 제재수준 → 대응방안·기한’ 구조로 문항별 작성", "proc"));
kids.push(item("**검증** — 법령 원문(법제처 국가법령정보센터·EUR-Lex)과 판례 사건번호 대조, 환각 제거", "proc"));
kids.push(item("**누락 쟁점 보완 재작성** — BaFin 무회신 가중 리스크, AWS 수탁 처리, 국내법 한정 검토를 후속 지시로 추가 반영", "proc"));

// 2
kids.push(sectionHeading("2. AI 활용 내역"));
kids.push(body("각 절차 단계에서의 AI 활용 범위는 다음과 같다."));
kids.push(mkTable([2400, 1250, 6096], [
  { header: true, aligns: [AlignmentType.LEFT, AlignmentType.CENTER, AlignmentType.LEFT], cells: ["절차 단계", "AI 활용도", "세부 과업"] },
  { aligns: [0, AlignmentType.CENTER, 0], cells: ["사실관계 구조화", "보조", "처리 흐름·쟁점 1차 분해 (최종 확정은 직접)"] },
  { aligns: [0, AlignmentType.CENTER, 0], cells: ["쟁점–법령 매핑", "◎ 핵심", "행위별 적용 법령·조문번호 후보 도출"] },
  { aligns: [0, AlignmentType.CENTER, 0], cells: ["근거법령·판례 리서치", "◎ 핵심", "PSD2/독일 ZAG, GDPR 조문, 신용정보법 마이데이터 조항, 제재 상한"] },
  { aligns: [0, AlignmentType.CENTER, 0], cells: ["자문서 초안 작성", "◎ 핵심", "문항별 목차 설계·문장화"] },
  { aligns: [0, AlignmentType.CENTER, 0], cells: ["누락 쟁점 보완", "◎ 핵심", "무회신 리스크·AWS 위탁·국내법 한정 재작성"] },
  { aligns: [0, AlignmentType.CENTER, 0], cells: ["검증·취사선택", "△ 제한", "법령 원문 대조·판례 진위 확인은 직접, AI는 교차질의 보조"] },
  { aligns: [0, AlignmentType.CENTER, 0], cells: ["최종 법리 판단", "✕ 미사용", "변호사 관점의 사안 적용·최종 판단은 직접 수행"] },
]));
kids.push(new Paragraph({ spacing: { before: 120, after: 90, line: 268 }, children: rich("요컨대 AI는 (i) 방대한 사실관계에서 **행위별 규제 쟁점을 빠짐없이 식별**하고, (ii) EU·국내 **근거 법령·조문을 1차 제시**하며, (iii) **자문서 형식으로 구조화**하는 단계에서 집중적으로 활용했다. 반면 법령 원문 확인, 판례 실재 여부, 사안 적용의 타당성에 대한 최종 판단은 직접 수행하여 AI를 보조 도구로 한정했다.", { size: 20 }) }));

// 3
kids.push(sectionHeading("3. AI 도구별 실제 수행 내역"));
kids.push(subHeading("(가) 생성형 AI ― 쟁점 분석 및 자문서 초안 생성"));
kids.push(body("문항별로 실제 입력한 프롬프트와 산출물은 다음과 같다."));
kids.push(mkTable([1150, 3900, 4696], [
  { header: true, aligns: [AlignmentType.CENTER, 0, 0], cells: ["문항", "입력(요지)", "산출물"] },
  { aligns: [AlignmentType.CENTER, 0, 0], cells: ["1문", "회사·EU 진출·개인정보 처리 현황 + “EU 금융규제 위반·BaFin 경고 대응 방안과 구체적 근거법령”", "무인가 결제서비스(PSD2 / 독일 ZAG) 위반 진단, 행위별(①송금=자금이체·송금업, ②조회=계좌정보서비스 AIS) 근거법령 정리, 대응 로드맵"] },
  { aligns: [AlignmentType.CENTER, 0, 0], cells: ["1문 후속", "“①송금·②조회를 큰 목차로 한 행위별 위반 자문서” / “BaFin 2주 무회신 문제”", "행위별 재구조화 + 무회신 시 시정명령·과태료·형사책임·영업금지 등 **가중 리스크** 추가"] },
  { aligns: [AlignmentType.CENTER, 0, 0], cells: ["2문", "1문 사실관계 + 유출사고 + “GDPR 위반 전수 진단·조문·제재수준 + 유출사고 조치·기한”", "GDPR 역외적용(제3조), 적법근거·투명성(제6·12~14조), 대리인·DPO·처리기록(제27·37·30조), 국외이전(제44조 이하), 유출통지(제33조 72시간/제34조), 과징금(제83조)"] },
  { aligns: [AlignmentType.CENTER, 0, 0], cells: ["2문 후속", "“AWS 위탁 쟁점을 넣어 처음부터 재작성”", "수탁자(처리자) 지위·제28조 위탁계약(DPA)·서울 리전 재이전 쟁점 통합"] },
  { aligns: [AlignmentType.CENTER, 0, 0], cells: ["3문", "사실관계 + 스크래핑·마이데이터·샌드박스 만료 + “국내법 3목차 자문서”", "스크래핑 수집의 신용정보법·전자금융거래법·정보통신망법 쟁점, 마이데이터(본인신용정보관리업) 허가·API 의무, 혁신금융서비스 만료 후 무인가 영업 리스크"] },
  { aligns: [AlignmentType.CENTER, 0, 0], cells: ["3문 후속", "“외국법 제외, 국내 판례·법규 중심 재검토”", "EU 논의 제거 후 국내 법령·판례 중심으로 재작성"] },
]));
kids.push(subHeading("(나) 법령·판례 검증 도구"));
kids.push(item("**법제처 국가법령정보센터(Open API)**: 국내 법령 조문·시행일·판례 사건번호를 실시간 대조 (신용정보법, 전자금융거래법, 금융혁신지원특별법, 개인정보보호법)", "bul"));
kids.push(item("**EUR-Lex 및 감독기구 공개자료**: GDPR·PSD2 원문 조문 번호·문언, 독일 ZAG 대응 조항 확인", "bul"));

// 4
kids.push(sectionHeading("4. AI 답변 검증"));
kids.push(subHeading("검증 방법"));
kids.push(item("**법령 1차출처 대조** — AI가 제시한 모든 조문은 원문에서 직접 확인. 국내법은 국가법령정보센터, EU법은 EUR-Lex 원문과 조문번호·문언을 대조하고, 일치하지 않으면 정정 또는 삭제했다.", "verify"));
kids.push(item("**판례 실재성 검증** — 사건번호가 제시된 판례는 번호·선고일·법원·요지를 원전에서 확인. 검색되지 않거나 쟁점이 상이하면 자문서에서 삭제하고 ‘확인 불가’로 처리했다.", "verify"));
kids.push(item("**제재수준 수치 검증** — 과징금 상한(GDPR 제83조 €2천만 또는 전세계 매출 4% 등)·통지 기한(72시간) 등 수치는 조문 문언으로 재확인했다.", "verify"));
kids.push(item("**교차 질의** — 동일 쟁점을 달리 질의해 답변 일관성을 점검하고, 불일치 시 원문을 우선했다.", "verify"));
kids.push(subHeading("환각·오류 발견 및 대응 사례"));
kids.push(mkTable([1850, 3500, 4396], [
  { header: true, aligns: [0, 0, 0], cells: ["유형", "AI 답변", "검증 결과 및 대응"] },
  { aligns: [0, 0, 0], cells: ["판례 사건번호 환각", "스크래핑·정보통신망 무단접근 관련 국내 판례를 구체 사건번호와 함께 제시", "국가법령정보센터 검색 결과 일부 번호가 실재하지 않거나 쟁점 불일치 → 해당 인용을 삭제하고 확인된 법령 조문 중심으로 대체"] },
  { aligns: [0, 0, 0], cells: ["조문번호 부정확", "마이데이터의 스크래핑 금지·API 의무 근거를 부정확한 조항으로 인용", "신용정보법상 본인신용정보관리업 관련 조문 및 감독규정으로 정정"] },
  { aligns: [0, 0, 0], cells: ["사실 오인(법리 단정)", "한국행(서울 리전) 데이터 이전을 일률적으로 GDPR 위법으로 단정", "EU의 **한국 적정성 결정(2021.12)**으로 별도 안전장치 없이 이전 가능함을 반영해 수정. 다만 당초 수집목적과 다른 AI 학습 목적 이용은 목적제한 원칙(제5조)상 별도 쟁점으로 구분"] },
]));
kids.push(new Paragraph({ spacing: { before: 120, after: 60, line: 268 }, children: rich("검증 결과 AI는 **체계·조문 후보 제시에는 유용하나, 구체적 판례 인용과 사안 포섭에서 환각·오류 가능성이 있다**고 판단하여, 모든 법령·판례는 1차출처 확인을 거친 것만 자문서에 반영하고 최종 법리 판단은 직접 수행했다.", { size: 20 }) }));

// ---- document ----
const doc = new Document({
  styles: { default: { document: { run: { font: KFONT, size: 20 } } } },
  numbering: {
    config: [
      { reference: "proc", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 300 } } } }] },
      { reference: "verify", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 460, hanging: 300 } } } }] },
      { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 420, hanging: 260 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } } },
    children: kids,
  }],
});

const OUT = "H:/내 드라이브/5.기타/문서/AI활용내역서_로스쿨AI챌린지.docx";
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("WROTE " + OUT + " (" + buf.length + " bytes)"); });
