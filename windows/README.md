# Windows

`windows/` overlays `claude/` for Windows 11 (Git for Windows, Windows PowerShell 5.1 or later). Shared files (CLAUDE.md, agents, rules, the Python hooks and their self-tests) come from `claude/`, so there is one copy to maintain. `settings.example.json` has the same keys and hook set as `claude/settings.example.json`; only the command strings and one matcher differ.

| Here | Port of (in `claude/`) |
|---|---|
| `statusline.ps1` | `statusline-command.sh` |
| `hooks/bash-ban-raw-tools.ps1` | `hooks/bash-ban-raw-tools`; the matcher is `Bash\|PowerShell`, so it also bans `Get-Content`, `Select-String`, `findstr` |
| `hooks/run-cli-hook.ps1` | `hooks/run-cli-hook` |
| `hooks/cbm-session-reminder.ps1`, `hooks/cbm-subagent-reminder.ps1` | the two `cbm-*-reminder` hooks |
| `hooks/memory-repo-symlink.ps1` | `hooks/memory-repo-symlink` (a junction, so no admin rights are needed) |
| `hooks/codemode-ponytail-band.ps1` | `hooks/codemode-ponytail-band` |

`agent-no-downgrade`, `bash-ban-shell-writes`, `flow-skill-check`, `skill-model-invocable` and `armarium-links` are Python and run as they are, called with `python`.

## Install

```powershell
pwsh windows\install.ps1          # dry run: lists new / replace per file
pwsh windows\install.ps1 -Apply   # writes; each replaced file is copied to ~\.claude\backups\armarium-<time>\
```

The installer rewrites three lines of `CLAUDE.md` that assume macOS and zsh (the `codebase-memory-mcp` path, the shell bullet, the RTK bullet) and stops if one is missing. It never touches `skills/`, `settings.json` or `settings.local.json`.

Then merge `settings.example.json` into `~\.claude\settings.json` by hand and replace `C:/Users/YOU` with your profile path (forward slashes work in Bash and PowerShell hooks alike).

## Requirements

`python` on PATH (the Python hooks), Git for Windows (the Bash tool), `rtk` (`winget install rtk-ai.rtk`), and optionally `codebase-memory-mcp`. `run-cli-hook.ps1` also looks in `~\.local\bin`, `~\.cargo\bin`, `%APPDATA%\npm`, scoop shims and the WinGet links folder. Self-tests: `python -I ~\.claude\hooks\test_agent_no_downgrade.py`, `test_bash_ban_shell_writes.py`, `test_codemode_ponytail_band.py`, `test_flow_skill_check.py`, `test_skill_model_invocable.py` and `test_armarium_links.py`. `armarium-links` stays silent after `install.ps1`, which copies rather than links. `test_armarium_links.py` creates symlinks, which Windows allows only with Developer Mode on or from an elevated shell.

## Known gaps

- `bash-ban-shell-writes` keys its 10-minute unlock file on the parent PID under `/tmp`, while `bash-ban-raw-tools.ps1` uses `%TEMP%\bash-raw-unlock-<pid>`. The two unlocks are separate on Windows.
- Each `.ps1` hook starts a PowerShell process (about 0.2 to 0.4 s per call), where the macOS hooks start bash.
