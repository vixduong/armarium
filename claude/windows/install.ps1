# Overlay claude/common/ then claude/windows/ onto ~/.claude (claude/unix/ is macOS and Linux only). Dry run unless -Apply; every file it replaces is backed up first.
# Never touches settings.json or settings.local.json: merge settings.example.json by hand. skills/ gets only the repo's own skills; other skills on the machine stay.
param([switch]$Apply)
$ErrorActionPreference = 'Stop'
$claude = Split-Path $PSScriptRoot
$dest = Join-Path $env:USERPROFILE '.claude'
$bak  = Join-Path $dest ("backups\armarium-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))

# CLAUDE.md lines that assume macOS/zsh; each must match once, or the repo text has drifted
$patch = @(
  @('~/.local/bin/codebase-memory-mcp cli', 'codebase-memory-mcp cli'),
  @('- **Shell is zsh**: `$cmd` holding "pnpm ci" does not word-split (exit 127); call each command directly or use the repo script.',
    '- **Two shells**: the Bash tool is Git Bash (use `C:/...` paths); the PowerShell tool is pwsh 7 (use `;` or `&&`, not `&`). Write each command in the syntax of the tool you call.'),
  @('- **RTK**: Bash runs as', '- **RTK**: Bash and PowerShell run as')
)

$files = foreach ($root in 'common', 'windows') {
  $base = Join-Path $claude $root
  Get-ChildItem $base -Recurse -File | Where-Object {
    $rel = $_.FullName.Substring($base.Length + 1)
    -not (($rel -split '\\') -contains '__pycache__') -and
    -not ($root -eq 'windows' -and ($rel -in 'install.ps1', 'README.md', 'settings.example.json'))
  } | ForEach-Object { [pscustomobject]@{ Src = $_.FullName; Rel = $_.FullName.Substring($base.Length + 1) } }
}
# windows/ wins over common/ for the same relative path
$files = $files | Group-Object Rel | ForEach-Object { $_.Group[-1] }

function Get-Wanted($f) {
  if ($f.Rel -ne 'CLAUDE.md') { return , [IO.File]::ReadAllBytes($f.Src) }
  $t = [IO.File]::ReadAllText($f.Src)
  foreach ($p in $patch) {
    if (-not $t.Contains($p[0])) { throw "CLAUDE.md patch target not found: $($p[0])" }
    $t = $t.Replace($p[0], $p[1])
  }
  , (New-Object Text.UTF8Encoding $false).GetBytes($t)
}

foreach ($f in $files) {
  $to = Join-Path $dest $f.Rel
  $want = Get-Wanted $f
  # CR is ignored: a CRLF checkout and an LF checkout of the same file count as the same
  $state = if (-not (Test-Path $to)) { 'new' }
           elseif ([Linq.Enumerable]::SequenceEqual([byte[]]([IO.File]::ReadAllBytes($to) -ne 13), [byte[]]($want -ne 13))) { 'same' }
           else { 'replace' }
  if ($state -eq 'same') { continue }
  "{0,-8} {1}" -f $state, $f.Rel
  if (-not $Apply) { continue }
  if ($state -eq 'replace') {
    $b = Join-Path $bak $f.Rel; New-Item -ItemType Directory -Force (Split-Path $b) | Out-Null; Copy-Item $to $b
  }
  New-Item -ItemType Directory -Force (Split-Path $to) | Out-Null
  [IO.File]::WriteAllBytes($to, $want)
}
if ($Apply) { "Done. Backups of replaced files: $bak" } else { 'Dry run. Re-run with -Apply to write.' }
