# SubagentStart context adapter (port of hooks/cbm-subagent-reminder).
# Fail-open: it never blocks or logs hook/prompt content.
# PowerShell does not hand its own stdin to a child process, so pass it on explicitly.
$bin = & "$PSScriptRoot\run-cli-hook.ps1" --which codebase-memory-mcp
if (-not $bin) { exit 0 }
$utf8 = New-Object Text.UTF8Encoding $false
[Console]::InputEncoding = $utf8; [Console]::OutputEncoding = $utf8; $OutputEncoding = $utf8
[Console]::In.ReadToEnd() | & $bin hook-augment 2>$null
exit 0
