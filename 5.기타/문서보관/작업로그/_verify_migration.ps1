# Migration verify: compare current E:\법학볼트 against saved manifest.
# Run:  powershell -ExecutionPolicy Bypass -File "sync\_meta\_verify_migration.ps1"
# ASCII-only code (PS5.1 encoding-safe). Reads ASCII-named manifest copy.
$here = $PSScriptRoot
$root = (Get-Item $here).Parent.Parent.FullName       # E:\법학볼트
$man  = Join-Path $here '_migration_manifest_2026-06-23.csv'
if(-not (Test-Path -LiteralPath $man)){ Write-Host "manifest not found: $man"; exit 1 }
$M=@{}; Import-Csv -LiteralPath $man | ForEach-Object { $M[$_.rel]=[long]$_.size }
$C=@{}
Get-ChildItem -LiteralPath $root -Recurse -File -Force -EA SilentlyContinue |
  Where-Object { $_.FullName -notlike "$root\.git\*" } |
  ForEach-Object { $C[$_.FullName.Substring($root.Length+1)] = $_.Length }
$missing = @($M.Keys | Where-Object { -not $C.ContainsKey($_) })
$changed = @($M.Keys | Where-Object { $C.ContainsKey($_) -and $C[$_] -ne $M[$_] })
$extra   = @($C.Keys | Where-Object { -not $M.ContainsKey($_) })
Write-Host ("manifest files = {0}" -f $M.Count)
Write-Host ("current  files = {0}" -f $C.Count)
Write-Host ("MISSING = {0}" -f $missing.Count); $missing | Select-Object -First 40 | ForEach-Object { Write-Host "  - $_" }
Write-Host ("CHANGED = {0}" -f $changed.Count); $changed | Select-Object -First 40 | ForEach-Object { Write-Host "  ~ $_" }
Write-Host ("EXTRA   = {0}" -f $extra.Count);   $extra   | Select-Object -First 40 | ForEach-Object { Write-Host "  + $_" }
if($missing.Count -eq 0 -and $changed.Count -eq 0){ Write-Host "`n[OK] no missing/changed vs manifest" }
else { Write-Host "`n[CHECK] differences found (see above)" }
