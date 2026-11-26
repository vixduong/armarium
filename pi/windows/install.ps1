# Copy pi's rules (AGENTS.md) and the docs they point to into pi's agent dir. Dry run unless -Apply; a replaced file is backed up first.
# settings.example.json is opt-in: merge it into settings.json by hand. Re-run after an edit in the repo.
param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot)
$dest = if ($env:PI_CODING_AGENT_DIR) { $env:PI_CODING_AGENT_DIR } else { Join-Path $env:USERPROFILE '.pi\agent' }
$bak  = Join-Path $dest ("backups\armarium-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))

$files = @(, @((Join-Path $repo 'pi\common\AGENTS.md'), 'AGENTS.md')) +
         @('CODING_STANDARDS.md', 'RTK.md', 'rules\frontend.md', 'rules\video.md' | ForEach-Object { , @((Join-Path $repo "claude\common\$_"), $_) })
foreach ($f in $files) {
  $src, $name = $f
  $to = Join-Path $dest $name
  $state = if (-not (Test-Path $to)) { 'new' }
           elseif ((Get-FileHash $to).Hash -eq (Get-FileHash $src).Hash) { 'same' }
           else { 'replace' }
  "{0,-8} {1}" -f $state, $name
  if (-not $Apply -or $state -eq 'same') { continue }
  if ($state -eq 'replace') {
    $b = Join-Path $bak $name; New-Item -ItemType Directory -Force (Split-Path $b) | Out-Null; Copy-Item $to $b
  }
  New-Item -ItemType Directory -Force (Split-Path $to) | Out-Null
  Copy-Item $src $to
}
if ($Apply) { 'Done. Run /reload in an open pi session.' } else { 'Dry run. Re-run with -Apply to write.' }
