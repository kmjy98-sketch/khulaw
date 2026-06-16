<#
.SYNOPSIS
    log_file_op.ps1 — 파일 이동·이름변경·복사·trash 이동 자동 로그 (Windows/PowerShell)

.DESCRIPTION
    CLAUDE.md #16-C 의무 로그 시스템의 PowerShell 헬퍼.
    sha256·size 계산 → master.csv / master.jsonl / master.md 3개 형식에 동시 append.
    -Execute 지정 시 실제 이동/복사 수행 + 전후 sha256 무결성 검증.
    공유드라이브(0.공유드라이브/) 경로는 #16-B 따라 쓰기·이동 차단.

.PARAMETER Op
    move | rename | copy | delete-to-trash

.PARAMETER Src
    원본 경로

.PARAMETER Dst
    대상 경로 또는 신규 이름

.PARAMETER Reason
    이동 사유 1줄

.PARAMETER TaskId
    작업 세션 ID 또는 메모

.PARAMETER Execute
    실제 이동/복사 수행 (미지정 시 로그만)

.EXAMPLE
    # 이동 실행 + 자동 로그
    .\log_file_op.ps1 -Op move -Src "원본.md" -Dst "대상.md" -Reason "중복 정리" -Execute

.EXAMPLE
    # 이미 끝난 이동을 기록만
    .\log_file_op.ps1 -Op rename -Src "구이름.md" -Dst "새이름.md" -Reason "명명규칙 정정"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidateSet("move", "rename", "copy", "delete-to-trash")]
    [string]$Op,
    [Parameter(Mandatory = $true)][string]$Src,
    [Parameter(Mandatory = $true)][string]$Dst,
    [string]$Reason = "",
    [string]$TaskId = "",
    [switch]$Execute
)

$ErrorActionPreference = "Stop"

$WsRoot   = "H:\내 드라이브"
$LogDir   = Join-Path $WsRoot ".agent\file_ops_log"
$CsvPath  = Join-Path $LogDir "master.csv"
$JsonlPath = Join-Path $LogDir "master.jsonl"
$MdPath   = Join-Path $LogDir "master.md"

$SharedMarkers = @("0.공유드라이브", "공유 드라이브", "shared drive")

function Test-Shared([string]$p) {
    $s = $p.Replace("\", "/").ToLower()
    foreach ($m in $SharedMarkers) { if ($s.Contains($m.ToLower())) { return $true } }
    return $false
}

function Get-Sha256([string]$p) {
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower()
}

# #16-B 공유드라이브 가드
if ($Execute -and ((Test-Shared $Dst) -or (Test-Shared $Src))) {
    Write-Error "[차단] 공유드라이브(0.공유드라이브/) 경로는 이동·쓰기 금지 (#16-B)."
    exit 2
}

$sha = $null
$size = $null
$verified = $null   # $null = 미검증

if ($Execute) {
    if (-not (Test-Path -LiteralPath $Src)) { Write-Error "[오류] 원본 없음: $Src"; exit 1 }
    if (Test-Path -LiteralPath $Dst) { Write-Error "[오류] 대상 이미 존재: $Dst"; exit 1 }

    $isFile = (Get-Item -LiteralPath $Src).PSIsContainer -eq $false
    if ($isFile) { $pre = Get-Sha256 $Src; $size = (Get-Item -LiteralPath $Src).Length }

    $dstParent = Split-Path -Parent $Dst
    if ($dstParent -and -not (Test-Path -LiteralPath $dstParent)) {
        New-Item -ItemType Directory -Force -Path $dstParent | Out-Null
    }

    if ($Op -eq "copy") { Copy-Item -LiteralPath $Src -Destination $Dst -Recurse }
    else { Move-Item -LiteralPath $Src -Destination $Dst }

    if ($isFile) {
        $post = Get-Sha256 $Dst
        $sha = $post
        $verified = ($pre -eq $post)
        if (-not $verified) { Write-Warning "[경고] sha256 불일치! pre=$($pre.Substring(0,12)) post=$($post.Substring(0,12))" }
    }
}
else {
    $target = if (Test-Path -LiteralPath $Dst) { $Dst } elseif (Test-Path -LiteralPath $Src) { $Src } else { $null }
    if ($target -and -not (Get-Item -LiteralPath $target).PSIsContainer) {
        $sha = Get-Sha256 $target
        $size = (Get-Item -LiteralPath $target).Length
        if ((Test-Path -LiteralPath $Dst) -and (Test-Path -LiteralPath $Src)) {
            $verified = ((Get-Sha256 $Src) -eq (Get-Sha256 $Dst))
        }
        elseif (Test-Path -LiteralPath $Dst) { $verified = $true }
    }
}

$timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss")

$rec = [ordered]@{
    timestamp   = $timestamp
    operation   = $Op
    source_path = $Src
    dest_path   = $Dst
    size_bytes  = $size
    sha256      = $sha
    task_id     = $TaskId
    reason      = $Reason
    verified    = $verified
}

if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }

