export const meta = {
  name: 'cloze-fix',
  description: 'v37 카드 클로즈 결함 전수 수정(마커 [...]/【】→{{}}, 파편 경계, anchor 제외) — 법리 내용 불변, 사전 백업',
  phases: [ { title: 'Fix' }, { title: 'Verify' } ],
}

// args = { items: [{file, path, flags}], verify_sample: <int> }
const items = [{"file": "신민사법선택형_가족법_llamaparse_p061-090_암기장_v37.md", "path": "H:/내 드라이브/outputs/02_cards_v37/신민사법선택형_가족법_llamaparse_p061-090_암기장_v37.md", "flags": "빈칸라벨_있으나_cloze070"}, {"file": "논점민소_p421-450_cloze_v37.md", "path": "H:/내 드라이브/outputs/02_cards_v37/논점민소_p421-450_cloze_v37.md", "flags": "빈칸라벨_있으나_cloze062"}]
const SAMPLE = 2
const PASS2 = true

function fixPrompt(it) { return [
  '역할: v37 Anki 카드 파일의 클로즈 결함만 고치는 정밀 편집자. 법리(요건·판례문구·결론)의 내용은 절대 바꾸지 않는다.',
  `대상 파일(Read 후 같은 경로에 Write): ${it.path}`,
  `이 파일 감사 플래그: ${it.flags}`,
  '',
  '수정 대상 = 클로즈 메커니즘만:',
  '1) 마커 통일: 클로즈 타겟이 `[내용]`(대괄호) 또는 `【내용】`(전각)으로 표시돼 있으면 `{{내용}}`로 바꾼다.',
  '   - 빈칸 필드가 빈 대괄호 `[　　]`(안에 내용 없이 공백·전각공백만 — 채우기형)면, 뒷면(뒤) 필드에서 그 자리에 들어갈 정답 어구를 특정해 `{{정답}}`으로 채운다. 뒤에서 정답을 명확히 특정할 수 없으면 그 카드는 그대로 두고 notes에 보고한다(추측 금지).',
  '   - 단, 다음은 클로즈가 아니므로 그대로 둔다: `[A]`/`[B]`/`[C]`/`[D]`, `[OX-N]`, `[일반론]`/`[포섭]`/`[예외]`/`[요건]`/`[함정]`/`[기재례]`, `[변NN]`/`[N변시]` 등 난이도·속성·출처·기출 태그, 그리고 `(난이도 A)` 같은 메타.',
  '   - 헤딩 줄(`### [속성] ...`, `## ...`)과 frontmatter는 절대 건드리지 않는다.',
  (typeof PASS2 !== "undefined" && PASS2) ?
  '   - [PASS2] 앞면(선지)에 빈 괄호 `( )`가 있고 빈칸 필드에 정답 키워드가 있으면: 원 OX 카드(앞→뒤)는 그대로 두고, **빈칸 필드를 「앞면 문장의 `( )`에 `{{키워드}}`를 넣은 완성문」으로 교체**한다(빌더 DOUBLE이 OX-Basic + Cloze 둘 다 생성 = 중복 의도). `( )`가 여러 개면 빈칸 ①②③ 순서로 매핑. 정답을 빈칸 키워드/뒤에서 특정 못하면 그 카드 보류.' : '',
  '2) 파편 교정: 클로즈가 조사·연결어미로 끝나면(…를/…을/…으로/…고/…며/…관한/…위한/…하여 등) 빈칸 범위를 체언 또는 결론술어 경계로 좁힌다. 예: `{{인정할 수 없다고}}`→`{{인정할 수 없다}}`(고는 밖), `{{명확하지 않으므로}}`→`{{명확하지 않}}`은 금지(어색)—이 경우 `{{명확하지 않다}}`처럼 자연스러운 종결로. 빈칸 가린 뒤 문장 골격이 남아야 한다.',
  '3) anchor 제외: 클로즈 안에 조문번호(제○조)·사건번호(○○다/도/두/헌○○)가 들어가 있으면 그 anchor를 빈칸 밖 평문으로 빼고, 빈칸은 그 조문·판례가 담는 법리 내용에 건다. 예: `{{민법 제103조 위반}}`→`{{사회질서 위반}}으로 무효(민법 제103조)`.',
  '4) 한 카드 빈칸 5개 이상이면 핵심 2~4개만 남긴다(의미 훼손 없이).',
  '',
  '절대 금지: 법리·요건·판례문구·결론의 내용 변경/추가/삭제, 새 사실 생성, 앞·뒤의 법적 텍스트를 클로즈 마커 교체 외로 수정, 헤딩/frontmatter 변경. 누설은 명백할 때만 손대고 애매하면 둔다. 확신 없으면 그 카드는 건드리지 말 것.',
  '',
  '작업: 파일 Read → 규칙대로 클로즈만 수정 → 같은 경로 Write(백업은 이미 완료됨). 그다음 다시 Read해 (a)법적 텍스트 불변 (b)모든 {{}} 내용 있음 (c)헤딩·frontmatter 불변 자가검증. JSON 반환.',
].join('\n') }

