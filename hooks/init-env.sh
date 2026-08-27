#!/bin/sh
# init-env.sh — kimi-atlas SessionStart hook: persist portable plugin-root env.
#
# Runs on EVERY SessionStart, not once. `hooks/hooks.json` registers this file
# under matcher `"*"`, so it fires for `startup` AND for `resume`/`clear`/
# `compact`/`fork` — and compaction is routine in a long atlas run. Every line
# below therefore has to be correct on the SECOND fire, whose ambient
# environment is the env file the FIRST fire already wrote; see the idempotence
# note on ATLAS_ORIG_PYTHONPATH, which is the one value that state can destroy.
#
# Reads the plugin root from $CLAUDE_PLUGIN_ROOT (always available to hook
# commands) and persists it for the REST OF THE SESSION by appending `export`
# lines to the file named in $CLAUDE_ENV_FILE:
#   * PYTHONSAFEPATH=1   — stops CPython from ranking the interpreter's own
#     working directory above the stdlib on `sys.path`.
#   * PYTHONNOUSERSITE=1 — stops CPython's `site` from adding the USER SITE
#     directory and, on the same ENABLE_USER_SITE flag, from importing
#     `usercustomize` AT STARTUP.
#
#     THE THIRD DOOR, and the two switches above do not reach it. That import
#     needs no `import` statement in the program being run — being findable IS
#     the exploit. MEASURED on CPython 3.12.3 against the SHIPPED tree: a
#     `usercustomize.py` planted through an ambient $PYTHONUSERBASE EXECUTED
#     inside `python3 -c "from scripts import verdict"` — the process that loads
#     the FROZEN gate — with PYTHONSAFEPATH=1 set and PYTHONPATH pinned to the
#     plugin root; rc=0, and the gate loaded normally afterwards, so the
#     compromise was silent. With this switch exported the same fixture does not
#     execute and the gate still loads.
#
#     THE INIT FLOOR GUARD CANNOT SEE IT, which is why it is closed here rather
#     than reported there: `usercustomize` runs at `site` time, BEFORE the
#     guard's own body, so `sys.flags.safe_path` was MEASURED True in the same
#     interpreter in which the hijack had already run.
#
#     THE COST, measured rather than assumed, because unlike the scrub applied
#     to this hook's OWN python3 further down, this one is EXPORTED and so
#     reaches every third-party tool the session launches: a tool installed into
#     its own venv (the `uv tool install` shape
#     `references/stage5-negative-gate-live-validation.md` records as this
#     project's convention for semgrep) is UNAFFECTED — measured rc=0, because
#     its dependencies live in the venv rather than the user site. A tool
#     installed with `pip install --user` DOES break — measured rc=1,
#     ModuleNotFoundError — because its dependencies live in exactly the
#     directory this switch suppresses. The two seams that launch somebody
#     else's code therefore strip it again, each for its own recorded reason:
#     `scripts/proccap.py::target_env` for the TARGET's build, and
#     `scripts/sast.py` for the semgrep child.
#   * ATLAS_PLUGIN_ROOT — the plugin root, for scripts/hooks that need a stable
#     portable reference instead of a hardcoded path.
#   * PYTHONPATH         — set to the plugin root AND NOTHING ELSE, so
#     `python3 -m scripts.<mod>` / `from scripts import <mod>` resolve against
#     the plugin rather than against any DIRECTORY the target repo can put on
#     the search path. Narrower than it used to read, and deliberately: with
#     PYTHONSAFEPATH and PYTHONNOUSERSITE alongside it this closes the cwd, the
#     PYTHONPATH and the user-site doors, but it does NOT close $PYTHONHOME,
#     which relocates the stdlib itself and is scrubbed only for this hook's own
#     python3 (see THE FOURTH DOOR below). "Nothing the environment can steer"
#     would be a false sentence; these three doors is the true one.
#
#     THE AMBIENT $PYTHONPATH IS NOT PROPAGATED ONTO THIS VARIABLE. It is not
#     inspected, not filtered and not appended here; it is replaced outright.
#     That is DELIBERATE ISOLATION for every python3 that resolves the PLUGIN's
#     own modules. The ambient value is not DISCARDED, though — it is preserved
#     under ATLAS_ORIG_PYTHONPATH below, and handed back to the TARGET's own
#     build, which is the only consumer that legitimately needs it.
#
#     WHY IT IS REPLACED RATHER THAN EXTENDED. The ambient environment is
#     ATTACKER-STEERABLE: a checked-out repo reaches it through .envrc/direnv,
#     a project `.claude/settings.json` env block, or a devcontainer wrapper.
#     What this hook writes is SOURCED by the host shell, so any entry that
#     survived into it would govern module resolution for EVERY python3 the
#     session launches, wherever that process runs. `PYTHONSAFEPATH=1` is NOT
#     the countermeasure — MEASURED on CPython 3.12.3, it removes only
#     `sys.path[0]` and does not filter PYTHONPATH entries at all: a
#     `sitecustomize.py` reached through PYTHONPATH still EXECUTED with the
#     switch on. That is the v1.5.1 module-hijack class (CHANGELOG.md
#     `[1.5.1]`, line 356) re-armed session-wide through one variable.
#
#     FILTERING WAS TRIED AND MEASURED INSUFFICIENT, which is why this is a
#     replacement rather than a sanitiser. Keeping only ABSOLUTE ambient entries
#     closed the empty/relative hole — those resolve against each process's own
#     working directory — but persisted an absolute hostile directory verbatim,
#     and a later python3 in that session executed a `sitecustomize.py` out of
#     it with PYTHONSAFEPATH=1 on. A half-closed hole is not a defence.
#
#   * ATLAS_ORIG_PYTHONPATH — the ambient $PYTHONPATH, VERBATIM, parked under a
#     name no interpreter consults. ALWAYS written, even when the ambient value
#     was unset or empty (in which case it is written as the empty string).
#
#     IDEMPOTENT ACROSS RE-FIRES, and this is a live regression, not a
#     hypothetical. Because the matcher is `"*"` (see the top of this file), the
#     SECOND fire's ambient environment is what the FIRST fire wrote — so
#     `${PYTHONPATH-}` reads the PLUGIN ROOT, and a line that recorded it would
#     overwrite the user's real original with it. MEASURED against the
#     unguarded line: fire 1 recorded '/opt/mono/src', fire 2 recorded
#     '/plugin', after which `target_env` hands '/plugin' to every target build
#     — the exact FALSE RED this variable exists to prevent, now permanent for
#     the rest of the session and immune to the seam that was supposed to fix
#     it. `${ATLAS_ORIG_PYTHONPATH-${PYTHONPATH-}}` makes an ALREADY-RECORDED
#     original win, including an already-recorded EMPTY one (`-`, not `:-`,
#     precisely so "the hook ran and the user had no PYTHONPATH" survives a
#     re-fire as itself rather than being upgraded to the plugin root). The
#     write stays UNCONDITIONAL, so absence keeps its one meaning.
#
#     THE SEAM, because one variable was serving two consumers with OPPOSITE
#     needs. The PLUGIN's own python3 needs the plugin root ALONE — that is the
#     isolation above, and it does not change. The TARGET's build needs the
#     TARGET's real $PYTHONPATH, because `scripts/proccap.py::target_env()`
#     hands the SESSION environment to the child that runs the target's own
#     verify command (`runcheck.py`, `suiterun.py`). With PYTHONPATH pinned
#     session-wide, that child inherited PYTHONPATH=<plugin root>: a monorepo
#     wired through .envrc lost its own $PYTHONPATH and went RED on lens 5 for a
#     reason that had nothing to do with its code — a FALSE RED, which this
#     project treats as worse than the bug it fixes, and one with no escape
#     hatch, because `suiterun.run_suite` SYNTHESISES its command from
#     `langfloor.resolve_runner_tag` and there is no per-command prefix to set.
#     `target_env` restores $PYTHONPATH from this variable and drops this
#     variable itself, so the target sees exactly what it would have seen with
#     no plugin in the picture.
#
#     NOT A NEW EXPOSURE, and the asymmetry is the whole point: the code this
#     value reaches is the TARGET's own code, which is already executing in its
#     own repo under its own runner. The isolation that matters here is the
#     PLUGIN's, and that stays pinned.
#
#     WRITTEN UNCONDITIONALLY on purpose. Its ABSENCE tells `target_env` that
#     this hook never ran OR that the write was torn before this line, and both
#     of those mean the same thing to it: no recorded original exists, so it
#     must neither invent nor destroy a $PYTHONPATH. (The first case is a bare
#     `python3 -m scripts.<mod>` outside a session; the second is the ordering
#     residue documented on the single printf below.) Were this line skipped for
#     an unset ambient value, "hook ran, user had no PYTHONPATH" would collapse
#     into that same absence, and the plugin root would leak onto target builds
#     — where the plugin's own `scripts/` and `tests/` packages can shadow the
#     target's.
#
#     The value is ATTACKER-STEERABLE and lands in a file the host SOURCES, so
#     it goes through `shquote` below like every other value on that line.
#
#     A non-empty ambient value is reported once on stderr (the bytes are not
#     echoed).
#
#     MEASURED, AND THE ANSWER IS NO — this was an OPEN VERIFICATION ITEM and is
#     now closed against the real binary. probe/probe_cc_envfile_sessionstart.sh
#     launches a genuine `claude -p` session with an ambient $PYTHONPATH set (so
#     this line certainly fires) and asks the model to report verbatim any text
#     it received mentioning `init-env.sh`. Result: `DIAGNOSTIC_SEEN=NONE`,
#     i.e. `stderr_diagnostic=not-surfaced`. A command hook's stderr on a ZERO
#     exit does NOT reach the session, exactly as suspected.
#
#     THE LINE IS KEPT ANYWAY, deliberately and with its purpose narrowed: it is
#     the only trace available from inside a POSIX shell, it costs one line, and
#     it IS visible under `--debug` and to anything capturing the hook's stderr
#     directly. What it must never be is DISCLOSURE — no behaviour here depends
#     on a user seeing it, and nothing downstream may start assuming they did.
#   * ATLAS_SESSION_ID   — the stable Claude Code session identifier, read from
#     the "session_id" field of the SessionStart event JSON on stdin (the
#     common field present on every Claude Code hook payload). This is the
#     Claude Code-native replacement for Kimi CLI's SKILL-body `${KIMI_SESSION_ID}`
#     substitution: orchestrator invocations now source the run/session id from
#     this session-wide env var instead. Only written when stdin actually
#     carries a non-empty session_id that also passes the allowlist below — a
#     missing, unparsable OR REJECTED payload leaves ATLAS_SESSION_ID unset
#     rather than failing this hook. When it is unset the consumer that needs it
#     fails CLOSED rather than degrading: `skills/atlas/SKILL.md`'s INIT floor
#     guard emits `ATLAS-PRECONDITION-FAILED` and the run aborts, because its
#     `/tmp/atlas-$ATLAS_SESSION_ID-<what>` scratch paths would otherwise
#     collapse onto a fixed world-writable `/tmp/atlas--<what>`.
#
# This hook reads the SessionStart event JSON from stdin (for session_id only)
# and WRITES the env-file lines above; it never touches the target repo's
# working tree.
#
# THE FOURTH DOOR, recorded here so no reader takes the list above for a
# complete one. CPython resolves modules from FOUR ambient channels, and this
# hook's persisted posture closes THREE of them session-wide: the interpreter's
# own cwd/script dir (PYTHONSAFEPATH=1), $PYTHONPATH (pinned to the plugin root),
# and the user site directory plus its `usercustomize` startup import
# (PYTHONNOUSERSITE=1). The fourth, $PYTHONHOME, relocates the STDLIB ITSELF and
# is NOT closed session-wide: it is only unset for this hook's own python3, in
# the scrubbed command substitution far below. An ambient $PYTHONHOME pointing at
# a complete stdlib mirror therefore still reaches every later plugin
# interpreter, including the one that loads the FROZEN gate. It cannot be closed
# from here — an env file can export a value but cannot export an UNSET, and
# hard-setting $PYTHONHOME would break every host with a relocated interpreter.
#
# TWO WAYS IT WRITES NOTHING AT ALL, both deliberate and both loud, listed here
# because the summary above otherwise reads as an unconditional promise:
# a missing $CLAUDE_PLUGIN_ROOT or $CLAUDE_ENV_FILE (`${VAR:?}`), and a
# $CLAUDE_PLUGIN_ROOT that is not an ABSOLUTE path (see the check below the
# assignments). Each exits non-zero before the single write, so there is never a
# partial env file to reason about. Every OTHER failure here is fail-open by
# design and costs only ATLAS_SESSION_ID.
#
# Strict mode is POSIX-only on purpose. `-o pipefail` is a bashism that dash
# does not implement, and dash IS /bin/sh on Debian/Ubuntu; `hooks/hooks.json`
# runs this file as `sh "<path>"`, so the shebang is bypassed and the real
# interpreter is whatever /bin/sh is. Under dash `set -euo pipefail` aborted
# this hook on its very first executable line ("Illegal option -o pipefail",
# exit 2), leaving $CLAUDE_ENV_FILE empty and ALL SIX variables above unset
# for the entire session. Dropping pipefail costs nothing here: the only
# pipeline in this file already ends in `|| true` and is deliberately
# fail-open, so pipefail could never have acted on it.
#
# WHY `set -eu` AND NOT the `trap 'exit 0' EXIT` that hooks/telemetry.sh and
# hooks/session-resume.sh use: this is the only hook whose output the HOST
# SHELL SOURCES. A forced exit 0 over a half-written $CLAUDE_ENV_FILE would
# hand the host a truncated assignment to evaluate, so a write that fails
# part-way must abort loudly instead. (Same shape as the deliberate trap
# opt-out documented in hooks/guard-destructive.sh, for a different reason:
# there a trap would override the deny `exit 2`.)
set -eu

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT is not set}"
ENV_FILE="${CLAUDE_ENV_FILE:?CLAUDE_ENV_FILE is not set}"

