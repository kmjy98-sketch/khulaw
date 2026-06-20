// 마크다운 답안/검토의견서 -> docx 제출본 (법무 서면용, Python 불가 환경 표준)
// usage: node md_to_docx.js <in.md> <out.docx> [bodyPt=12] [linePct=160]
//   bodyPt  : 본문 글꼴 pt (제목=+2pt, 표=본문-1.5pt 근사)
//   linePct : 줄간격 % (160=가인 기본값)
// 분량 초과 시: 양식 미지정 대회는 bodyPt/linePct를 낮춰 재생성(예: 10.5 / 120). 페이지 캡이 구속.
// 면수 실측(Word COM): $w=New-Object -ComObject Word.Application; $d=$w.Documents.Open($out);
//                      $d.ComputeStatistics(2)  # wdStatisticPages → 캡 비교
// 의존: docx 패키지를 C: 로컬에 설치 (H:/구글드라이브 경로는 npm install 깨짐)
//   New-Item -ItemType Directory -Force C:\Users\<u>\docx_build; cd ...; npm init -y; npm install docx
//   실행: $env:NODE_PATH='C:\Users\<u>\docx_build\node_modules'; node '<repo>\.agent\scripts\md_to_docx.js' in.md out.docx 10.5 120
//   ※ require('docx')는 스크립트 위치 기준으로 해석된다 → NODE_PATH로 C: node_modules를 지정(또는 스크립트를 빌드폴더에 복사 후 실행). cwd는 무관.
// 서식: A4·여백 20mm·맑은 고딕·양쪽맞춤·표 자동(가인 D절). 최종은 한글에서 열어 HWP/HWPX 저장·매수 실측.
const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, AlignmentType, Table, TableRow, TableCell, WidthType, BorderStyle, convertMillimetersToTwip } = require('docx');

const FONT = 'Malgun Gothic';
const bodyPt = parseFloat(process.argv[4] || '12');
const linePct = parseFloat(process.argv[5] || '160');
const BODY = Math.round(bodyPt * 2);
const H1 = Math.round((bodyPt + 2) * 2);
const H2 = Math.round((bodyPt + 1) * 2);
const H3 = BODY;
const LINE = Math.round(240 * linePct / 100);
const CELL = Math.max(16, Math.round((bodyPt - 1.5) * 2));

const inPath = process.argv[2], outPath = process.argv[3];
let md = fs.readFileSync(inPath, 'utf8');
if (md.startsWith('---')) { const m = md.match(/^---\r?\n[\s\S]*?\r?\n---\r?\n/); if (m) md = md.slice(m[0].length); }
const lines = md.split(/\r?\n/);

function runs(text, opt = {}) {
  const size = opt.size || BODY, baseBold = !!opt.bold, out = [];
  String(text).split('**').forEach((p, i) => { if (p !== '') out.push(new TextRun({ text: p, bold: baseBold || (i % 2 === 1), font: FONT, size })); });
  if (out.length === 0) out.push(new TextRun({ text: '', font: FONT, size }));
  return out;
}
const b = { style: BorderStyle.SINGLE, size: 2, color: '888888' };
const cb = { top: b, bottom: b, left: b, right: b };
const children = []; let tbuf = [];
function flushTable() {
  if (!tbuf.length) return;
  const rows = tbuf.filter(r => !/^\s*\|[\s:|-]+\|\s*$/.test(r)).map(r => r.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(c => c.trim()));
  const n = Math.max(...rows.map(c => c.length));
  children.push(new Table({ width: { size: 100, type: WidthType.PERCENTAGE }, rows: rows.map((arr, ri) => new TableRow({ tableHeader: ri === 0, children: Array.from({ length: n }, (_, ci) => new TableCell({ borders: cb, margins: { top: 40, bottom: 40, left: 80, right: 80 }, children: [new Paragraph({ spacing: { line: 264, lineRule: 'auto' }, children: runs(arr[ci] || '', { size: CELL, bold: ri === 0 }) })] })) })) }));
  children.push(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: '', font: FONT, size: BODY })] }));
  tbuf = [];
}
for (const raw of lines) {
  const line = raw.replace(/\s+$/, ''), t = line.trim();
  if (t.startsWith('|')) { tbuf.push(line); continue; }
  flushTable();
  if (t === '' || t === '---') continue;
  if (line.startsWith('# ')) children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 240, after: 200, line: LINE, lineRule: 'auto' }, children: runs(line.slice(2), { bold: true, size: H1 }) }));
  else if (line.startsWith('## ')) children.push(new Paragraph({ spacing: { before: 160, after: 80, line: LINE, lineRule: 'auto' }, children: runs(line.slice(3), { bold: true, size: H2 }) }));
  else if (line.startsWith('### ')) children.push(new Paragraph({ spacing: { before: 110, after: 50, line: LINE, lineRule: 'auto' }, children: runs(line.slice(4), { bold: true, size: H3 }) }));
  else children.push(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 0, line: LINE, lineRule: 'auto' }, children: runs(line) }));
}
flushTable();
const doc = new Document({ styles: { default: { document: { run: { font: FONT, size: BODY } } } }, sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: convertMillimetersToTwip(20), right: convertMillimetersToTwip(20), bottom: convertMillimetersToTwip(20), left: convertMillimetersToTwip(20) } } }, children }] });
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(outPath, buf); console.log('WROTE ' + outPath + ' (' + buf.length + ' bytes, body ' + bodyPt + 'pt / line ' + linePct + '%)'); }).catch(e => { console.error('ERR', e); process.exit(1); });