const FIX_SCHEMA = { type:'object', additionalProperties:false,
  required:['file','edits_made','content_unchanged'],
  properties:{
    file:{type:'string'}, edits_made:{type:'integer'},
    marker_fixed:{type:'integer'}, fragment_fixed:{type:'integer'}, anchor_fixed:{type:'integer'},
    overcloze_fixed:{type:'integer'}, content_unchanged:{type:'boolean'},
    notes:{type:'string'}, samples:{type:'array', items:{type:'string'}, description:'수정 전→후 예 2개'} } }

const VERIFY_SCHEMA = { type:'object', additionalProperties:false,
  required:['file','legal_text_intact','verdict'],
  properties:{ file:{type:'string'}, legal_text_intact:{type:'boolean'},
    cloze_valid:{type:'boolean'}, issues:{type:'array', items:{type:'string'}},
    verdict:{type:'string', enum:['ok','warn','bad']} } }

log(`클로즈 수정 전수: ${items.length}파일 (백업 완료 가정)`)

const results = await pipeline(items,
  (it) => agent(fixPrompt(it), { label:`fix:${it.file.slice(0,28)}`, phase:'Fix', schema:FIX_SCHEMA, effort:'medium', agentType:'general-purpose' })
            .then(r => ({ it, fix:r })),
  (prev, it, idx) => {
    // 표본만 적대적 검증(법리 텍스트 보존 확인)
    if (!prev || !prev.fix) return { file:it.file, fix:null, verify:null }
    if (SAMPLE && (idx % Math.max(1, Math.floor(items.length / SAMPLE)) === 0)) {
      return agent([
        '역할: 카드 수정 후 법리 텍스트가 보존됐는지 확인하는 검수자.',
        `대상: ${it.path}  / 백업원본: H:/내 드라이브/5.기타/_백업/카드클로즈수정_2026-06-22/${it.file}`,
        '두 파일을 Read해 비교: 클로즈 마커({{}})·빈칸 경계 외에 법리/요건/판례문구/결론 텍스트가 바뀌었는지. 바뀌었으면 bad. 마커·경계만 바뀌었으면 ok.',
        'JSON 반환.',
      ].join('\n'), { label:`verify:${it.file.slice(0,24)}`, phase:'Verify', schema:VERIFY_SCHEMA, effort:'medium', agentType:'general-purpose' })
        .then(v => ({ file:it.file, fix:prev.fix, verify:v }))
    }
    return { file:it.file, fix:prev.fix, verify:null }
  }
)

const ok = results.filter(Boolean)
const totalEdits = ok.reduce((a,r)=> a + (r.fix && r.fix.edits_made || 0), 0)
const contentChanged = ok.filter(r=> r.fix && r.fix.content_unchanged === false)
const verifyBad = ok.filter(r=> r.verify && r.verify.verdict === 'bad')
log(`수정 완료: ${ok.length}파일, 편집 ${totalEdits}건. 내용변경의심 ${contentChanged.length}, 검증bad ${verifyBad.length}`)

return {
  files: ok.length, total_edits: totalEdits,
  content_changed_flags: contentChanged.map(r=>r.file),
  verify_bad: verifyBad.map(r=>({file:r.file, issues:r.verify.issues})),
  per_file: ok.map(r=>({ file:r.file, edits:r.fix&&r.fix.edits_made,
    marker:r.fix&&r.fix.marker_fixed, frag:r.fix&&r.fix.fragment_fixed, anchor:r.fix&&r.fix.anchor_fixed,
    content_unchanged:r.fix&&r.fix.content_unchanged, verify:r.verify&&r.verify.verdict })),
}
