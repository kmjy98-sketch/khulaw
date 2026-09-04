export const meta = {
  name: 'ox-cloze-pilot',
  description: 'OX 카드에 병렬 클로즈(정답 완성문) 추가 — 파일럿 2파일, X거짓선지는 뒤 정답으로',
  phases: [ { title: 'AddCloze' }, { title: 'Verify' } ],
}

const CARD = 'H:/내 드라이브/outputs/02_cards_v37'
const BK = 'H:/내 드라이브/5.기타/_백업/OX클로즈_2026-06-22'
const items = [
  { file: '강성민OX3_llamaparse_p001-030_암기장_v37.md' },
  { file: '법조윤리_01.md' },
].map(i => ({ ...i, path: `${CARD}/${i.file}`, bak: `${BK}/${i.file}` }))

function addPrompt(it) { return [
  '역할: v37 암기장 OX 카드에 「병렬 클로즈」(정답 회상 완성문)를 추가하는 정밀 편집자. OX 인식 카드(앞=선지/뒤=O·X+근거)는 그대로 두고, 정답 회상용 클로즈를 `빈칸:` 필드로 추가한다. 법리 내용 불변.',
  `대상 파일(Read 후 같은 경로 Write): ${it.path}`,
  '',
  '각 `### [OX...]` 카드 중 본문에 `{{`(클로즈)가 없는 것만 대상:',
  "1) 뒤(뒷면)에서 '참인 정답'을 파악: 뒤가 'O'면 앞 선지가 참 / 'X'면 뒤에 적힌 교정 내용이 참.",
  '2) 그 정답을 담은 자연스러운 한 문장을 만들고, 핵심구(개념·요건·기준·결론) 1~3개를 `{{c1::}}`..로 감싸 그 카드에 **`빈칸:` 필드로 추가**(앞·뒤는 그대로).',
  '   ⚠필수 안전장치: **X(거짓) 선지 문장 자체를 클로즈하지 말 것.** 반드시 뒤의 「교정된 정답」으로 완성문을 만든다.',
  '     예: 앞="…직접성을 인정할 수 있다 (X)" / 뒤="…인정되지 않는다" → 빈칸:"…직접성을 {{c1::인정할 수 없다}}."',
  '   - 조문번호(제○조)·사건번호(○○헌○○/○○다○○)는 빈칸 밖 평문 보존(anchor). 조사·어미 파편 금지(체언/결론술어 종결). 빈칸 2~4개 이내, 상호 독립.',
  '   - 정답이 단순 사실확인이라 가릴 핵심구가 없거나 완성문이 어색하면 그 카드는 건드리지 말 것(skipped).',
  '3) 이미 `{{}}` 있는 카드, `[OX]`가 아닌 카드(일반론/포섭/예외/요건 등)는 절대 손대지 않는다.',
  '',
  '절대 금지: 앞·뒤 법리 텍스트 변경, 새 사실 생성, 헤딩/frontmatter 변경, 카드 삭제. 확신 없으면 그 카드는 그대로 둔다.',
  '작업: 파일 Read → 위 규칙대로 `빈칸:` 추가 → 같은 경로 Write(백업 완료됨). 그다음 다시 Read해 (a)앞·뒤 불변 (b)X카드가 거짓 아닌 정답을 클로즈했는지 자가검증. JSON 반환.',
].join('\n') }

function verifyPrompt(it) { return [
  '역할: OX 병렬 클로즈 추가 결과를 검수. 특히 X(거짓) 선지를 잘못 클로즈해 틀린 법리를 외우게 만들지 않았는지 본다.',
  `대상: ${it.path} / 백업원본: ${it.bak}`,
  '두 파일 Read 비교: ①앞·뒤 법리 텍스트가 그대로인지(빈칸 필드 추가 외 변경 없어야 ok) ②새로 추가된 `빈칸:` 완성문이 뒤의 「참인 정답」과 일치하는지(X카드에서 거짓 선지를 클로즈했으면 bad) ③조문·사건번호가 빈칸 밖인지.',
  'JSON 반환.',
].join('\n') }

const ADD_SCHEMA = { type:'object', additionalProperties:false,
  required:['file','ox_total','cloze_added','skipped','content_unchanged'],
  properties:{ file:{type:'string'}, ox_total:{type:'integer'}, cloze_added:{type:'integer'},
    skipped:{type:'integer'}, x_cards_handled:{type:'integer'}, content_unchanged:{type:'boolean'},
    notes:{type:'string'}, samples:{type:'array', items:{type:'string'}, description:'앞/뒤→추가한 빈칸 예 2개(X카드 1개 포함)'} } }
const VERIFY_SCHEMA = { type:'object', additionalProperties:false,
  required:['file','legal_text_intact','x_handling_ok','verdict'],
  properties:{ file:{type:'string'}, legal_text_intact:{type:'boolean'}, x_handling_ok:{type:'boolean'},
    cloze_valid:{type:'boolean'}, issues:{type:'array', items:{type:'string'}},
    verdict:{type:'string', enum:['ok','warn','bad']} } }

log(`OX 병렬 클로즈 파일럿: ${items.length}파일`)
const results = await pipeline(items,
  (it) => agent(addPrompt(it), { label:`add:${it.file.slice(0,24)}`, phase:'AddCloze', schema:ADD_SCHEMA, effort:'high', agentType:'general-purpose' }).then(r=>({it,add:r})),
  (prev, it) => (!prev||!prev.add) ? { file:it.file, add:null, verify:null }
      : (prev.add.cloze_added === 0) ? { file:it.file, add:prev.add, verify:null }   // 추가 0이면 검증 생략
      : agent(verifyPrompt(it), { label:`verify:${it.file.slice(0,20)}`, phase:'Verify', schema:VERIFY_SCHEMA, effort:'high', agentType:'general-purpose' }).then(v=>({file:it.file, add:prev.add, verify:v}))
)
const ok = results.filter(Boolean)
return { files: ok.length,
  total_added: ok.reduce((a,r)=>a+(r.add&&r.add.cloze_added||0),0),
  bad: ok.filter(r=>r.verify&&r.verify.verdict==='bad').map(r=>r.file),
  per_file: ok.map(r=>({ file:r.file, ox:r.add&&r.add.ox_total, added:r.add&&r.add.cloze_added,
    skipped:r.add&&r.add.skipped, x:r.add&&r.add.x_cards_handled, content_unchanged:r.add&&r.add.content_unchanged,
    verify:r.verify&&r.verify.verdict, x_ok:r.verify&&r.verify.x_handling_ok, samples:r.add&&r.add.samples })) }
