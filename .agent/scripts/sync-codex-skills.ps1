param(
    [string]$SourceRoot = "H:\내 드라이브\.agent\skills",
    [string]$DestRoot = "$env:USERPROFILE\.codex\skills",
    [switch]$WhatIfOnly
)

$ErrorActionPreference = 'Stop'

function Normalize-SkillMdEncoding {
    param([string]$Root)

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)

    Get-ChildItem -Recurse -File -Path $Root -Filter SKILL.md |
        Where-Object { $_.FullName -notmatch '\\.system\\' } |
        ForEach-Object {
            $path = $_.FullName
            $text = [System.IO.File]::ReadAllText($path)

            # Remove leading BOM character if present so frontmatter starts with '---'
            if ($text.Length -gt 0 -and [int][char]$text[0] -eq 65279) {
                $text = $text.Substring(1)
            }

            [System.IO.File]::WriteAllText($path, $text, $utf8NoBom)
        }
}

if (-not (Test-Path $SourceRoot)) {
    throw "SourceRoot not found: $SourceRoot"
}

if (-not (Test-Path $DestRoot)) {
    New-Item -ItemType Directory -Path $DestRoot -Force | Out-Null
}

$skillDirs = Get-ChildItem -Path $SourceRoot -Directory
$copied = @()

foreach ($dir in $skillDirs) {
    $dest = Join-Path $DestRoot $dir.Name
    if (-not (Test-Path $dest)) {
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
    }

    if ($WhatIfOnly) {
        Write-Output "PLAN  | $($dir.FullName) -> $dest"
    }
    else {
        Copy-Item -Path (Join-Path $dir.FullName '*') -Destination $dest -Recurse -Force
        Write-Output "SYNCED | $($dir.Name) -> $dest"
        $copied += $dir.Name
    }
}

if (-not $WhatIfOnly) {
    Normalize-SkillMdEncoding -Root $DestRoot
    Write-Output "DONE  | copied=$($copied.Count)"
}
