# Master Runner — 2026-04-29
# 1. sync_organize_2026-04-29.ps1
# 2. rename_헌법사례형_2026-04-29.ps1
# 3. Critical 3건 이동 (무제, Gemini_위임_병행_검토, Colab_ocr_드라이런_검토)
# 4. Gemini CLI 파일럿 호출 (방위산업 계약해제)
# 원칙: CLAUDE.md #15 (verify-before-act), #16 (Move only, 삭제 금지)

$ErrorActionPreference = "Continue"
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
chcp 65001 | Out-Null

$log = "H:\내 드라이브\_run_master_log_2026-04-29.txt"
Start-Transcript -Path $log -Force | Out-Null

Write-Host "=== Master 실행 시작: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan

# ---------- [1] sync_organize ----------
Write-Host "`n--- [1] sync_organize_2026-04-29.ps1 ---" -ForegroundColor Cyan
try {
    & "H:\내 드라이브\sync_organize_2026-04-29.ps1"
    Write-Host "[OK] sync_organize 완료" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] sync_organize: $_" -ForegroundColor Red
}

# ---------- [2] rename_헌법사례형 ----------
Write-Host "`n--- [2] rename_헌법사례형_2026-04-29.ps1 ---" -ForegroundColor Cyan
try {
    & "H:\내 드라이브\5.기타\rename_헌법사례형_2026-04-29.ps1"
    Write-Host "[OK] rename_헌법사례형 완료 (exit=$LASTEXITCODE)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] rename_헌법사례형: $_" -ForegroundColor Red
}

# ---------- [3] Critical 3건 이동 ----------
Write-Host "`n--- [3] Critical 3건 이동 (율촌 초안.md 보류) ---" -ForegroundColor Cyan
$moves = @(
    @{ From = "H:\내 드라이브\sync\무제.md";                       To = "H:\내 드라이브\sync\로펌_자소서\" },
    @{ From = "H:\내 드라이브\sync\Gemini_위임_병행_검토.md";       To = "H:\내 드라이브\sync\_meta\" },
    @{ From = "H:\내 드라이브\sync\Colab_ocr_드라이런_검토.md";     To = "H:\내 드라이브\sync\_meta\" }
)
foreach ($m in $moves) {
    if (Test-Path -LiteralPath $m.From) {
        try {
            Move-Item -LiteralPath $m.From -Destination $m.To -Force
            Write-Host "  [MV] $($m.From) → $($m.To)" -ForegroundColor Green
        } catch {
            Write-Host "  [ERROR] $($m.From): $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  [SKIP] $($m.From) 없음" -ForegroundColor Yellow
    }
}

Write-Host "`n[검증] sync 루트 잔존 파일:" -ForegroundColor Cyan
Get-ChildItem "H:\내 드라이브\sync" -File | Select-Object Name, Length | Format-Table -AutoSize

# ---------- [4] Gemini CLI 호출 ----------
Write-Host "`n--- [4] Gemini CLI 파일럿 (방위산업 계약해제) ---" -ForegroundColor Cyan

$promptFile = "H:\내 드라이브\sync\_meta\Gemini_프롬프트_방산계약해제_2026-04-29.txt"
$gemOut     = "H:\내 드라이브\sync\Gemini_파일럿_방산계약해제_v1.md"

$prompt = @'
방위산업 계약해제 시나리오에 대한 한국 법률 1차 자료를 정리해주세요.

다음 형식을 모든 항목에 필수 적용:
- 출처: 정부 공식 사이트 URL(예: law.go.kr, scourt.go.kr, ccourt.go.kr, dapa.go.kr) 또는 KCI 논문 서지정보(저자, 논문제목, 학술지명, 권호, 페이지)
- 발췌: 원문 정확한 인용 (5문장 이내, 따옴표 포함)
- 위치: 조항 번호 또는 페이지 번호
- 카테고리: [방위사업법] / [방위사업청 고시·훈령] / [대법원 판례] / [헌법재판소 결정] / [KCI 학술논문] 중 하나

원칙:
- 블로그·카페·위키피디아·뉴스 기사 사용 금지
- 1차 자료만 인용. 학설 요약은 KCI 논문 서지로만
- 추측·해석 금지. 출처 확인 불가하면 항목 제외
- 모든 답변 한국어

쟁점 범위:
1. 방위사업법상 계약해제 사유와 절차
2. 부정당업자 제재 처분 (방위사업법 제46조 등)
3. 대법원·헌재 관련 판례 (계약해제, 부정당업자 제재, 손해배상)
4. 학설 (KCI 등재 논문 우선)
'@

$prompt | Out-File -FilePath $promptFile -Encoding utf8
Write-Host "  프롬프트 저장: $promptFile"

# gemini 실행 — Start-Process로 백그라운드, 타임아웃 적용
try {
    $geminiCmd = Get-Command gemini -ErrorAction Stop
    Write-Host "  gemini 발견: $($geminiCmd.Source)"

    # Start-Process + 타임아웃
    $stderr = "H:\내 드라이브\sync\_meta\Gemini_stderr_2026-04-29.txt"
    $proc = Start-Process -FilePath $geminiCmd.Source `
        -ArgumentList @("-p", $prompt) `
        -RedirectStandardOutput $gemOut `
        -RedirectStandardError $stderr `
        -NoNewWindow `
        -PassThru

    $timeoutSec = 180
    if ($proc.WaitForExit($timeoutSec * 1000)) {
        Write-Host "  [OK] Gemini 호출 완료 (exit=$($proc.ExitCode))" -ForegroundColor Green
        Write-Host "  결과 파일: $gemOut"
        $sz = (Get-Item -LiteralPath $gemOut -ErrorAction SilentlyContinue).Length
        Write-Host "  크기: $sz bytes"
    } else {
        Write-Host "  [TIMEOUT] $timeoutSec 초 초과 — 강제 종료" -ForegroundColor Red
        try { $proc.Kill() } catch {}
    }
} catch {
    Write-Host "  [ERROR] gemini 호출 실패: $_" -ForegroundColor Red
}

Write-Host "`n=== Master 실행 종료: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===" -ForegroundColor Cyan
Write-Host "로그: $log"

Stop-Transcript | Out-Null
