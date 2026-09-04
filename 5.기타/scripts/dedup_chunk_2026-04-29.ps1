# 중복 chunk 정본 선정 + 백업 이동 스크립트
# 작성: 2026-04-29
# 기준: C(메타) + D(size) + A(ch 번호)
# 원칙: CLAUDE.md #16 — 삭제 금지, _trash 또는 _백업 폴더로 이동만

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("송영곤", "윤동환")]
    [string]$Target,

    [switch]$DryRun = $false  # 기본은 실제 실행. -DryRun 주면 탐지만.
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 경로 설정
$BaseRoot = "H:\내 드라이브\sync\_교재원문\민법"
$Today = "2026-04-29"

if ($Target -eq "송영곤") {
    $TargetDir = Join-Path $BaseRoot "송영곤_논점민법_보충"
    $BackupDir = Join-Path $TargetDir "_백업\중복정리\$Today"
} else {
    $TargetDir = Join-Path $BaseRoot "윤동환_민법의맥"
    $BackupDir = Join-Path $TargetDir "_백업\중복정리\$Today"
}

$MetaDir = "H:\내 드라이브\sync\_meta"
$ManifestPath = Join-Path $MetaDir "중복정리_manifest_${Target}_${Today}.json"
$ReportPath = Join-Path $MetaDir "중복정리_보고_${Target}_${Today}.md"

Write-Host "=== 중복 chunk 정본 선정 batch ==="
Write-Host "대상: $Target"
Write-Host "폴더: $TargetDir"
Write-Host "DryRun: $DryRun"
Write-Host ""

if (-not (Test-Path $TargetDir)) {
    Write-Error "대상 폴더 없음: $TargetDir"
    exit 1
}

# 백업 폴더 생성 (실제 실행 시)
if (-not $DryRun) {
    if (-not (Test-Path $BackupDir)) {
        New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
        Write-Host "백업 폴더 생성: $BackupDir"
    }
}

# 1. .md 파일 수집 (백업 폴더 제외, _교재목차.md 제외)
$AllFiles = Get-ChildItem -Path $TargetDir -Filter "*.md" -File | Where-Object {
    $_.FullName -notmatch '\\_백업\\' -and $_.Name -ne '_교재목차.md'
}

Write-Host "스캔 대상 파일 수: $($AllFiles.Count)"

# 2. 각 파일별 hash + 메타 추출
function Get-FileMeta {
    param([System.IO.FileInfo]$File)

    $content = Get-Content -Path $File.FullName -Raw -Encoding UTF8

    # front matter 추출 (--- 사이)
    $frontMatter = ""
    $body = $content
    if ($content -match '^(---[\s\S]*?\n---\n)([\s\S]*)$') {
        $frontMatter = $Matches[1]
        $body = $Matches[2]
    }

    # 본문 hash (front matter 제외)
    $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hashBytes = $sha.ComputeHash($bodyBytes)
    $hash = ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""

    # 서브책자 필드 추출
    $subBook = ""
    if ($frontMatter -match '서브책자:\s*([^\r\n챕터]+)') {
        $subBook = $Matches[1].Trim()
    }

    # ch 번호 추출 (파일명에서)
    $chNum = 99999
    if ($File.Name -match '_ch(\d+)') {
        $chNum = [int]$Matches[1]
    } elseif ($File.Name -match 'ch(\d+)_') {
        $chNum = [int]$Matches[1]
    }

    return [PSCustomObject]@{
        Path = $File.FullName
        Name = $File.Name
        Size = $File.Length
        Hash = $hash
        SubBook = $subBook
        ChNum = $chNum
        BodyLength = $body.Length
    }
}

Write-Host "메타 추출 중..."
$Metas = @()
$progress = 0
foreach ($f in $AllFiles) {
    $progress++
    if ($progress % 20 -eq 0) {
        Write-Host "  $progress / $($AllFiles.Count)"
    }
    try {
        $meta = Get-FileMeta -File $f
        $Metas += $meta
    } catch {
        Write-Warning "메타 추출 실패: $($f.Name) — $_"
    }
}
Write-Host "메타 추출 완료: $($Metas.Count)개"

# 3. hash로 그룹화 → 중복 그룹만 추출
$Groups = $Metas | Group-Object -Property Hash | Where-Object { $_.Count -gt 1 }
Write-Host "중복 그룹 수: $($Groups.Count)"
Write-Host ""

# 4. 정본 선정 함수
function Select-Primary {
    param($Members)

    # (c) 서브책자 메타 우선순위
    function MetaRank($subBook) {
        if ($subBook -match '본책|기본민법강의|메인') { return 1 }
        if ($subBook -match '보충|선택형|DT|사례|필기노트|DailyTest') { return 2 }
        if ($subBook -match '부록|색인') { return 3 }
        return 99
    }

    $sorted = $Members | Sort-Object @(
        @{Expression = { MetaRank($_.SubBook) }; Ascending = $true},
        @{Expression = { $_.Size }; Ascending = $false},  # 큰 것 먼저
        @{Expression = { $_.ChNum }; Ascending = $true}
    )
    return $sorted[0]
}

