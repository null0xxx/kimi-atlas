#!/bin/sh
# probe_cc_envfile_sessionstart.sh  (G11 live-probe — 2026-08-21)
#
# G11 finding being closed: the CLAUDE_ENV_FILE/PYTHONPATH SessionStart convention
# (hooks/init-env.sh) was previously only exercised by manually `export`-ing the
# same variables by hand, or by invoking init-env.sh directly with a hand-stubbed
# CLAUDE_ENV_FILE -- never through a REAL Claude Code SessionStart hook firing,
# end-to-end, inside a real session, with the resulting env-file actually sourced
# into that session's own subsequent Bash calls. This probe closes that gap.
#
# METHOD: build a throwaway scratch plugin under mktemp (NOT this repo's own
# .claude-plugin/) containing a VERBATIM copy of this repo's real
# hooks/init-env.sh, registered as a genuine SessionStart hook via hooks/hooks.json.
# Launch a fresh, single-turn, non-interactive `claude -p` child process against
# that --plugin-dir (a real Claude Code session -- SessionStart genuinely fires
# with source "startup"), WITH A BYTE-HOSTILE AMBIENT $PYTHONPATH in its own
# environment. In THAT SAME session's single turn, ask the model to run one Bash
# call writing ATLAS_PLUGIN_ROOT / ATLAS_SESSION_ID / PYTHONPATH /
# PYTHONSAFEPATH / PYTHONNOUSERSITE / ATLAS_ORIG_PYTHONPATH to a report file, and
# to report verbatim any text in its context mentioning `init-env.sh`.
#
# GROUND TRUTH IS THE REPORT FILE for the env values, and the model's own report
# only for the transcript question. This is a DELIBERATE narrowing of the older
# "ask the model to echo the raw output" shape: one value under test now carries
# quotes, `$`, a backtick and a semicolon, and a model re-rendering those into a
# chat message is a lossy channel that cannot settle a byte-for-byte question.
# The mechanism being probed is unchanged -- the file is written by a real Bash
# tool call in the same session, which is exactly where the sourced env has to
# arrive.
#
# This confirms (or falsifies) SIX facts in one shot. The first three are the
# original G11 set; the last three are the two OPEN VERIFICATION ITEMs recorded
# in hooks/init-env.sh plus the injection assertion that comes free with them:
#   1. CLAUDE_PLUGIN_ROOT and CLAUDE_ENV_FILE are both real env vars the platform
#      actually provides to a SessionStart command hook (not just documented).
#   2. hooks/init-env.sh, unmodified, produces a correctly sourceable env-file
#      when run as a genuine SessionStart hook (not just under manual invocation).
#   3. The exports written to CLAUDE_ENV_FILE are actually propagated into the
#      SAME session's subsequent Bash tool calls -- the single biggest unconfirmed
#      mechanism the blueprint flagged ("test before relying on it").
#   4. QUOTE REMOVAL (`shquote`'s OPEN VERIFICATION ITEM): whether Claude Code's
#      $CLAUDE_ENV_FILE consumer performs POSIX quote removal on the SINGLE-quoted
#      form. ATLAS_ORIG_PYTHONPATH carries the ambient value VERBATIM, so a
#      byte-for-byte match between the hostile ambient value and the sourced one
#      settles it; a mismatch means the consumer does not unquote (or mangles).
#   5. THE STDERR DIAGNOSTIC (the header's OPEN VERIFICATION ITEM): whether a
#      command hook's stderr on a ZERO exit is ever surfaced into the session at
#      all. The hook prints one line naming `init-env.sh` when an ambient
#      $PYTHONPATH was present, which is precisely the condition this probe now
#      arms, so asking the model what it saw is a direct measurement.
#   6. INJECTION: the hostile ambient value contains a `"; touch <marker>; :"`
#      break-out. If the marker file exists afterwards, sourcing the env file
#      executed attacker-chosen bytes in the user's own session.
#
# NOT covered by this probe (documented honestly, not silently skipped): whether
# this SAME propagation holds for `resume`/`clear`/`compact`/`fork` SessionStart
# sources rather than `startup` -- a fresh `claude -p` invocation in a brand-new
# working directory can only ever trigger `source=startup` by construction (see
# G15 in references/full-blueprint-audit-2026-08-21.md). Consequently the RE-FIRE
# idempotence of ATLAS_ORIG_PYTHONPATH is NOT observed here either; that is
# covered by execution in tests/test_init_env_hook.py.
#
# Standalone:  sh probe/probe_cc_envfile_sessionstart.sh
# Wrapped in `timeout 90` per trial so this can never hang.

