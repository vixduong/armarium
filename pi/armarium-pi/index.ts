// Loads armarium's pi rules (AGENTS.md) as a context file, its ~/.pi/agent/ pointers resolved to the repo's shared docs.
// Self-test: python3 -I pi/test_armarium_pi.py
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const here = dirname(fileURLToPath(import.meta.url));
const path = join(here, "..", "AGENTS.md");
const shared = join(here, "..", "..", "claude", "common") + "/";

export default function (pi: ExtensionAPI) {
	// contextFiles is rebuilt for each run, so read on each run: an edit to AGENTS.md is live without /reload.
	pi.on("before_agent_start", (event) => {
		const o = event.systemPromptOptions;
		// Same reach as a global ~/.pi/agent/AGENTS.md: off under --no-context-files, and pi-subagents children
		// (tagged <active_agent .../>) get no global context by default.
		if (process.argv.includes("--no-context-files") || process.argv.includes("-nc")) return;
		if (`${o.customPrompt ?? ""}${o.appendSystemPrompt ?? ""}`.includes("<active_agent ")) return;
		// Global rules go first so a project AGENTS.md after them can override, as pi orders a global file.
		o.contextFiles.unshift({ path, content: readFileSync(path, "utf8").replaceAll("~/.pi/agent/", () => shared) });
	});
}
