// case-answer-panel-grade — 사례형 답안 패널 채점 워크플로 (2026-06-23 검증)
// 사용: Workflow({name:"case-answer-panel-grade", args:{과목,문제,해설,답안,배점표?}})
//   args 미지정 시 사례1(민사사례연습1) 데모로 실행.
// 원칙: 해설=절대 기준(#1). 채점관 프롬프트는 .agent/skills/case-answer-review/채점관_프롬프트_v1.md.
export const meta = {
  name: 'case-answer-panel-grade',
  description: '사례형 답안 패널 채점: 해설 원문 기준 채점관 3명 병렬 → 집계(등급 다수결·약점 합집합) → review_type·초기 due 매핑 → 복습 등록안',
  phases: [
    { title: 'Panel', detail: '독립 채점관 3명이 해설 기준으로 병렬 채점' },
    { title: 'Aggregate', detail: '등급 다수결·약점 합집합·불일치 표출(JS)' },
    { title: 'Synthesize', detail: '약점 dedup + review_type 배정 → 복습 등록안' },
  ],
}

const DEMO = {
  과목: '민법',
  문제: '甲·乙이 A토지를 공유. 甲이 공유물분할등기 신청을 乙에게 맡기며 서류·인감 교부. 乙이 이를 이용해 甲 지분 포함 A토지 전부를 丙에게 매도·이전등기. 丙은 A토지 소유권을 취득하는가? (15점)',
  해설: `I. 논점정리: ㉠ 공유자 甲의 동의 없이 이루어진 乙의 공유토지 처분행위의 효력, ㉡ 甲의 지분 처분행위와 민법 제126조 성립가능성
II. 공유토지 처분행위의 효력: 공유자 중 1인이 다른 공유자의 동의 없이 공유물 전부를 처분한 경우에도 처분공유자의 지분범위 내에서는 유효한 처분행위. ∴ 乙의 지분에 한해서는 유효.
III. 甲 지분과 민법 제126조: ① 제126조 표현대리는 권한 외 법률행위 + 정당한 이유로 성립하며, 권리외관 창출에 '본인의 귀책'이 필요. ② '정당한 이유'는 보통의 주의력을 가진 사람이 대리권 존재를 믿는 데 과실 없는 경우(선의·무과실)이며, 입증책임은 '계약의 유효를 주장하는 자'에게 있다. [사안검토] ㉠ 분할등기 신청권=기본대리권, ㉡ 등기 넘어 매매=권한 외, ㉢ 丙은 서류·인감 지닌 乙을 믿어 과실 없음, ㉣ 甲의 서류·인감 교부=본인의 귀책. ∴ 제126조 표현대리 성립.
IV. 결론: 丙은 A토지 전부에 대해 완전한 소유권을 취득.`,
  배점표: '없음 — 항목별 O/△/X만',
  답안: `乙이 甲 동의 없이 공유토지 전부를 처분했으나 자기 지분 범위에선 유효하다. 甲 지분은 무권대리이나 민법 제126조 표현대리가 문제된다. 乙은 공유물분할등기 신청권이라는 기본대리권이 있었고, 이를 넘어 매매하였으며, 丙은 등기서류와 인감을 지닌 乙을 권한 있다고 믿을 정당한 이유가 있었다. 따라서 제126조 표현대리가 성립하여 丙은 A토지 전부를 취득한다.`,
}
const I = (args && args.해설) ? args : DEMO
const DUE = { issue_spotting: 1, conclusion_drill: 1, keyword_recall: 2, mini_application: 2, outline_recall: 3, stable: 7 }

const GRADER_PROMPT = `역할: 너는 변호사시험 ${I.과목} 사례형 답안 채점관이다. 아래 [해설]을 절대 기준으로 [학생답안]을 채점한다.

철칙:
1. [해설]이 정답이다. 의심·수정·반박 금지. 네 법지식이 해설과 달라도 해설을 따른다.
2. 감점·누락 단정에는 반드시 [해설]의 해당 부분을 직접 발췌 인용한다. 해설에 근거 없는 감점 금지.
3. [해설]에 없는 쟁점으로 학생을 평가하지 않는다. 학생이 해설에 없는 말을 했으면 '해설 외'로만 표기.
4. 한국어. 추측 금지.

[문제]
${I.문제}

[해설(모범답안) — 절대 기준]
${I.해설}

[배점표]
${I.배점표 || '없음 — 항목별 O/△/X만'}

[학생답안]
${I.답안}

[채점] 각 항목 O(충족)/△(부분)/X(누락) + 해설 발췌 근거.
출력 키 매핑: issue=쟁점포착, law=법리, application=포섭, conclusion=결론.
각 항목은 verdict(O/△/X)와 basis(해설 발췌). weaknesses=해설 기준 누락 약점(문자열 배열). grade=종합 등급(O/△/X). comment=총평.
※ 헌법 결론-예외는 미적용 — 결론은 해설 기준.`

