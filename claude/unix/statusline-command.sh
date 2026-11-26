#!/bin/bash
# Status line for Claude Code: each block is one purpose; " | " separates blocks, " · " separates items inside a block
input=$(cat)
j() { echo "$input" | jq -r "$1 // empty"; }

cwd=$(j '.workspace.current_dir // .cwd')
model=$(j '.model.display_name')
effort=$(j '.effort.level')
ctx=$(j '.context_window.used_percentage')
ctx_size=$(j '.context_window.context_window_size')
five=$(j '.rate_limits.five_hour.used_percentage')
week=$(j '.rate_limits.seven_day.used_percentage')
in_tok=$(j '.context_window.total_input_tokens')
out_tok=$(j '.context_window.total_output_tokens')
cache_read=$(j '.context_window.current_usage.cache_read_input_tokens')
cache_write=$(j '.context_window.current_usage.cache_creation_input_tokens')
hit=$(j '.prompt_cache.hit_ratio')
cost=$(j '.cost.total_cost_usd')
cache_exp=$(j '.prompt_cache.expires_at')

C=$'\033[36m'; M=$'\033[35m'; Y=$'\033[33m'; G=$'\033[32m'
R=$'\033[31m'; B=$'\033[1m'; D=$'\033[2m'; Z=$'\033[0m'

pct_color() {
  local p=${1%.*}
  if [ "$p" -ge 80 ]; then printf '%s' "$R"
  elif [ "$p" -ge 50 ]; then printf '%s' "$Y"
  else printf '%s' "$G"; fi
}

# 272000 -> 272k, 1000000 -> 1.0M
kfmt() { awk -v n="$1" 'BEGIN { if (n >= 1000000) { x = n / 1000000; s = "M" } else if (n >= 1000) { x = n / 1000; s = "k" } else { printf "%d", n; exit }; if (x == int(x)) printf "%d%s", x, s; else printf "%.1f%s", x, s }'; }

# Join the non-empty arguments with the separator given first
joinby() {
  local sep="$1" out="" s
  shift
  for s in "$@"; do [ -n "$s" ] && out="${out:+$out$sep}$s"; done
  printf '%s' "$out"
}
DOT="${D} · ${Z}"
BAR="${D} | ${Z}"

# Items
folder=""; [ -n "$cwd" ] && folder="${B}${C}${cwd##*/}${Z}"

branch_seg=""
export GIT_OPTIONAL_LOCKS=0
if [ -n "$cwd" ]; then
  branch=$(git -C "$cwd" symbolic-ref --short HEAD 2>/dev/null || git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
  if [ -n "$branch" ]; then
    dirty=""
    [ -n "$(git -C "$cwd" status --porcelain 2>/dev/null | head -1)" ] && dirty="*"
    branch_seg="${D}git${Z} ${M}${B}${branch}${dirty}${Z}"
  fi
fi

model_seg=""; [ -n "$model" ] && model_seg="${Y}${B}${model}${Z}"
effort_seg=""; [ -n "$effort" ] && effort_seg="${D}think${Z} ${M}${effort}${Z}"

ctx_seg=""
if [ -n "$ctx" ]; then
  ctx_seg="${D}ctx${Z} $(pct_color "$ctx")$(printf '%.1f' "$ctx")%${Z}"
  [ -n "$ctx_size" ] && ctx_seg="$ctx_seg ${D}of${Z} ${C}$(kfmt "$ctx_size")${Z}"
fi

# A fresh session reports 0 for tokens and cost: hide them until there is something to show
zero() { awk -v n="${1:-0}" 'BEGIN { exit !(n + 0 == 0) }'; }
in_seg=""; [ -n "$in_tok" ] && ! zero "$in_tok" && in_seg="${D}in${Z} ${C}$(kfmt "$in_tok")${Z}"
out_seg=""; [ -n "$out_tok" ] && ! zero "$out_tok" && out_seg="${D}out${Z} ${C}$(kfmt "$out_tok")${Z}"
cache_seg=""; [ -n "$cache_read" ] && cache_seg="${D}cache read${Z} ${C}$(kfmt "$cache_read")${Z}"
write_seg=""; [ -n "$cache_write" ] && write_seg="${D}write${Z} ${C}$(kfmt "$cache_write")${Z}"
hit_seg=""; [ -n "$hit" ] && hit_seg="${D}hit${Z} ${G}$(awk -v h="$hit" 'BEGIN { printf "%.0f%%", h * 100 }')${Z}"
cost_seg=""; [ -n "$cost" ] && ! zero "$cost" && cost_seg="${Y}\$$(printf '%.3f' "$cost")${Z}"

# Idle budget: time left until the prompt cache goes cold (next turn then re-caches in full)
idle_seg=""
case "${cache_exp%.*}" in ''|*[!0-9]*) cache_exp="" ;; esac  # digits only: shell arithmetic would evaluate anything else
if [ -n "$cache_exp" ]; then
  left=$(( ${cache_exp%.*} - $(date +%s) ))
  if [ "$left" -le 0 ]; then idle_seg="${D}idle${Z} ${R}cold${Z}"
  else
    if [ "$left" -ge 3600 ]; then t="$((left / 3600))h$((left % 3600 / 60))m"
    elif [ "$left" -ge 60 ]; then t="$((left / 60))m"
    else t="${left}s"; fi
    if [ "$left" -lt 120 ]; then ic=$R; elif [ "$left" -lt 600 ]; then ic=$Y; else ic=$G; fi
    idle_seg="${D}idle${Z} ${ic}${t}${Z}"
  fi
fi

five_seg=""; [ -n "$five" ] && five_seg="${D}5h${Z} $(pct_color "$five")$(printf '%.0f' "$five")%${Z}"
week_seg=""; [ -n "$week" ] && week_seg="${D}7d${Z} $(pct_color "$week")$(printf '%.0f' "$week")%${Z}"

# Blocks
blk_project=$(joinby "$DOT" "$folder" "$branch_seg")
blk_model=$(joinby "$DOT" "$model_seg" "$effort_seg")
blk_ctx="$ctx_seg"
blk_tokens=$(joinby "$DOT" "$in_seg" "$out_seg" "$cache_seg" "$write_seg" "$hit_seg" "$idle_seg" "$cost_seg")
blk_limits=$(joinby "$DOT" "$five_seg" "$week_seg")

row1=$(joinby "$BAR" "$blk_project" "$blk_model" "$blk_ctx")
row2=$(joinby "$BAR" "$blk_tokens" "$blk_limits")

[ -n "$row1" ] && printf '%s\n' "$row1"
[ -n "$row2" ] && printf '%s\n' "$row2"
