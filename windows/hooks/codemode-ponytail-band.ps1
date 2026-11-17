# SessionStart (port of hooks/codemode-ponytail-band): warn when Code Mode is on but ponytail's band mod is registered again.
# The band (a JS mod that checks tool calls) makes Code Mode fall back to ordinary tools; a ponytail update restores it.
# Fail-open: any missing file or tool -> silent exit 0.
$ErrorActionPreference = 'SilentlyContinue'
if ($env:CLAUDE_CODE_EXPERIMENTAL_CODE_MODE -ne '1') { exit 0 }
try {
  $reg = Get-Content -Raw -Encoding UTF8 (Join-Path $env:USERPROFILE '.claude\plugins\installed_plugins.json') | ConvertFrom-Json
  $dir = $reg.plugins.'ponytail@ponytail'[0].installPath
  if (-not $dir) { exit 0 }
  $plugin = Get-Content -Raw -Encoding UTF8 (Join-Path $dir '.claude-plugin\plugin.json') | ConvertFrom-Json
} catch { exit 0 }
if ((ConvertTo-Json $plugin.hooks -Depth 10 -Compress) -notmatch 'claude-band') { exit 0 }
$msg = "Code Mode is on, but ponytail $(Split-Path $dir -Leaf) registers its band mod again, so Code Mode falls back to ordinary tools. Remove `"./hooks/claude-band.json`" from $dir/.claude-plugin/plugin.json."
[Console]::Out.WriteLine((@{ systemMessage = $msg } | ConvertTo-Json -Compress))