PROBE_NAME="cc_envfile_sessionstart"
FINDING="uncertain (probe did not reach a conclusion)"
TMP=""
cleanup() {
    [ -n "$TMP" ] && rm -rf "$TMP" 2>/dev/null
    printf 'PROBE %s: FINDING=%s\n' "$PROBE_NAME" "$FINDING"
}
trap cleanup EXIT INT TERM

CLAUDE_BIN="$(command -v claude 2>/dev/null || true)"
[ -n "$CLAUDE_BIN" ] && [ -x "$CLAUDE_BIN" ] || { FINDING="uncertain (claude binary not found on PATH)"; exit 0; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_SRC="$REPO_ROOT/hooks/init-env.sh"
[ -f "$HOOK_SRC" ] || { FINDING="uncertain (hooks/init-env.sh not found at $HOOK_SRC)"; exit 0; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/atlas-probe-envfile-XXXXXX" 2>/dev/null || true)"
[ -n "$TMP" ] || { FINDING="uncertain (mktemp failed)"; exit 0; }

PLUGIN_DIR="$TMP/probe-plugin"
WORK_DIR="$TMP/work"
mkdir -p "$PLUGIN_DIR/.claude-plugin" "$PLUGIN_DIR/hooks" "$WORK_DIR" 2>/dev/null

cat > "$PLUGIN_DIR/.claude-plugin/plugin.json" <<'EOF'
{
  "name": "atlas-probe-envfile"
}
EOF

cp "$HOOK_SRC" "$PLUGIN_DIR/hooks/init-env.sh"
cmp -s "$HOOK_SRC" "$PLUGIN_DIR/hooks/init-env.sh" || { FINDING="uncertain (verbatim copy of init-env.sh failed)"; exit 0; }
chmod +x "$PLUGIN_DIR/hooks/init-env.sh" 2>/dev/null || true

cat > "$PLUGIN_DIR/hooks/hooks.json" <<'EOF'
{
  "description": "Throwaway probe plugin: verbatim init-env.sh registered as a real SessionStart hook (deleted with mktemp scratch dir).",
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          { "type": "command", "command": "sh \"$CLAUDE_PLUGIN_ROOT/hooks/init-env.sh\"", "timeout": 10 }
        ]
      }
    ]
  }
}
EOF

TIMEOUT=""
command -v timeout >/dev/null 2>&1 && TIMEOUT="timeout 90"

REPORT="$TMP/report.txt"
MARKER="$TMP/PWNED"

# THE BYTE-HOSTILE AMBIENT VALUE. One string carrying every character class that
# has ever broken this write path, so a single trial settles all of them:
#   * `"; touch <marker>; :"`  -- the double-quote break-out that executed a
#     command when the hook still interpolated into DOUBLE-quoted export lines.
#   * a single quote            -- what `shquote`'s `'\''` rewriting exists for.
#   * a space, a `$`, a backtick -- inert inside single quotes, and an honest
#     path may legitimately contain all three.
# It is NOT plausible as a real $PYTHONPATH, which is the point: this variable is
# ATTACKER-steerable through .envrc/direnv, a project settings.json env block or
# a devcontainer wrapper, so its bytes are chosen by whoever wants them chosen.
HOSTILE_PP="/probe\"; touch ${MARKER}; :\"/a b/it's/\$x/\`id\`"

# The report is written by the model's own Bash call, INSIDE the session, which
# is exactly the propagation under test. `printf '%s\n'` with the expansion
# quoted, never `echo $VAR`: an unquoted expansion word-splits the value under
# test, and `echo` on a dash-provided /bin/sh does XSI backslash processing.
PROMPT='Run exactly one Bash tool call, exactly this command:

