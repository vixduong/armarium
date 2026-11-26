# Windows

`claude/windows/` overlays `claude/common/` for Windows 11 (Git for Windows, Windows PowerShell 5.1 or later). Shared files (CLAUDE.md, agents, rules, the Python hooks and their self-tests) come from `claude/common/`, so there is one copy to maintain. `settings.example.json` has the same keys and hook set as `claude/unix/settings.example.json`; only the command strings and one matcher differ.

| Here | Port of (in `claude/unix/`) |
|---|---|
| `statusline.py` | `statusline-command.sh` |
| `hooks/bash-ban-raw-tools.py` | `hooks/bash-ban-raw-tools`; the matcher is `Bash\|PowerShell`, so it also bans `Get-Content`, `Select-String`, `findstr` |
| `hooks/run_cli_hook.py` | `hooks/run-cli-hook`, for the per-call `rtk hook claude` |
| `hooks/cbm_session_reminder.py` | `hooks/cbm-session-reminder`; a stale cache is replayed at once and refreshed in the background |
| `hooks/memory_repo_symlink.py` | `hooks/memory-repo-symlink` (a junction, so no admin rights are needed) |
| `hooks/codemode_ponytail_band.py` | `hooks/codemode-ponytail-band`; its self-test is `claude/common/hooks/test_codemode_ponytail_band.py`, which runs this port on Windows |

`agent-no-downgrade`, `bash-ban-shell-writes`, `flow-skill-check`, `reviewer-gate`, `skill-model-invocable` and `armarium-links` are Python and run as they are, called with `python`. The ones that start `git` find it with `path_only.py`, which reads only the absolute PATH entries, because Windows would otherwise run a `git.exe` from the project folder.

## Install

```powershell
pwsh claude\windows\install.ps1          # dry run: lists new / replace per file
pwsh claude\windows\install.ps1 -Apply   # writes; each replaced file is copied to ~\.claude\backups\armarium-<time>\
```

The installer rewrites three lines of `CLAUDE.md` that assume macOS and zsh (the `codebase-memory-mcp` path, the shell bullet, the RTK bullet) and stops if one is missing. It copies the repo's own `skills/` (other skills on the machine stay), never touches `settings.json` or `settings.local.json`, and it never deletes: no setting calls the PowerShell hooks an older install left in `~\.claude\hooks` (`bash-ban-raw-tools.ps1`, `cbm-session-reminder.ps1`, `codemode-ponytail-band.ps1`, `memory-repo-symlink.ps1`, `run-cli-hook.ps1`), so delete them by hand.

Then merge `settings.example.json` into `~\.claude\settings.json` by hand and replace `C:/Users/YOU` with your profile path (forward slashes work in Bash and PowerShell hooks alike).

## Requirements

`python` on PATH (the Python hooks), Git for Windows (the Bash tool), `rtk` (`winget install rtk-ai.rtk`), and optionally `codebase-memory-mcp`. `run_cli_hook.py` also looks in `~\.local\bin`, `~\.cargo\bin`, `%APPDATA%\npm`, scoop shims and the WinGet links folder. Self-tests: `python -I ~\.claude\hooks\test_agent_no_downgrade.py`, `test_bash_ban_shell_writes.py`, `test_codemode_ponytail_band.py`, `test_flow_skill_check.py`, `test_reviewer_gate.py`, `test_skill_model_invocable.py`, `test_armarium_links.py`, `test_bash_ban_raw_tools.py`, `test_cbm_session_reminder.py`, `test_memory_repo_symlink.py` and `test_statusline.py`. `armarium-links` stays silent after `install.ps1`, which copies rather than links. `test_armarium_links.py` creates symlinks, which Windows allows only with Developer Mode on or from an elevated shell.

## Known gaps

- `bash-ban-shell-writes` and `bash-ban-raw-tools.py` share the 10-minute unlock file `%TEMP%\bash-raw-unlock-<pid>`. Both take the PID from `os.getppid()`, which is the `python` launcher's when `python` is a launcher (uv, py).
- Every hook is Python: a PowerShell start cost 0.3 to 0.9 s (measured) where the macOS hooks start bash, and the session-start hooks ran in parallel with the slowest setting the wait. `cbm_session_reminder.py`: `hook-augment` takes about 2 s, so a stale cache is replayed at once and refreshed in the background, and the graph context can lag one index behind.
