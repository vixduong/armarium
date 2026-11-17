# Status line for Claude Code (port of statusline-command.sh): each block is one purpose;
# " | " separates blocks, " · " separates items inside a block.
$ErrorActionPreference = 'SilentlyContinue'
$utf8 = New-Object Text.UTF8Encoding $false
[Console]::InputEncoding = $utf8; [Console]::OutputEncoding = $utf8
$inv = [Globalization.CultureInfo]::InvariantCulture
try { $d = [Console]::In.ReadToEnd() | ConvertFrom-Json } catch { exit 0 }
if (-not $d) { exit 0 }

$e = [char]27
function Paint($c, $t) { "${e}[${c}m$t${e}[0m" }
function Dim($t) { Paint 2 $t }
function Has($v) { $null -ne $v -and "$v" -ne '' }
function Zero($v) { [double]$v -eq 0 }
function PctColor($p) { $i = [math]::Truncate([double]$p); if ($i -ge 80) { 31 } elseif ($i -ge 50) { 33 } else { 32 } }
# 272000 -> 272k, 1000000 -> 1.0M
function Kfmt($v) {
  $n = [double]$v
  if ($n -ge 1e6) { $x = $n / 1e6; $s = 'M' } elseif ($n -ge 1e3) { $x = $n / 1e3; $s = 'k' } else { return [string][int]$n }
  if ($x -eq [math]::Floor($x)) { "$([int]$x)$s" } else { $x.ToString('0.0', $inv) + $s }
}
function JoinBy($sep, $items) { (@($items) | Where-Object { $_ }) -join $sep }
$DOT = Dim " $([char]0xB7) "   # not a literal: Windows PowerShell 5.1 reads a BOM-less file as ANSI
$BAR = Dim ' | '

# Items
$cwd = if ($d.workspace.current_dir) { $d.workspace.current_dir } else { $d.cwd }
$folder = $null; $branchSeg = $null
if ($cwd) {
  $folder = Paint '1;36' (($cwd -split '[\\/]' | Where-Object { $_ } | Select-Object -Last 1))
  $env:GIT_OPTIONAL_LOCKS = '0'
  $branch = git -C $cwd symbolic-ref --short HEAD 2>$null
  if (-not $branch) { $branch = git -C $cwd rev-parse --short HEAD 2>$null }
  if ($branch) {
    $dirty = if (git -C $cwd status --porcelain 2>$null | Select-Object -First 1) { '*' } else { '' }
    $branchSeg = (Dim 'git') + ' ' + (Paint '1;35' "$branch$dirty")
  }
}

$modelSeg = if ($d.model.display_name) { Paint '1;33' $d.model.display_name }
$effortSeg = if ($d.effort.level) { (Dim 'think') + ' ' + (Paint 35 $d.effort.level) }

$cw = $d.context_window
$ctxSeg = $null
if (Has $cw.used_percentage) {
  $ctxSeg = (Dim 'ctx') + ' ' + (Paint (PctColor $cw.used_percentage) (([double]$cw.used_percentage).ToString('0.0', $inv) + '%'))
  if (Has $cw.context_window_size) { $ctxSeg += ' ' + (Dim 'of') + ' ' + (Paint 36 (Kfmt $cw.context_window_size)) }
}

# A fresh session reports 0 for tokens and cost: hide them until there is something to show
$inSeg = if ((Has $cw.total_input_tokens) -and -not (Zero $cw.total_input_tokens)) { (Dim 'in') + ' ' + (Paint 36 (Kfmt $cw.total_input_tokens)) }
$outSeg = if ((Has $cw.total_output_tokens) -and -not (Zero $cw.total_output_tokens)) { (Dim 'out') + ' ' + (Paint 36 (Kfmt $cw.total_output_tokens)) }
$cacheSeg = if (Has $cw.current_usage.cache_read_input_tokens) { (Dim 'cache read') + ' ' + (Paint 36 (Kfmt $cw.current_usage.cache_read_input_tokens)) }
$writeSeg = if (Has $cw.current_usage.cache_creation_input_tokens) { (Dim 'write') + ' ' + (Paint 36 (Kfmt $cw.current_usage.cache_creation_input_tokens)) }
$pc = $d.prompt_cache
$hitSeg = if (Has $pc.hit_ratio) { (Dim 'hit') + ' ' + (Paint 32 (([double]$pc.hit_ratio * 100).ToString('0', $inv) + '%')) }
$costSeg = if ((Has $d.cost.total_cost_usd) -and -not (Zero $d.cost.total_cost_usd)) { Paint 33 ('$' + ([double]$d.cost.total_cost_usd).ToString('0.000', $inv)) }

# Idle budget: time left until the prompt cache goes cold (next turn then re-caches in full)
$idleSeg = $null
if (Has $pc.expires_at) {
  $left = [long][math]::Floor([double]$pc.expires_at) - [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  if ($left -le 0) { $idleSeg = (Dim 'idle') + ' ' + (Paint 31 'cold') }
  else {
    $t = if ($left -ge 3600) { "$([math]::Floor($left / 3600))h$([math]::Floor(($left % 3600) / 60))m" }
         elseif ($left -ge 60) { "$([math]::Floor($left / 60))m" } else { "${left}s" }
    $ic = if ($left -lt 120) { 31 } elseif ($left -lt 600) { 33 } else { 32 }
    $idleSeg = (Dim 'idle') + ' ' + (Paint $ic $t)
  }
}

$rl = $d.rate_limits
$fiveSeg = if (Has $rl.five_hour.used_percentage) { (Dim '5h') + ' ' + (Paint (PctColor $rl.five_hour.used_percentage) (([double]$rl.five_hour.used_percentage).ToString('0', $inv) + '%')) }
$weekSeg = if (Has $rl.seven_day.used_percentage) { (Dim '7d') + ' ' + (Paint (PctColor $rl.seven_day.used_percentage) (([double]$rl.seven_day.used_percentage).ToString('0', $inv) + '%')) }

# Blocks -> rows
$row1 = JoinBy $BAR @((JoinBy $DOT @($folder, $branchSeg)), (JoinBy $DOT @($modelSeg, $effortSeg)), $ctxSeg)
$row2 = JoinBy $BAR @((JoinBy $DOT @($inSeg, $outSeg, $cacheSeg, $writeSeg, $hitSeg, $idleSeg, $costSeg)), (JoinBy $DOT @($fiveSeg, $weekSeg)))
if ($row1) { Write-Output $row1 }
if ($row2) { Write-Output $row2 }
