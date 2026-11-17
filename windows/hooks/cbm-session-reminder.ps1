# SessionStart context adapter (port of hooks/cbm-session-reminder).
# Fail-open: it never blocks or logs hook/prompt content.
# `hook-augment` costs ~300 ms per session start, so the output is cached per cwd;
# the cache stays valid until an index file (*.db) changes.
$ErrorActionPreference = 'SilentlyContinue'
$bin = & "$PSScriptRoot\run-cli-hook.ps1" --which codebase-memory-mcp
if (-not $bin) { exit 0 }

$utf8 = New-Object Text.UTF8Encoding $false
[Console]::InputEncoding = $utf8; [Console]::OutputEncoding = $utf8; $OutputEncoding = $utf8
$in = [Console]::In.ReadToEnd()
$d = Join-Path $env:USERPROFILE '.cache\codebase-memory-mcp'
$cwd = try { ($in | ConvertFrom-Json).cwd } catch { $null }

$f = $null
if ($cwd) {
  $sha = [Security.Cryptography.SHA1]::Create()
  $h = -join ($sha.ComputeHash($utf8.GetBytes($cwd)) | ForEach-Object { $_.ToString('x2') })
  $f = Join-Path $d "hook-cache\$($h.Substring(0, 16)).json"
}
$newest = Get-ChildItem $d -Filter *.db | Where-Object Name -ne 'activity.db' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($f -and (Test-Path -LiteralPath $f) -and (Get-Item -LiteralPath $f).Length -gt 0) {
  $t = (Get-Item -LiteralPath $f).LastWriteTime
  if ($t -gt (Get-Item $d).LastWriteTime -and (-not $newest -or $t -gt $newest.LastWriteTime)) {
    [Console]::Out.Write([IO.File]::ReadAllText($f)); exit 0
  }
}
$out = (($in | & $bin hook-augment 2>$null) -join "`n")
[Console]::Out.Write($out)
if ($f -and $out) {
  New-Item -ItemType Directory -Force (Split-Path $f) | Out-Null
  [IO.File]::WriteAllText($f, $out, $utf8)
}
exit 0