const dim = { type: 'object', properties: { verdict: { type: 'string', enum: ['O', '△', 'X'] }, basis: { type: 'string' } }, required: ['verdict', 'basis'] }
const GRADER_SCHEMA = {
  type: 'object',
  properties: {
    issue: dim, law: dim, application: dim, conclusion: dim,
    weaknesses: { type: 'array', items: { type: 'string' } },
    grade: { type: 'string', enum: ['O', '△', 'X'] },
    comment: { type: 'string' },
  },
  required: ['issue', 'law', 'application', 'conclusion', 'weaknesses', 'grade'],
}

phase('Panel')
const verdicts = (await parallel([1, 2, 3].map(n => () =>
  agent(GRADER_PROMPT, { label: `채점관:${n}`, phase: 'Panel', schema: GRADER_SCHEMA })
))).filter(Boolean)

if (verdicts.length < 2) return { error: '채점관 응답 부족', got: verdicts.length }

phase('Aggregate')
const DIMS = ['issue', 'law', 'application', 'conclusion']
const KO = { issue: '쟁점', law: '법리', application: '포섭', conclusion: '결론' }
const RANK = { O: 3, '△': 2, X: 1 }
function majority(values) {
  const cnt = {}
  for (const v of values) cnt[v] = (cnt[v] || 0) + 1
  const max = Math.max(...Object.values(cnt))
  const top = Object.keys(cnt).filter(k => cnt[k] === max).sort((a, b) => RANK[a] - RANK[b])
  return { value: top[0], split: top.length > 1 || max < values.length, dist: cnt }
}
const dimResult = {}
for (const d of DIMS) dimResult[d] = majority(verdicts.map(v => v[d].verdict))
const overall = majority(verdicts.map(v => v.grade))
const allWeak = verdicts.flatMap(v => v.weaknesses || [])
const disagreements = [...DIMS.filter(d => dimResult[d].split).map(d => KO[d]), ...(overall.split ? ['등급'] : [])]
log(`패널 ${verdicts.length}명 · 등급분포 ${JSON.stringify(overall.dist)} · 불일치 ${disagreements.length ? disagreements.join(',') : '없음'}`)

phase('Synthesize')
const SYN_SCHEMA = {
  type: 'object',
  properties: {
    weaknesses: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          text: { type: 'string' },
          review_type: { type: 'string', enum: ['issue_spotting', 'conclusion_drill', 'keyword_recall', 'mini_application', 'outline_recall', 'stable'] },
        },
        required: ['text', 'review_type'],
      },
    },
    comment: { type: 'string' },
  },
  required: ['weaknesses', 'comment'],
}
const syn = await agent(
  `너는 채점 집계자다. 아래 3명 채점관의 누락 약점을 **의미 기준으로 중복 제거**해 합집합을 만들고, 각 약점에 복습 유형(review_type)을 배정하라. 노이즈("약점 아님" 등)는 제외.

review_type 기준: 쟁점 못 찾음→issue_spotting / 목차·구조 누락→outline_recall / 법리·키워드(정의·요건·입증책임)→keyword_recall / 결론 반대·오류→conclusion_drill / 포섭(사실↔법리) 약함→mini_application.

채점관별 누락 약점:
${verdicts.map((v, i) => `[채점관${i + 1}] ${JSON.stringify(v.weaknesses)}`).join('\n')}

종합 등급=${overall.value}, 항목=${JSON.stringify(Object.fromEntries(DIMS.map(d => [KO[d], dimResult[d].value])))}.
약점 합집합(text)·review_type·1줄 총평(comment)을 한국어로.`,
  { label: '집계', phase: 'Synthesize', schema: SYN_SCHEMA }
)

const 복습등록안 = (syn?.weaknesses || []).map(w => ({ 약점: w.text, review_type: w.review_type, 초기_due: `D+${DUE[w.review_type] ?? 1}` }))

return {
  과목: I.과목,
  채점관수: verdicts.length,
  등급: overall.value,
  등급분포: overall.dist,
  항목판정: Object.fromEntries(DIMS.map(d => [KO[d], { 판정: dimResult[d].value, 분포: dimResult[d].dist }])),
  검토필요_불일치: disagreements.length ? disagreements : '없음',
  복습등록안,
  총평: syn?.comment || '',
  약점_원천: allWeak,
}