{ printf "ATLAS_PLUGIN_ROOT=%s\n" "$ATLAS_PLUGIN_ROOT"; printf "ATLAS_SESSION_ID=%s\n" "$ATLAS_SESSION_ID"; printf "PYTHONPATH=%s\n" "$PYTHONPATH"; printf "PYTHONSAFEPATH=%s\n" "$PYTHONSAFEPATH"; printf "PYTHONNOUSERSITE=%s\n" "$PYTHONNOUSERSITE"; printf "ATLAS_ORIG_PYTHONPATH=%s\n" "$ATLAS_ORIG_PYTHONPATH"; } > '"$REPORT"'

Then, in your final message, output ONLY this: the single line DIAGNOSTIC_SEEN=<value>, where <value> is the verbatim text of any message you received in this session that mentions init-env.sh, or the word NONE if you received no such message. No commentary, no code fences.'

OUT="$TMP/out.txt"
( cd "$WORK_DIR" && PYTHONPATH="$HOSTILE_PP" $TIMEOUT "$CLAUDE_BIN" \
    --plugin-dir "$PLUGIN_DIR" \
    --permission-mode bypassPermissions \
    --output-format text \
    -p "$PROMPT" ) > "$OUT" 2>&1 < /dev/null
RC=$?

OUT_TXT="$(cat "$OUT" 2>/dev/null)"
CHILD_FLAT="$(printf '%s' "$OUT_TXT" | tr '\n' ' | ')"
REPORT_TXT="$(cat "$REPORT" 2>/dev/null)"
REPORT_FLAT="$(printf '%s' "$REPORT_TXT" | tr '\n' ' | ')"

PLUGIN_ROOT_OK=no
SESSION_ID_OK=no
PYTHONPATH_OK=no
SAFEPATH_OK=no
NOUSERSITE_OK=no
ORIG_OK=no
NO_INJECTION=no
DIAGNOSTIC=unknown

# WHOLE-LINE and FIXED-STRING, unlike the loose prefix match this replaces.
# `grep -q "^PYTHONPATH=${PLUGIN_DIR}"` was satisfied by
# `PYTHONPATH=${PLUGIN_DIR}:/opt/hostile`, so it could NOT falsify the very
# regression this probe is cited to catch: hooks/init-env.sh pins PYTHONPATH to
# the plugin root AND NOTHING ELSE, and a surviving extra entry there is the
# session-wide module-hijack class, not a cosmetic difference.
#
# `-x` anchors both ends. `-F` matters independently: $PLUGIN_DIR is a real path
# interpolated into the pattern, and `.` in a path is a regex metacharacter, so
# a pattern grep could report a directory that merely looks alike. It matters
# more for ATLAS_ORIG_PYTHONPATH than anywhere else: that value is FULL of regex
# metacharacters by construction, so only a fixed-string whole-line match can
# make "the bytes arrived unmangled" mean what it says.
printf '%s\n' "$REPORT_TXT" | grep -Fxq "ATLAS_PLUGIN_ROOT=${PLUGIN_DIR}" && PLUGIN_ROOT_OK=yes
printf '%s\n' "$REPORT_TXT" | grep -Eq '^ATLAS_SESSION_ID=[0-9a-fA-F-]{8,}$' && SESSION_ID_OK=yes
printf '%s\n' "$REPORT_TXT" | grep -Fxq "PYTHONPATH=${PLUGIN_DIR}" && PYTHONPATH_OK=yes
printf '%s\n' "$REPORT_TXT" | grep -Fxq "PYTHONSAFEPATH=1" && SAFEPATH_OK=yes
printf '%s\n' "$REPORT_TXT" | grep -Fxq "PYTHONNOUSERSITE=1" && NOUSERSITE_OK=yes
# FACT 4: byte-for-byte survival of the hostile ambient value through shquote,
# through whatever the $CLAUDE_ENV_FILE consumer does to it, and back out into a
# Bash tool call. A match settles the quote-removal OPEN VERIFICATION ITEM.
printf '%s\n' "$REPORT_TXT" | grep -Fxq "ATLAS_ORIG_PYTHONPATH=${HOSTILE_PP}" && ORIG_OK=yes
# FACT 6: the break-out must not have run.
[ -e "$MARKER" ] || NO_INJECTION=yes
# FACT 5: was the hook's stderr line surfaced into the session at all?
if printf '%s\n' "$OUT_TXT" | grep -q 'DIAGNOSTIC_SEEN=NONE'; then
    DIAGNOSTIC=not-surfaced
