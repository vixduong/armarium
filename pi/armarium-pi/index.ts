// armarium-pi: loads armarium's pi rules (AGENTS.md) as a context file, its ~/.pi/agent/ pointers resolved to the repo's
// shared docs; blocks tool calls until the run's `Flow:` line is written; asks the user before destructive or credential commands;
// blocks a bash command that writes a file, as judged by the hook Claude Code runs (claude/common/hooks/bash-ban-shell-writes);
// gives a run one more turn when its final reply has no Exit list.
// Self-test: python3 -I pi/test_armarium_pi.py
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { delimiter, dirname, isAbsolute, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const here = dirname(realpathSync(fileURLToPath(import.meta.url))); // one path however the file was reached: a second copy must find the rules already added
const path = join(here, "..", "AGENTS.md");
const shared = join(here, "..", "..", "claude", "common") + "/";

const FLOW_LINE = /^[\s>*_`#-]*Flow\s*:/m;
const MAX_FLOW_BLOCKS = 2; // the 3rd message's calls go through: a model that cannot comply must not loop forever
// shortcut: a pattern check on the command text, so variables, eval, aliases, scripts and other languages get past it;
// upgrade to an allowlist or a sandbox if a model is seen evading it.
// Command position: line start, after a shell separator or keyword, or after a wrapper; then VAR=x and a path prefix.
const CMD = String.raw`(?:^\s*|[;&|({!\x60]\s*|\$\(\s*|\b(?:sudo|doas|rtk|xargs|exec|nohup|time|then|do|else|command|builtin|nice|env)\s+(?:-\S+\s+)*)(?:\w+=\S*\s+)*(?:\S*\/|\\)?`;
const GIT = String.raw`\bgit\b(?:\s+-\S+(?:\s+[^-\s]\S*)?)*?\s+`; // global options such as -C dir, --no-pager
const ARGS = String.raw`[^;&|\n]*\s`; // rest of the same command
const RISKY: RegExp[] = [
	/\bdrop\s+(?:database|schema|table)\b/i,
	/\bdropdb\b/i,
	/\btruncate\s+table\b/i,
	/\bflushall\b/i,
	new RegExp(CMD + String.raw`(?:kill|pkill|killall)\b`, "im"),
	new RegExp(CMD + String.raw`rm\b` + ARGS + String.raw`(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)\b`, "im"),
	new RegExp(GIT + String.raw`push\b` + ARGS + String.raw`(?:--force\S*|--mirror\b|-[a-zA-Z]*f[a-zA-Z]*\b|\+\S+)`, "i"),
	new RegExp(GIT + String.raw`reset\b` + ARGS + String.raw`--hard\b`, "i"),
	new RegExp(GIT + String.raw`clean\b` + ARGS + String.raw`(?:-[a-zA-Z]*f|--force\b)`),
	new RegExp(GIT + String.raw`commit\b` + ARGS + String.raw`-[a-zA-Z]*n[a-zA-Z]*\b`),
	new RegExp(GIT + String.raw`checkout\b` + ARGS + String.raw`(?:--\s+)?\.(?:\s|$)`, "m"),
	new RegExp(GIT + String.raw`restore\b` + ARGS + String.raw`\.(?:\s|$)`, "m"),
	new RegExp(GIT + String.raw`branch\b` + ARGS + String.raw`-D\b`),
	new RegExp(GIT + String.raw`stash\s+(?:drop|clear)\b`, "i"),
	new RegExp(GIT + String.raw`remote\s+set-url\b`, "i"),
	/--no-verify\b/,
	/\bcredential\.helper\b/i,
	new RegExp(GIT + String.raw`credential\s+fill\b`),
	/\bgh\s+auth\s+(?:token|setup-git)\b/,
	/\bgh\s+auth\s+status\b[^;&|\n]*\s(?:-t|--show-token)\b/,
];
// context-mode's tools run shell code outside bash, so their command fields are checked too.
const SHELL_TOOLS = new Set(["bash", "ctx_execute", "ctx_execute_file", "ctx_batch"]);

// Shell writes: the same hook file Claude Code runs judges the command, so both agents share one rule set and one self-test.
const WRITES_HOOK = join(shared, "hooks", "bash-ban-shell-writes");
// Absolute PATH entries only: on Windows a bare program name starts from the cwd, the user's project, first.
const onPath = (names: string[]): string | undefined => {
	for (const dir of (process.env.PATH ?? "").split(delimiter).map((d) => d.replace(/^"|"$/g, "")))
		for (const name of names) if (isAbsolute(dir) && existsSync(join(dir, name))) return join(dir, name);
};
// The hook's reason when it blocks (exit 2). No python, a timeout or any other exit lets the command through, as the hook itself fails open.
const shellWrite = (command: string): string | undefined => {
	const python = onPath(process.platform === "win32" ? ["python.exe", "python3.exe"] : ["python3", "python"]);
	if (!python) return;
	const input = JSON.stringify({ tool_name: "Bash", tool_input: { command } });
	const r = spawnSync(python, [WRITES_HOOK], { input, encoding: "utf8", timeout: 5000 });
	return r.status === 2 ? r.stderr.trim().replace(/^BLOCKED:\s*/, "") : undefined;
};

// A second copy of this extension in one process (another path to the package, or -e beside it) must not repeat an effect.
// The last tool call the user said yes to, shared by every copy, so the second copy does not ask again.
const APPROVED = Symbol.for("armarium-pi.approved-tool-call");
const globals = globalThis as Record<symbol, unknown>;

// pi-subagents' required-child-extension registry (src/shared/required-child-extensions.js): every child of a registered
// session loads these files whatever its agent settings say, and a load failure aborts the launch instead of running ungated.
// shortcut: written straight into the versioned global registry so this package needs no pi-subagents dependency;
// upgrade to its exported registerRequiredChildExtensions if the package ever takes that dependency.
const REGISTRY = Symbol.for("pi-subagents.required-child-extensions.v1");
// requireForAllRunners: pi-subagents refuses a machine placement or an external-CLI runner (they load no pi extension)
// and keeps the snapshot with the run, so workflow-script, resumed and recovered children stay gated.
const SELF = Object.freeze({
	id: "armarium-pi",
	path: realpathSync(fileURLToPath(import.meta.url)),
	requireForAllRunners: true as const,
});
type Entry = { id: string; path: string; requireForAllRunners?: true };
const registry = (): Map<string, readonly Entry[]> | undefined => {
	const root = globalThis as Record<symbol, unknown>;
	root[REGISTRY] ??= { version: 1, bySession: new Map() };
	const r = root[REGISTRY] as { version?: unknown; bySession?: unknown };
	return r.version === 1 && r.bySession instanceof Map ? (r.bySession as Map<string, readonly Entry[]>) : undefined;
};

const strings = (v: unknown): string[] =>
	typeof v === "string" ? [v] : v && typeof v === "object" ? Object.values(v).flatMap(strings) : [];

export default function (pi: ExtensionAPI) {
	// Per session instance (subagent children get their own), reset on each user prompt.
	let gated = false;
	let flowSeen = false;
	let attempts = 0; // assistant messages that called tools with no Flow line yet
	let needsExit = false; // a Flow line other than `answer directly` was written
	let exitAsked = false;
	let lastText = ""; // text of the latest assistant message: the final reply when the run settles
	let approvedHere: string | undefined; // the tool call this copy got a yes for

	// contextFiles is rebuilt for each run, so read on each run: an edit to AGENTS.md is live without /reload.
	pi.on("before_agent_start", (event, ctx) => {
		register(ctx);
		const o = event.systemPromptOptions;
		if (event.messageType === "user") {
			flowSeen = needsExit = exitAsked = false;
			attempts = 0;
		}
		// Same reach as a global ~/.pi/agent/AGENTS.md: off under --no-context-files, and pi-subagents children
		// (tagged <active_agent .../>) get no global context by default.
		gated = false;
		if (process.argv.includes("--no-context-files") || process.argv.includes("-nc")) return;
		if (`${o.customPrompt ?? ""}${o.appendSystemPrompt ?? ""}`.includes("<active_agent ")) return;
		gated = true;
		// Global rules go first so a project AGENTS.md after them can override, as pi orders a global file.
		if (o.contextFiles.some((f) => f.path === path)) return; // another copy added the rules
		o.contextFiles.unshift({ path, content: readFileSync(path, "utf8").replaceAll("~/.pi/agent/", () => shared) });
	});

	// Registered at session start, since pi-subagents can launch children before any prompt (/run, scheduled runs,
	// workflow auto-resume); runs and subagent calls refresh it. A host that registered first is kept beside ours.
	// shortcut: a host calling pi-subagents' registerRequiredChildExtensions after us throws (the key is taken), and a host
	// that disposes while merged gets its entry back on our restore; switch to that API if this package takes the dependency.
	let registeredAs: string | undefined;
	let previous: readonly Entry[] | undefined; // the other host's exact array, restored so its dispose() still matches
	const unregister = () => {
		const map = registry();
		if (map && registeredAs !== undefined && map.get(registeredAs)?.includes(SELF)) {
			if (previous) map.set(registeredAs, previous);
			else map.delete(registeredAs);
		}
		registeredAs = previous = undefined;
	};
	const register = (ctx: { sessionManager: { getSessionId(): string } }) => {
		// pi-subagents looks a parent up by its session id (parentSessionId); a session-file key is never read.
		const key = ctx.sessionManager.getSessionId();
		if (key === registeredAs) return;
		unregister();
		const map = registry();
		if (!map) return;
		previous = map.get(key);
		map.set(key, Object.freeze([...(previous ?? []).filter((e) => e.id !== SELF.id), SELF]));
		registeredAs = key;
	};
	pi.on("session_start", (_event, ctx) => {
		unregister();
		register(ctx);
	});
	pi.on("session_shutdown", unregister);

	pi.on("message_end", (event) => {
		const m = event.message as { role?: string; content?: unknown };
		if (m.role !== "assistant" || !Array.isArray(m.content)) return;
		const parts = m.content as { type?: string; text?: string }[];
		lastText = parts.map((c) => (c.type === "text" ? c.text : "")).join("\n");
		const flows = lastText.split("\n").filter((l) => FLOW_LINE.test(l));
		if (flows.length) flowSeen = true;
		else if (!flowSeen && parts.some((c) => c.type === "toolCall")) attempts++;
		if (flows.some((l) => !/answer directly|answered in chat/i.test(l))) needsExit = true; // the chat row, by its flow or its Route name
	});

	// AGENTS.md Exit: every final reply except a chat answer lists the row's Done-when items, each ✓ or ✗.
	// One reminder per user prompt, so a model that cannot comply still settles (Claude Code: flow-skill-check, stop_hook_active).
	pi.on("agent_before_settle", (event) => {
		if (!gated || !needsExit || exitAsked || event.outcome !== "completed") return;
		if (lastText.split("\n").some((l) => /[✓✗]/.test(l) && !FLOW_LINE.test(l))) return;
		exitAsked = true;
		if (event.entries.some((e) => (e as { customType?: string }).customType === "armarium-exit")) return; // another copy asked
		const content =
			"armarium-pi: this run has a `Flow:` line, but the final reply has no Exit list. Reply again and list the row's " +
			"Done-when items, each ✓ with its evidence or ✗ with the reason (AGENTS.md Exit).";
		return { entries: [...event.entries, { type: "custom_message", customType: "armarium-exit", content, display: true }], continue: true };
	});

	pi.on("tool_call", async (event, ctx) => {
		if (event.toolName === "subagent") register(ctx); // the session key can change after the run started
		if (gated && !flowSeen && attempts <= MAX_FLOW_BLOCKS) {
			return {
				block: true,
				reason:
					"armarium-pi: write a plain line starting `Flow:` (pi/AGENTS.md Route) in your reply text, not in thinking, " +
					"then call tools. A chat answer that calls tools writes `Flow: answer directly`.",
			};
		}
		if (!SHELL_TOOLS.has(event.toolName)) return;
		const input = event.input as { command?: unknown; commands?: unknown; code?: unknown };
		// bash only: ctx_execute code may be Python or JS, where > is a comparison.
		const write = event.toolName === "bash" && typeof input.command === "string" ? shellWrite(input.command) : undefined;
		if (write) return { block: true, reason: `armarium-pi: ${write} In pi those tools are \`write\` and \`edit\`.` };
		const command = strings([input.command, input.commands, input.code]).join("\n");
		const hit = RISKY.map((p) => command.match(p)).find(Boolean);
		if (!hit) return;
		const start = Math.max(command.lastIndexOf("\n", hit.index ?? 0) + 1, (hit.index ?? 0) - 40);
		const end = command.indexOf("\n", (hit.index ?? 0) + hit[0].length);
		const line = command.slice(start, end < 0 ? undefined : end).trim();
		const reason =
			"armarium-pi: this command is destructive or touches credentials, so it needs the user's yes. " +
			"Stop and ask the user in your reply. A subagent has no user here, and a supervisor's yes does not open this check: " +
			"report the command as blocked in your final answer.";
		if (!ctx.hasUI) return { block: true, reason };
		// Another copy asked about this call and got a yes: use that yes once. A later call with the same id is asked again.
		if (globals[APPROVED] === event.toolCallId && approvedHere !== event.toolCallId) {
			delete globals[APPROVED];
			return;
		}
		// The match goes first so padding cannot push the risky part out of the dialog.
		const shown = command.length > 800 ? `${command.slice(0, 800)}\n… (${command.length} chars)` : command;
		const yes = await ctx.ui.confirm("armarium-pi: allow this command?", `Matched: ${line.slice(0, 300)}\n\n${shown}`, {
			timeout: 60_000,
			signal: ctx.signal,
		});
		// confirm returns false for a no, a timeout and an abort alike.
		approvedHere = yes ? event.toolCallId : undefined;
		if (yes) globals[APPROVED] = event.toolCallId;
		else delete globals[APPROVED];
		return yes ? undefined : { block: true, reason: "armarium-pi: no yes from the user for this command. Ask in your reply how to proceed." };
	});
}
