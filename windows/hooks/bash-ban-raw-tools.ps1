# PreToolUse Bash/PowerShell gate (port of hooks/bash-ban-raw-tools): block a command whose first word is
# cat/head/tail/find/grep/rg/wc, or Get-Content/gc/type/Select-String/sls/findstr. RTK wrappers pass.
# Escape hatch: create $env:TEMP\bash-raw-unlock-<parent pid> (valid 10 min).
# Fail-open: any parse/IO error lets the call through.
$ErrorActionPreference = 'SilentlyContinue'
$raw = [Console]::In.ReadToEnd()
try { $p = $raw | ConvertFrom-Json } catch { exit 0 }
if ($p.tool_name -notin 'Bash', 'PowerShell') { exit 0 }

# Unlock is per session and absent from the block messages: it is for the user.
# Expires after 10 min; a future mtime (clock skew, forged) counts as expired.
$ppid = (Get-CimInstance Win32_Process -Filter "ProcessId=$PID").ParentProcessId
$unlock = Join-Path $env:TEMP "bash-raw-unlock-$ppid"
if (Test-Path -LiteralPath $unlock) {
  $age = ((Get-Date) - (Get-Item -LiteralPath $unlock).LastWriteTime).TotalSeconds
  if ($age -ge 0 -and $age -lt 600) { exit 0 }
  Remove-Item -LiteralPath $unlock -Force
}

$cmd = [string]$p.tool_input.command
$trimmed = $cmd.TrimStart()
$first = ($trimmed -split '\s+')[0]
if ($first -eq 'rtk') { exit 0 }   # rtk wraps git/cargo/pytest/docker/etc.

# `type` reads a file only in PowerShell; in Bash it is a shell builtin (`type -a git`).
$type = if ($p.tool_name -eq 'PowerShell') { '|type' } else { '' }
$readers = "cat|head|tail|find|grep|rg|wc|Get-Content|gc|Select-String|sls|findstr$type"

# A truncation pipe after a file reader still floods context before the trim.
if ($cmd -match '\|\s*(tail|head)\b' -and $first -match "^(cat|grep|rg|find|Get-Content|gc|Select-String|sls|findstr$type)$") {
  [Console]::Error.WriteLine(@'
BLOCKED: '| tail'/'| head' pipeline. Output truncation not allowed - raw output still floods context before trim.

REPLACE WITH mcp__plugin_context-mode_context-mode__ctx_execute:
  language: "shell", code: "<the same pipeline>"

Sandbox keeps the full output out of context; print only the answer.
For ONE short command (<20 lines) drop the pipe - just run it raw.
'@)
  exit 2
}

if ($first -notmatch "^($readers)$") { exit 0 }

# The rtk PreToolUse hook rewrites these into compact `rtk ...` forms, so blocking here only costs a turn: defer when rtk resolves.
& "$PSScriptRoot\run-cli-hook.ps1" --which rtk | Out-Null
if ($LASTEXITCODE -eq 0) { exit 0 }

$msg = switch -Regex ($first) {
  '^(cat|head|tail|Get-Content|gc|type)$' { "BLOCKED '$first'. Use the Read tool (absolute path + offset/limit), or ctx_execute(language:'shell') for big files." }
  '^find$'                                 { "BLOCKED 'find'. Use the Glob tool (pattern='**/...') if listed, else ctx_execute(language:'shell')." }
  '^(grep|rg|Select-String|sls|findstr)$'  { "BLOCKED '$first'. Use the Grep tool (pattern, glob, output_mode) if listed, else ctx_execute(language:'shell')." }
  '^wc$'                                   { "BLOCKED 'wc'. If you need line count, Read the file (line count is visible) or pipe via 'rtk wc'." }
}
[Console]::Error.WriteLine($msg)
exit 2
