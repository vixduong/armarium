#!/bin/sh
# Link pi's rules (AGENTS.md) and the docs they point to into pi's agent dir. A file already there is reported, never replaced.
# settings.example.json is opt-in: merge it into settings.json by hand.
# Self-test: python3 -I pi/unix/test_install.py
set -eu
repo=$(cd "$(dirname "$0")/../.." && pwd)
dest=${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}

link() { # $1 source in the repo, $2 path under $dest
  if [ -L "$dest/$2" ] && [ "$(readlink "$dest/$2")" = "$1" ]; then echo "same    $2"
  elif [ -e "$dest/$2" ] || [ -L "$dest/$2" ]; then echo "skip    $2: exists; move it aside to use the repo's"
  else mkdir -p "$(dirname "$dest/$2")"; ln -s "$1" "$dest/$2"; echo "linked  $2"
  fi
}
link "$repo/pi/common/AGENTS.md" AGENTS.md
for f in CODING_STANDARDS.md RTK.md rules/frontend.md rules/video.md; do  # shared with claude/
  link "$repo/claude/common/$f" "$f"
done
echo "Run /reload in an open pi session."
