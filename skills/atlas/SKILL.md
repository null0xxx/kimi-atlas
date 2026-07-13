---
name: atlas
description: Use when the user runs /skill:atlas or asks kimi-atlas to turn a rough coding request into elite, verified, human-gated implemented code. (P0 skeleton — orchestrator not yet implemented.)
argument-hint: "<rough coding request> | ping"
---

# atlas — orchestrator (P0 skeleton)

kimi-atlas is being built in phases (see `PLAN.md` at the plugin root). This is the **P0 skeleton**: it proves the plugin loads and the skill is discoverable. The full state-machine orchestrator lands in P2.

## Behavior

- If the argument is exactly `ping` (or empty), respond with a single line:
  `kimi-atlas P0 skeleton loaded OK — orchestrator not yet implemented (see PLAN.md §6/P2).`
  Then stop.
- For any other argument, respond:
  `kimi-atlas is not yet implemented (P0 skeleton). The orchestrator (INIT -> INTENT_CAPTURED -> ... -> OUTPUT) is scheduled for P2. See PLAN.md.`
  Then stop.

Do not dispatch subagents, write files, or take any action in P0 — this skeleton only confirms load and discovery.