# --- CSV ---
$csvNew = -not (Test-Path -LiteralPath $CsvPath)
if ($csvNew) {
    "timestamp,operation,source_path,dest_path,size_bytes,sha256,task_id,reason,verified" |
        Out-File -LiteralPath $CsvPath -Encoding utf8
}
function Esc([object]$v) {
    if ($null -eq $v) { return "" }
    $s = [string]$v
    if ($s -match '[",\r\n]') { return '"' + $s.Replace('"', '""') + '"' }
    return $s
}
$verCsv = if ($null -eq $verified) { "" } else { $verified.ToString().ToLower() }
$line = @(
    (Esc $timestamp), (Esc $Op), (Esc $Src), (Esc $Dst),
    (Esc $size), (Esc $sha), (Esc $TaskId), (Esc $Reason), (Esc $verCsv)
) -join ","
Add-Content -LiteralPath $CsvPath -Value $line -Encoding utf8

# --- JSONL ---
$json = ($rec | ConvertTo-Json -Compress -Depth 3)
Add-Content -LiteralPath $JsonlPath -Value $json -Encoding utf8

# --- MD ---
$mdNew = -not (Test-Path -LiteralPath $MdPath)
if ($mdNew) {
    $header = @"
# 파일 이동·이름변경 마스터 로그 (사람 가독본)

> 자동 생성 — log_file_op.ps1 / log_file_op.py 가 append.
> 기계 처리용 원본은 master.jsonl, 표 계산은 master.csv 참조.
> CLAUDE.md #16-C 의무 로그. 직접 손으로 수정하지 말 것.

| timestamp | operation | source | dest | size | sha256 | task_id | reason | verified |
|---|---|---|---|---|---|---|---|---|
"@
    Out-File -LiteralPath $MdPath -Encoding utf8 -InputObject $header
}
$vMd = if ($verified -eq $true) { "OK" } elseif ($verified -eq $false) { "FAIL" } else { "—" }
$sizeMd = if ($null -eq $size) { "—" } else { $size }
$shaMd = if ($sha) { $sha.Substring(0, [Math]::Min(12, $sha.Length)) + "…" } else { "—" }
$taskMd = if ($TaskId) { $TaskId } else { "—" }
$reasonMd = if ($Reason) { $Reason } else { "—" }
$mdLine = "| $timestamp | $Op | ``$Src`` | ``$Dst`` | $sizeMd | ``$shaMd`` | $taskMd | $reasonMd | $vMd |"
Add-Content -LiteralPath $MdPath -Value $mdLine -Encoding utf8

$vMsg = if ($verified -eq $true) { "검증OK" } elseif ($verified -eq $false) { "검증FAIL" } else { "미검증" }
Write-Output "[로그완료] $Op | $vMsg | $(Split-Path -Leaf $Src) -> $Dst | $LogDir\master.(csv|jsonl|md)"
