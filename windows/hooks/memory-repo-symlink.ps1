# SessionStart hook (Windows port of hooks/memory-repo-symlink):
# point ~/.claude/projects/<slug>/memory at <repo>/.claude/memory so memory lives in the repo.
$ErrorActionPreference = 'SilentlyContinue'

$cwd = $env:CLAUDE_PROJECT_DIR
if (-not $cwd) { $cwd = (Get-Location).Path }

$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) { exit 0 }
$repoRoot = (& git -C $cwd rev-parse --show-toplevel 2>$null)
if (-not $repoRoot) { exit 0 }
$repoRoot = $repoRoot.Replace('/', '\').TrimEnd('\')
# In a linked worktree, use the main checkout so memory outlives the worktree.
$common = (& git -C $cwd rev-parse --path-format=absolute --git-common-dir 2>$null)
if ($common) {
  $common = $common.Replace('/', '\').TrimEnd('\')
  if ((Split-Path $common -Leaf) -eq '.git') { $repoRoot = Split-Path $common -Parent }
}

# shortcut: slug rule inferred from observed project dir names; if it mismatches we
# simply do nothing (no junk dirs), so memory stays in the projects dir as before.
$slug = $repoRoot -replace '[:\\/ ]', '-' -replace '\.', '-'
$projectsMemory = Join-Path $env:USERPROFILE ".claude\projects\$slug\memory"

$claudeHome = (Join-Path $env:USERPROFILE '.claude')
if ($repoRoot -eq $claudeHome) {
  $repoMemory = Join-Path $repoRoot 'memory'
} else {
  $repoMemory = Join-Path $repoRoot '.claude\memory'
}

# Only act on project dirs Claude Code already created -> no orphan dirs.
if (-not (Test-Path -LiteralPath (Split-Path $projectsMemory -Parent))) { exit 0 }

New-Item -ItemType Directory -Path $repoMemory -Force | Out-Null

$item = Get-Item -LiteralPath $projectsMemory -Force -ErrorAction SilentlyContinue
if ($item -and $item.LinkType -and $item.Target -contains $repoMemory) { exit 0 }

# Existing real dir with contents -> move them into the repo first.
# Never overwrite a repo file; if anything stays behind, keep the real dir and retry next session.
if ($item -and -not $item.LinkType) {
  Get-ChildItem -LiteralPath $projectsMemory -Force |
    Where-Object { -not (Test-Path -LiteralPath (Join-Path $repoMemory $_.Name)) } |
    Move-Item -Destination $repoMemory
  if (Get-ChildItem -LiteralPath $projectsMemory -Force) { exit 0 }
  Remove-Item -LiteralPath $projectsMemory -Force
}

# A junction that points elsewhere: drop the link only (never its target), then recreate it.
# New-Item -Force over an existing junction removes it without recreating it.
if ($item -and $item.LinkType) { $item.Delete() }
# Junction, not symlink: works without admin/Developer Mode.
New-Item -ItemType Junction -Path $projectsMemory -Target $repoMemory -Force | Out-Null
exit 0