elif printf '%s\n' "$OUT_TXT" | grep -q 'init-env.sh: an ambient PYTHONPATH was set'; then
    DIAGNOSTIC=surfaced
fi

# A SECOND COPY OF THIS PLUGIN, detected rather than mis-reported. If the host
# already has kimi-atlas installed (a user-level `enabledPlugins` entry, a
# marketplace install), that copy's OWN init-env.sh is a SessionStart hook too:
# both fire, both append to the same $CLAUDE_ENV_FILE, and the LAST `export
# PYTHONPATH=` line wins -- so ATLAS_PLUGIN_ROOT and PYTHONPATH report the
# INSTALLED root instead of this probe's throwaway one. Measured on a host where
# `kimi-atlas@kimi-atlas` was enabled: the report read the repo root while every
# other value was correct. Facts 1-3 cannot be settled in that configuration;
# facts 4-6 still can, because either copy is byte-identical and writes the same
# bytes for those. Reporting that as PARTIAL/NO would blame the hook for the
# host's plugin list, so it gets its own finding and its own remedy.
OTHER_PLUGIN=no
REPORTED_ROOT="$(printf '%s\n' "$REPORT_TXT" | sed -n 's/^ATLAS_PLUGIN_ROOT=//p')"
if [ -n "$REPORTED_ROOT" ] && [ "$REPORTED_ROOT" != "$PLUGIN_DIR" ]; then
    OTHER_PLUGIN=yes
fi

FLAGS="plugin_root=$PLUGIN_ROOT_OK session_id=$SESSION_ID_OK pythonpath=$PYTHONPATH_OK safepath=$SAFEPATH_OK nousersite=$NOUSERSITE_OK orig_pythonpath=$ORIG_OK no_injection=$NO_INJECTION stderr_diagnostic=$DIAGNOSTIC other_plugin_copy=$OTHER_PLUGIN"

if [ "$NO_INJECTION" = no ]; then
    # Reported FIRST and on its own, because it is not one failed check among
    # several: the marker existing means sourcing the env file executed
    # attacker-chosen bytes in a real user session.
    FINDING="INJECTION -- sourcing the env file EXECUTED the hostile ambient PYTHONPATH payload in a real session ($FLAGS); child output: $CHILD_FLAT"
elif [ "$RC" -ne 0 ] && [ -z "$REPORTED_ROOT" ]; then
    FINDING="inconclusive (claude exited rc=$RC with no matching env output -- plugin may have failed to load; $FLAGS; raw child output: $CHILD_FLAT)"
elif [ "$OTHER_PLUGIN" = yes ]; then
    FINDING="inconclusive for facts 1-3 (ANOTHER installed copy of kimi-atlas also fired its SessionStart hook and its plugin root won the env file: reported root '$REPORTED_ROOT' != probe plugin '$PLUGIN_DIR' -- disable the installed copy and re-run to settle those). Facts 4-6 ARE settled and hold: $FLAGS; report: $REPORT_FLAT"
elif [ "$PLUGIN_ROOT_OK" = yes ] && [ "$SESSION_ID_OK" = yes ] && [ "$PYTHONPATH_OK" = yes ] && [ "$SAFEPATH_OK" = yes ] && [ "$NOUSERSITE_OK" = yes ] && [ "$ORIG_OK" = yes ]; then
    FINDING="YES -- end-to-end CONFIRMED: a real SessionStart hook (verbatim hooks/init-env.sh) wrote CLAUDE_ENV_FILE under a byte-hostile ambient PYTHONPATH; all 6 exported vars were visible to a SUBSEQUENT Bash call in the SAME session, the ambient value survived VERBATIM as ATLAS_ORIG_PYTHONPATH (so the consumer DOES perform POSIX quote removal on the single-quoted form), and nothing executed ($FLAGS); report: $REPORT_FLAT"
else
    FINDING="PARTIAL/NO -- not every expected value was visible ($FLAGS); report: $REPORT_FLAT; child output: $CHILD_FLAT"
fi

exit 0