# 5. 그룹별 정본 선정 + 이동 계획
$ManifestGroups = @()
$ProcessedCount = 0
$MovedCount = 0

foreach ($g in $Groups) {
    $members = $g.Group
    $primary = Select-Primary -Members $members
    $secondaries = $members | Where-Object { $_.Path -ne $primary.Path }

    $moveList = @()
    foreach ($s in $secondaries) {
        $backupPath = Join-Path $BackupDir $s.Name
        if (Test-Path $backupPath) {
            $backupPath = Join-Path $BackupDir "ch$($s.ChNum)_$($s.Name)"
        }

        $moveList += [PSCustomObject]@{
            원본 = $s.Path
            백업 = $backupPath
            메타 = $s.SubBook
            size = $s.Size
            ch = $s.ChNum
        }

        if (-not $DryRun) {
            Move-Item -Path $s.Path -Destination $backupPath -Force
            $MovedCount++
        }
    }

    $ManifestGroups += [PSCustomObject]@{
        hash = $g.Name
        멤버수 = $members.Count
        정본 = [PSCustomObject]@{
            path = $primary.Path
            메타 = $primary.SubBook
            size = $primary.Size
            ch = $primary.ChNum
        }
        이동 = $moveList
    }
    $ProcessedCount++

    if ($ProcessedCount % 5 -eq 0) {
        Write-Host "  처리: $ProcessedCount / $($Groups.Count) 그룹"
    }
}

Write-Host ""
Write-Host "=== 결과 ==="
Write-Host "중복 그룹: $($Groups.Count)"
Write-Host "이동된 파일: $MovedCount"
Write-Host "정본으로 남은 파일: $($Groups.Count)"
$totalToMove = ($ManifestGroups | ForEach-Object { $_.이동.Count } | Measure-Object -Sum).Sum
Write-Host "총 비정본 (이동 대상): $totalToMove"

# 6. manifest JSON 저장
if (-not (Test-Path $MetaDir)) {
    New-Item -Path $MetaDir -ItemType Directory -Force | Out-Null
}

$Manifest = [PSCustomObject]@{
    그룹수 = $Groups.Count
    처리일 = $Today
    기준 = "C(메타: 본책>보충>부록) + D(size 큰 것) + A(ch 번호 작은 것)"
    DryRun = $DryRun.IsPresent
    대상폴더 = $TargetDir
    백업폴더 = $BackupDir
    스캔파일수 = $AllFiles.Count
    이동된파일수 = $MovedCount
    그룹 = $ManifestGroups
}

$Manifest | ConvertTo-Json -Depth 10 | Out-File -FilePath $ManifestPath -Encoding UTF8
Write-Host "manifest 저장: $ManifestPath"

# 7. 보고 .md 저장
$report = @"
# 중복 chunk 정본 선정 보고 — $Target ($Today)

## 개요
- 대상 폴더: ``$TargetDir``
- 스캔 파일 수: $($AllFiles.Count)
- 중복 그룹: $($Groups.Count)
- 이동된 비정본 파일: $MovedCount
- DryRun: $($DryRun.IsPresent)

## 기준
1. (c) 메타 "서브책자" 우선순위: 본책 > 보충 > 부록 > 기타
2. (d) 동률 시 size 큰 것
3. (a) 추가 동률 시 ch 번호 작은 것 (tiebreaker)

## 백업 위치
``$BackupDir``

## 그룹별 정본/이동 내역

"@

foreach ($g in $ManifestGroups) {
    $primaryName = ($g.정본.path -split '\\')[-1]
    $report += "### 그룹 (hash $($g.hash.Substring(0,12))...)`n"
    $report += "- 멤버 수: $($g.멤버수)`n"
    $report += "- **정본**: ``$primaryName`` (ch$($g.정본.ch), $($g.정본.size) bytes)`n"
    $report += "  - 서브책자: $($g.정본.메타)`n"
    $report += "- 이동:`n"
    foreach ($m in $g.이동) {
        $name = ($m.원본 -split '\\')[-1]
        $report += "  - ``$name`` (ch$($m.ch), $($m.size) bytes) — 서브책자: $($m.메타)`n"
    }
    $report += "`n"
}

$report += "`n## 검증`n"
$report += "- 정본은 원래 위치 유지`n"
$report += "- 비정본은 모두 ``$BackupDir`` 에 보존됨 (CLAUDE.md #16 준수)`n"
$report += "- manifest: ``$ManifestPath```n"

$report | Out-File -FilePath $ReportPath -Encoding UTF8
Write-Host "보고서 저장: $ReportPath"

Write-Host ""
Write-Host "=== 완료 ==="
