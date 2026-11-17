# Hook shim (port of hooks/run-cli-hook): resolve a CLI by name, then run it with stdin and the remaining args.
# A missing binary is NOT an error: these hooks are optional accelerators, so exit 0 and let the tool call through.
# Usage:
#   run-cli-hook.ps1 <bin> [args...]   run <bin> (exit 0 if <bin> is not installed)
#   run-cli-hook.ps1 --which <bin>     print the resolved path, exit 1 if unresolvable
$ErrorActionPreference = 'SilentlyContinue'
$which = $args.Count -gt 0 -and $args[0] -eq '--which'
$rest = @($args | Select-Object -Skip $(if ($which) { 1 } else { 0 }))
if ($rest.Count -eq 0) { exit $(if ($which) { 1 } else { 0 }) }
$name = $rest[0]; $rest = @($rest | Select-Object -Skip 1)

function Resolve-Cli($name) {
  # Explicit override wins: CCT_RTK_BIN, CCT_CONTEXT_MODE_BIN, ...
  $o = [Environment]::GetEnvironmentVariable('CCT_' + ($name.ToUpper() -replace '[.-]', '_') + '_BIN')
  if ($o -and (Test-Path -LiteralPath $o -PathType Leaf)) { return $o }

  $c = Get-Command $name -CommandType Application | Select-Object -First 1
  if ($c) { return $c.Source }

  # Dirs a hook's PATH may lack: user-level installers and package managers
  $u = $env:USERPROFILE
  $dirs = "$u\.local\bin", "$u\.cargo\bin", "$u\.bun\bin", "$u\.volta\bin", "$env:APPDATA\npm", "$u\scoop\shims",
          "$env:LOCALAPPDATA\Microsoft\WinGet\Links", "$env:LOCALAPPDATA\Programs\$name"
  # Last resort: where `pip install --user` puts scripts. Costs a process, so it runs after the cheap probes miss.
  $base = & python -c 'import site; print(site.USER_BASE)' 2>$null
  if ($base) { $dirs += "$base\Scripts" }
  foreach ($d in $dirs) {
    foreach ($ext in '.exe', '.cmd', '.bat') {
      if (Test-Path -LiteralPath "$d\$name$ext" -PathType Leaf) { return "$d\$name$ext" }
    }
  }
}

$bin = Resolve-Cli $name
if (-not $bin) { exit $(if ($which) { 1 } else { 0 }) }
if ($which) { Write-Output $bin; exit 0 }

$utf8 = New-Object Text.UTF8Encoding $false
[Console]::InputEncoding = $utf8; [Console]::OutputEncoding = $utf8; $OutputEncoding = $utf8
$stdin = [Console]::In.ReadToEnd()
$stdin | & $bin @rest
exit $LASTEXITCODE