# The plugin root must be ABSOLUTE, and this is a HARD failure. `${VAR:?}` above
# checks exactly one property — non-empty — and that was the whole of the
# validation while this value became the SOLE entry on a session-wide
# $PYTHONPATH.
#
# MEASURED against the pre-fix hook: `CLAUDE_PLUGIN_ROOT='.'` persisted
# `export PYTHONPATH='.'`, and a later python3 spending that value with
# `PYTHONSAFEPATH=1` on EXECUTED a `sitecustomize.py` out of an untrusted cwd.
# A relative entry resolves against EACH PROCESS's own working directory, which
# for this plugin is the target repo — so one relative root reopens, for the
# whole session and in every directory the session visits, precisely the
# module-shadowing class `PYTHONSAFEPATH=1` is here to close. An earlier
# `keepabs` helper enforced absolute-only on the AMBIENT entries and was deleted
# with them; the invariant was never applied to the one entry that survived.
#
# FAIL CLOSED, unlike the deliberately fail-open session_id path below. The
# asymmetry is not an inconsistency: a missing session_id costs run-id
# stability, while this value IS the entire `sys.path` every plugin interpreter
# in the session will use. Persisting `PYTHONPATH='.'` must be impossible, not
# merely reported, so nothing is written and the hook exits non-zero.
#
# The exit STATUS is a fixed 2 rather than whatever `${VAR:?}` would have
# produced, because that differs by shell — MEASURED: 2 under dash, /bin/sh and
# busybox, 1 under bash 5.2.21. Tests assert non-zero, which is the property
# that matters. NOT ASSERTED HERE: what Claude Code does with a non-zero
# SessionStart command hook, which is unmeasured (see the stderr OPEN
# VERIFICATION ITEM in the header). The guarantee this line actually keeps is
# local and complete on its own — the bad value never reaches the env file.
case "$PLUGIN_ROOT" in
    /*) ;;
    *)
        printf '%s\n' "init-env.sh: CLAUDE_PLUGIN_ROOT is not an absolute path; refusing to persist a relative PYTHONPATH, which would resolve against each process's own working directory — including the target repo's. Nothing was written to CLAUDE_ENV_FILE." >&2
        exit 2
        ;;
esac

# Emit "$1" as a single-quoted shell word, rewriting every embedded `'` to the
# standard `'\''` sequence. Everything else — `"`, `$`, a backtick, a literal
# newline, a backslash — is inert inside single quotes, so the result is safe by
# construction for a file that gets SOURCED, and an honest path containing any
# of those characters still round-trips byte for byte.
#
# This exists because the values written below reach a SOURCED file and were
# previously interpolated into DOUBLE-quoted lines. The worst of them used to be
# $PYTHONPATH, which is AMBIENT rather than host-issued — a checked-out repo
# steers it through .envrc/direnv, a project `.claude/settings.json` env block,
# or a devcontainer wrapper — and `PYTHONPATH='/x"; touch /tmp/pwned; :"' closed
# the assignment and ran the command on source. THAT VALUE STILL REACHES THIS
# FILE, and saying otherwise would be the most dangerous sentence in the hook:
# it no longer lands on $PYTHONPATH, but it is written VERBATIM as
# $ATLAS_ORIG_PYTHONPATH (see the header) so `proccap.target_env` can hand the
# target's own build the path the target actually had. Parking it under a name
# no interpreter consults removes the sys.path hazard, NOT the injection one —
# the file is sourced either way — so this function is exactly as load-bearing
# for it as it ever was. Alongside it: $CLAUDE_PLUGIN_ROOT, host-issued but an
# honest path that may legitimately carry a space, a quote, a `$` or a backtick,
# and the stdin-borne session_id, which is untrusted payload outright. Those
# lines had never actually executed on Debian/Ubuntu, because
# the `set -euo pipefail` above aborted the hook first — fixing the portability
# defect is what put them on a reachable path. The quoting stays in place for
# all three: the plugin root is the only path value the SESSION's own
# interpreters inherit, so mangling it breaks `from scripts import ...`
# outright, and a mangled $ATLAS_ORIG_PYTHONPATH silently hands the target's
# build a path it never had.
#
# Pure POSIX parameter expansion, no fork and no external tool, on purpose.
# python3's `shlex.quote` would do the same job in one line, but `shlex` appears
# nowhere in scripts/ or hooks/ and, more importantly, routing these five
# UNCONDITIONAL exports through python3 would newly couple them to an
# interpreter whose failure this hook already tolerates on the session_id path
# (`|| true` below) — a missing or broken python3 would then reproduce the exact
# zero-byte env file the portability fix exists to prevent.
#
# MEASURED, AND IT DOES — this was an OPEN VERIFICATION ITEM and is now closed
# against the real binary. probe/probe_cc_envfile_sessionstart.sh launches a
# genuine `claude -p` session with an ambient $PYTHONPATH carrying a `";` command
# break-out, a single quote, a space, a `$` and a backtick, and reads back what a
# Bash tool call IN THAT SESSION actually holds. Result: ATLAS_ORIG_PYTHONPATH
# matched the hostile value BYTE FOR BYTE (`orig_pythonpath=yes`) and the
# break-out did not run (`no_injection=yes`). So the $CLAUDE_ENV_FILE consumer
# does perform POSIX quote removal on the single-quoted form, this function's
# output survives it unmangled, and the injection it exists to stop is stopped
# end to end rather than only in this repo's own test shells.
shquote() {
    _q_rest="$1"
    _q_out=""
    while [ "${_q_rest#*\'}" != "$_q_rest" ]; do
        _q_out="${_q_out}${_q_rest%%\'*}'\\''"
        _q_rest="${_q_rest#*\'}"
    done
    printf "'%s'" "${_q_out}${_q_rest}"
}

# `printf '%s\n'`, never `echo`: dash's builtin echo does XSI backslash
# processing UNCONDITIONALLY, so a value containing the two characters `\` `n`
# became a REAL newline — terminating the assignment and starting a fresh line
# in a file that gets sourced. That is a quote-free injection no quoting can
# fix. printf's `%s` is escape-inert in sh/dash/bash/busybox alike. Only the
# FORMAT string carries `\n` escapes; every attacker-reachable value travels
# through a `%s` conversion, which never re-interprets its argument.
#
# ONE printf, and THE TWO ISOLATION SWITCHES FIRST, because these five are a
# single security posture. Written as five appends under `set -e`, a failure
# part-way (ENOSPC, a read-only $CLAUDE_ENV_FILE) aborted the hook with
# ATLAS_PLUGIN_ROOT and PYTHONPATH already exported and PYTHONSAFEPATH absent —
# precisely the untrusted-cwd module-shadowing state
# tests/test_syspath_isolation.py exists to prevent.
#
# THE HONEST CONTRACT, because the obvious claim is FALSE: wrapping those
# appends in `{ ...; } >> "$ENV_FILE"` groups the REDIRECTION (one open), not
# the writes. Measured with strace under dash, that shape still issued one
# write(2) per append, so it never delivered the "all or none" it was
# annotated with. Collapsing them into a single printf makes the ordinary case
# one write(2) — also measured — but the property this file can actually keep is
# ORDERING, NOT ATOMICITY: stdio can still short-write on ENOSPC, and a buffer
# past BUFSIZ (a very long plugin root) is split by definition, so a torn FINAL
# line remains possible and would leave an unterminated quote that on source
# swallows everything after it, including lines other SessionStart hooks append
# to this same file. What ordering does buy is that every surviving PREFIX is a
# SAFE prefix, in TWO senses now: PYTHONSAFEPATH=1 and PYTHONNOUSERSITE=1 are
# both complete before any path-bearing line begins, so neither isolation switch
# can be the line that goes missing; and ATLAS_ORIG_PYTHONPATH is complete
# before the pinned PYTHONPATH, so no prefix can carry the pin while `target_env`
# reads "no recorded original" and leaves it in place. That residue is not
# fixable from inside a POSIX shell append; it is recorded rather than papered
# over, and tests/test_init_env_hook.py covers the cannot-open path only, never a
# mid-write tear.
#
# The `$(shquote ...)` capture escapes command substitution's trailing-newline
# stripping only because shquote's output always ends in `'`, so there is never
# a trailing newline to strip. That is luck, not design — the session_id capture
# below has no such luck and defends itself explicitly.

# Leave a trace when an ambient $PYTHONPATH was present, because repointing it is
# a decision the user can otherwise only observe as a mystery: their own value
# stops applying to the session's own interpreters, and without this line the
# only visible symptom is an import that used to work and now does not. Same
# contract as the session_id diagnostic below — one line, and the BYTES ARE NOT
# ECHOED, because stderr reaches a terminal and reprinting attacker-controlled
# bytes there is its own escape-sequence problem.
#
# NOBODY SEES THIS LINE IN AN ORDINARY SESSION — MEASURED, see the header. A
# command hook's stderr on a zero exit does not reach the session, so it is kept
# as a cheap trace (visible under `--debug`, or to anything capturing the hook's
# stderr directly) and is NOT relied on as disclosure to the user.
#
# Silent when the variable was unset or empty, which is the overwhelmingly common
# case: a line printed on every ordinary session is a line nobody reads, and this
# one has to still be legible on the session where it matters. `${PYTHONPATH-}`
# rather than `${PYTHONPATH:-}` is deliberate only for readability — `[ -n ... ]`
# treats unset and empty alike, and CPython contributes no sys.path entry for
# either (MEASURED on CPython 3.12.3: `PYTHONPATH=` and an unset PYTHONPATH
# produce a byte-identical `sys.path`), so both are correctly silent.
if [ -n "${PYTHONPATH-}" ]; then
    printf '%s\n' "init-env.sh: an ambient PYTHONPATH was set; the session's own PYTHONPATH is pinned to the plugin root, so neither PYTHONPATH nor the user site directory can steer module resolution for the session's own interpreters (\$PYTHONHOME still can — it relocates the stdlib itself and is scrubbed only for this hook's own interpreter). The original value is preserved as ATLAS_ORIG_PYTHONPATH and is restored for target builds by scripts/proccap.py::target_env; set it per command if you need it for anything else." >&2
fi

# The plugin root is written TWICE, as ATLAS_PLUGIN_ROOT and as the whole of
# PYTHONPATH. One `shquote` capture feeds both `%s`, so there is exactly one
# quoting decision to get right, and no expression in either of those two `%s`
# can reintroduce the ambient value.
#
# ATLAS_ORIG_PYTHONPATH joins the SAME single write, and it is written on EVERY
# run — the expansion collapses unset to the empty string on purpose. Its
# absence is the evidence `proccap.target_env` has that this hook never ran, or
# that the write was torn before this line; see the header.
#
# `${ATLAS_ORIG_PYTHONPATH-${PYTHONPATH-}}` is the RE-FIRE GUARD, and it is the
# reason this cannot be the simpler `${PYTHONPATH-}` it used to be: the matcher
# is `"*"`, so on the second SessionStart the ambient $PYTHONPATH IS the pinned
# plugin root this hook itself wrote, and recording that would destroy the
# user's real original for the rest of the session (measured — see the header).
# An already-recorded original therefore wins, and `-` rather than `:-` means an
# already-recorded EMPTY one wins too.
#
# THE ORDER IS THE GUARANTEE, and it changed for a reason. The two isolation
# switches still come first, so no surviving prefix can carry a path-bearing
# line with the isolation off. ATLAS_ORIG_PYTHONPATH now comes BEFORE the pinned
# PYTHONPATH, where it used to come after: a tear in that older final line left
# PYTHONSAFEPATH + ATLAS_PLUGIN_ROOT + PYTHONPATH=<plugin root> with
# ATLAS_ORIG_PYTHONPATH ABSENT, and absence is exactly what `target_env` reads
# as "no recorded original, leave PYTHONPATH alone" — so the pin survived onto
# every target build with nothing left to override it. In this order no
# surviving prefix can carry the pin without the value that overrides it, and
# the worst a tear can now cost is the pin itself, which breaks the plugin's own
# imports loudly instead of false-REDding the target quietly.
PLUGIN_ROOT_Q="$(shquote "$PLUGIN_ROOT")"
printf 'export PYTHONSAFEPATH=1\nexport PYTHONNOUSERSITE=1\nexport ATLAS_PLUGIN_ROOT=%s\nexport ATLAS_ORIG_PYTHONPATH=%s\nexport PYTHONPATH=%s\n' \
    "$PLUGIN_ROOT_Q" "$(shquote "${ATLAS_ORIG_PYTHONPATH-${PYTHONPATH-}}")" "$PLUGIN_ROOT_Q" >> "$ENV_FILE"

# Read the SessionStart event JSON from stdin (fail-open to empty object) and
# pull out "session_id", same JSON-handling convention as hooks/telemetry.sh
# and hooks/guard-destructive.sh (python3 owns all JSON parsing; no jq
# dependency). A read/parse failure or an absent/non-string field yields an
# empty SESSION_ID, and nothing is persisted in that case.
#
# WHY THE `X` SENTINEL — what a POSIX shell can and cannot carry across `$( )`:
#
#   * TRAILING NEWLINES: STRIPPED, and the sentinel restores them. `$( )` removes
#     EVERY trailing newline from its output. Without the sentinel a payload of
#     `"abc\n"` reached the allowlist below as `abc`, was ACCEPTED, and the hook
#     exported an ATLAS_SESSION_ID DIFFERENT from the id the payload carried —
#     silently, with no diagnostic, while `ctxstore.valid_run_id("abc\n")` is
#     False. The gate was inspecting a value the shell had already mangled, so
#     the "strictly stricter than ctxstore" contract below was untrue for that
#     whole input class. Appending one `X` inside python3 and stripping exactly
#     one `X` back off leaves `$( )` no trailing newline to strip, so the newline
#     SURVIVES to the gate and is rejected like any other out-of-charset byte. An
#     honest id ending in `X` is unharmed: only the one `X` python3 added is
#     removed.
#   * TRUNCATION: DETECTABLE. Output not ending in the sentinel cannot have come
#     from a completed write (no python3 at all, or a crash mid-write), so it is
#     treated as NO id rather than as a truncated one.
#   * NUL: UNRECOVERABLE IN THE SHELL, so python3 handles it first. A POSIX shell
#     variable cannot hold a NUL byte at all — command substitution drops it
#     before any code here runs, which let `"a\0b"` be accepted as `ab`. No
#     sentinel can rescue that, so python3 maps NUL to a newline BEFORE the value
#     leaves the interpreter. This cannot change a verdict: a value containing
#     NUL is already outside `[A-Za-z0-9._-]`, so ctxstore rejects it, and the
#     gate below rejects a newline too. Unlike dropping the byte, it keeps the
#     value NON-EMPTY, so the rejection diagnostic still fires instead of the
#     case masquerading as an absent id.
#
# WHY THE PYTHON ENVIRONMENT IS SCRUBBED FOR THIS ONE CALL. Everything above
# concerns what gets PERSISTED; this line is about what the hook itself RUNS,
# and it was arbitrary code execution at SessionStart merely from opening a
# repository. There are THREE independent startup channels here, all of them
# reachable through the same ambient environment (.envrc/direnv, a project
# `.claude/settings.json` env block, a devcontainer wrapper), and each was
# MEASURED on CPython 3.12.3 rather than reasoned about:
#
#   * $PYTHONPATH. python3 imports `json` here, and CPython searches PYTHONPATH
#     ahead of the stdlib — so an ambient PYTHONPATH pointing at a directory
#     holding a hostile `json.py` ran that file's top level INSIDE this hook.
#     MEASURED against the pre-fix hook: the marker was created and the hook
#     still exited 0, so the compromise was also SILENT.
#   * $PYTHONUSERBASE / the USER SITE directory. This one needs NO import
#     statement in the program at all: CPython's `site` module locates the user
#     site directory from $PYTHONUSERBASE and imports `usercustomize` AT
#     STARTUP. MEASURED: a `usercustomize.py` planted through PYTHONUSERBASE
#     EXECUTED inside this hook (rc=0) with PYTHONSAFEPATH=1 set and PYTHONPATH
#     unset — neither of those switches touches this channel. `PYTHONNOUSERSITE=1`
#     is the one that closes it: MEASURED, it suppresses both the user-site
#     addition and the `usercustomize` import, because CPython guards
#     `execusercustomize()` on the same ENABLE_USER_SITE flag. Unsetting
#     $PYTHONUSERBASE as well removes the attacker's ability to RELOCATE that
#     directory; on this host, with no `~/.local/.../usercustomize.py` present,
#     the unset alone was enough, but that is a property of the host, not of the
#     defence, so both are applied.
#   * $PYTHONHOME. MEASURED and SETTLED, having first looked unsettleable: a
#     PARTIAL fake home (one `os.py`) only aborts the interpreter, which reads
#     as a denial of service. Against a COMPLETE stdlib mirror it is full code
#     execution — the hook's own `import json` loaded the mirror's
#     `json/__init__.py` and ran its top level, with PYTHONSAFEPATH=1 on and
#     PYTHONPATH unset, and `json.loads` still worked so nothing downstream
#     noticed. (An early attempt using `os.py` as the witness reported a false
#     NEGATIVE: `os` is a deep-frozen module in CPython 3.11+, so its
#     `__file__` points at the attacker's copy while the executed code comes
#     from the frozen one. A non-frozen module is required to witness this.)
#
# THE COST OF UNSETTING $PYTHONHOME, stated rather than glossed: a host that
# legitimately sets it for a relocated interpreter loses it here, and python3
# may then fail to start. Locally that is bounded by the fail-open below — no
# ATLAS_SESSION_ID, no abort — the same bound the hook already accepts for a
# missing python3. THAT LOCAL BOUND IS NOT THE WHOLE COST, and saying so here
# would be the misleading half: an unset $ATLAS_SESSION_ID used to collapse
# `skills/atlas/SKILL.md`'s `/tmp/atlas-$ATLAS_SESSION_ID-<what>` scratch paths
# onto the FIXED, world-writable `/tmp/atlas--<what>`, which is written and read
# back to drive the frozen packet. That is why INIT now fails CLOSED on an empty
# $ATLAS_SESSION_ID with the `ATLAS-PRECONDITION-FAILED` line — this hook
# staying quiet is only safe because the consumer refuses to run without the
# value. NOT MEASURED: whether any real host in this project's use actually sets
# $PYTHONHOME.
#
# WHAT THIS SCRUB DOES NOT DO, because the persisted posture and this one are
# easy to conflate: it protects THIS HOOK'S OWN python3 only. $PYTHONHOME is NOT
# among the exported lines above and cannot be — exporting an unset is not a
# thing a sourced env file does, and hard-setting it would break every host with
# a relocated interpreter. So for the REST OF THE SESSION $PYTHONHOME remains an
# OPEN channel: a session-wide ambient $PYTHONHOME pointing at a complete stdlib
# mirror still reaches every later plugin python3, including the one that loads
# the FROZEN gate. PYTHONSAFEPATH closes the cwd door, the pinned PYTHONPATH
# closes the PYTHONPATH door, PYTHONNOUSERSITE closes the user-site door;
# $PYTHONHOME is the fourth and it is not closed here. Recorded, not fixed:
# closing it needs a mechanism this hook does not have.
#
# NOT REDUNDANT WITH THE PINNING ABOVE, which is the tempting reading now that
# the ambient value never lands on the persisted $PYTHONPATH. That decision
# governs what this hook WRITES for the rest of the session; this scrub governs
# what this hook's OWN interpreter reads, and that interpreter takes its
# environment from the inherited — ambient — one, not from the file being
# written a few lines up. Delete the scrub and the hostile `json.py` executes
# again on the very next session with the persisted value still perfectly clean.
# Three channels, and tests/test_init_env_hook.py arms a control for each, so a
# fixture that proves nothing fails loudly instead of passing quietly.
#
# `unset` is safe here and needs no restore: command substitution runs in a
# subshell, so the parent's variables are untouched — measured under dash, bash,
# busybox sh and /bin/sh, in each of which the parent still held its value
# afterwards, `unset` of an ALREADY-ABSENT variable exited 0, and `unset` of
# several names in one call was accepted (so `set -eu` has nothing to trip on).
# The persisted lines were already written above and read none of these
# variables, so the order genuinely cannot matter. Only the stdlib is needed by
# the parser below, which is why removing all three outright costs nothing that
# this hook uses.
#
# THE $PATH ASYMMETRY, stated rather than left implicit: `python3` below is still
# resolved from the AMBIENT $PATH — the same channel (.envrc/direnv, a project
# `.claude/settings.json` env block, a devcontainer wrapper). It is deliberately
# NOT pinned, and that is not an inconsistency with the scrub above: the
# variables differ in what a fix COSTS. Pinning $PATH would be theatre —
# hooks/hooks.json invokes this file as `sh "<path>"`, so $PATH already chose the
# interpreter executing these very lines, and `cat` on the next line resolves
# through it as well, so against a hostile $PATH this hook was lost before line
# 1 — and a hard `PATH=/usr/bin:/bin` would break every honest host whose python3
# lives under pyenv, conda, nix or homebrew. Dropping $PYTHONPATH,
# $PYTHONUSERBASE and the user site directory breaks nothing here: the parser
# needs no third-party module. $PYTHONHOME is the one scrubbed variable with a
# real cost, bounded and recorded above. A fix that breaks working sessions is
# worse than the gap; one that breaks nothing is not.
#
# STRICTLY SCOPED, recorded rather than quietly widened: hooks/telemetry.sh,
# hooks/guard-destructive.sh and hooks/session-resume.sh share this
# `python3 -c 'import json'` idiom and are reachable the same way — measured,
# telemetry.sh loaded the same hostile json.py. They are NOT touched from here;
# they need their own repo-wide pass.
INPUT="$(cat 2>/dev/null || printf '%s' '{}')"
RAW_SESSION_ID="$(unset PYTHONPATH PYTHONUSERBASE PYTHONHOME; printf '%s' "$INPUT" | PYTHONSAFEPATH=1 PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    v = d.get("session_id") if isinstance(d, dict) else None
    v = v if isinstance(v, str) else ""
    sys.stdout.write(v.replace("\0", "\n") + "X")
except Exception:
    pass
' 2>/dev/null || true)"
case "$RAW_SESSION_ID" in
    *X) RAW_SESSION_ID="${RAW_SESSION_ID%X}" ;;
    *)  RAW_SESSION_ID="" ;;
esac

# session_id arrives as UNTRUSTED payload data and the file it lands in is
# SOURCED by the host shell, so it is gated on ctxstore's own run_id charset —
# `scripts/ctxstore.py` `_RUN_ID_RE`: [A-Za-z0-9._-], no leading '-' (argv
# option injection), never '.' or '..', at most 128 characters.
#
# THE HONEST CONTRACT, because the obvious justification is false: this gate is
# STRICTLY STRICTER than ctxstore's runtime path, not merely a preview of it.
# `ctxstore.valid_run_id` is called only from `write_artifact_confined`;
# `init_run` builds `_run_dir` as `pathlib.Path(base) / run_id` with NO
# validation, so `init_run(base, "a/b")` succeeds and creates a nested directory
# even though `valid_run_id("a/b")` is False — and `skills/atlas-weave/SKILL.md`
# deliberately uses a hierarchical run_id containing '/'. So this DOES invent a
# failure mode of its own: a rejected session_id silently leaves
# ATLAS_SESSION_ID unset, and that unset variable has TWO known downstream
# consequences, both accepted here rather than fixed here:
#   1. `scripts/resume.py` falls through to `max(candidates, key=mtime)` and can
#      resume a DIFFERENT run.
#   2. `skills/atlas/SKILL.md:250,266` interpolate the unset variable into
#      `/tmp/atlas-$ATLAS_SESSION_ID-packet.json`, which collapses to the FIXED,
#      world-writable path `/tmp/atlas--packet.json` and is then written and
#      re-read. That exposure is PRE-EXISTING and universal today (the variable
#      is unset in every live session, because this hook was aborting at
#      `set -euo pipefail` before it wrote anything), and this hook's fix
#      strictly shrinks it by making the normal path export a real id. It is not
#      repaired from here: synthesising a substitute id would break DS-2 run-id
#      stability across compaction. It belongs to SKILL.md, which must stop
#      depending on an unset variable naming a shared /tmp path.
# Both are accepted costs — arbitrary command execution from a sourced env file
# is worse — and the one stderr line below leaves a trace when it happens.
#
# LC_ALL=C, scoped to this subshell: `[A-Za-z0-9._-]` is a COLLATION-ordered
# range, and on older bash (4.x, and the 3.2 that ships on macOS) `[a-z]` can
# admit non-ASCII letters that ctxstore's codepoint-based `_RUN_ID_RE` rejects.
# This does NOT reproduce on the shells measured here — bash 5.2.21, dash and
# busybox all reject `xéy` under both C and en_US.UTF-8 — so it is hardening for
# older hosts, not a live bug. It also settles a real portability skew for free:
# `${#VAR}` counts BYTES in dash but CHARACTERS in bash, and under LC_ALL=C both
# count bytes, so the 128 bound means the same thing everywhere.
#
# A rejected value is blanked rather than fatal — the same fail-open contract
# the header documents for a missing session_id.
SESSION_ID="$(
    LC_ALL=C
    export LC_ALL
    CANDIDATE="$RAW_SESSION_ID"
    case "$CANDIDATE" in
        -*|.|..|*[!A-Za-z0-9._-]*) CANDIDATE="" ;;
    esac
    if [ "${#CANDIDATE}" -gt 128 ]; then
        CANDIDATE=""
    fi
    printf '%s' "$CANDIDATE"
)"

# Leave a trace when a non-empty session_id was thrown away, so an attempted
# injection is not silent. The rejected bytes are NOT echoed: stderr reaches a
# terminal, and reprinting attacker-controlled bytes there is its own escape
# sequence problem.
if [ -n "$RAW_SESSION_ID" ] && [ -z "$SESSION_ID" ]; then
    printf '%s\n' "init-env.sh: session_id rejected by the run_id allowlist; ATLAS_SESSION_ID left unset" >&2
fi

# Written through the same `shquote` as the two values above, so the quoting is
# uniform and stays safe by construction even if the charset is ever widened.
if [ -n "$SESSION_ID" ]; then
    printf 'export ATLAS_SESSION_ID=%s\n' "$(shquote "$SESSION_ID")" >> "$ENV_FILE"
fi
