# Fork configuration and pilot

This fork preserves Leafiber's Iris Memory implementation and AGPL-3.0 license.
It adds protected member notes and conservative message-driven participation.
No service credentials or deployment-specific configuration belongs in this repo.

## Install

Install this fork using AstrBot's plugin repository installer:
https://github.com/d1scolor/astrbot_plugin_iris_memory

Do not run the upstream and fork simultaneously. Back up existing Iris data before
replacing it. This is not an automatic migration of existing shared memories.

For the initial single-bot, single-group pilot:

- Select an existing AstrBot embedding provider for L2, or disable L2 initially.
  L1 and member profiles can be tested without vector retrieval. Disable L3 if not
  testing knowledge graphs. Profile analysis uses the configured LLM provider.
- Enable group memory, group profile and persona isolation. These are the fork's
  new-install defaults; existing saved values remain unchanged. Enabling isolation
  can make older shared records invisible. It does not erase or reassign them.
- Keep personality evolution, expression learning, dream tasks and timer-based
  topic initiation off. Keep context_control.enable_conversation_cleanup=false
  initially so the fork does not clear the main agent's conversation history.
- Disable AstrBot's probability-based proactive replies and competing group-context
  injection. Iris supplies its own recent group context.
- Set proactive.provider_id to an existing AstrBot provider for decisions. A fast,
  reliable model is suitable; it needs structured text output, not tools or vision.
  It sees recent group text and the configured persona. A separate provider ID
  separates workload, not necessarily physical hardware or privacy boundaries.
- Add the group's complete UMO from /sid to proactive.group_whitelist. An empty
  whitelist blocks unsolicited replies. Normal explicit mentions remain usable.
- Leave proactive.dry_run=true first. Logs say whether the judge would speak; the
  candidate event is stopped before normal generation/tools/sending.
- When decisions look appropriate, set dry_run=false. Initial hard limits are
  one unsolicited attempt per 90 seconds and three per rolling 15 minutes.
  Explicit @ requests do not consume this new unsolicited-attempt budget.

The existing proactive.enabled controls message-based evaluation. The separate
proactive.proactive_enabled enables idle-topic initiation and should stay false.
Dry-run blocks the ordinary timer signal path too; do not use manual forced
initiation commands during an observation-only pilot.

## Member notes and profile ownership

Under AstrBot's plugin data directory:

```
member_profiles/<scope-hash>/notes.md
member_profiles/<scope-hash>/observations.md
```

The hash identifies persona + group + member. observations.md contains the scope
IDs and the current structured profile so an administrator can identify the folder.
A notes-only member is registered in the profile index for deletion/cleanup.

- Edit **notes.md** on the host's persistent data volume. It is read on subsequent
  requests without restarting. Prefer atomic editor saves. File limit: 32 KiB;
  at most 6000 characters are injected per request.
- **observations.md** is a regenerated snapshot of the stored profile, including
  metadata. Do not edit it: automatic updates replace it atomically. Generated
  claims are observations, not verified facts, and may need correction.
- Human notes never get rewritten by model analysis. They are injected as member
  background data, not executable instructions. They do not grant permissions.
- Dashboard edits to structured member fields mark those fields manual. Automatic
  saves preserve manual scalar/list/custom fields. A later Dashboard correction
  can replace a locked value. The whole custom_fields dictionary is one field.
- Deleting a member profile also deletes its notes/snapshot; bulk profile deletion
  covers indexed members. Ordinary conversation reset is not memory deletion.
- Existing manually edited fields from before this patch are not automatically
  known to be human-owned. Re-save those fields through the Dashboard to lock them.

Do not store passwords or tokens in these files. Their text is sent to the selected
conversation model when injected. Do not commit profile files or plugin data.

Scope currently uses upstream persona/group/member identifiers. This fork enables
isolation but does not rewrite every upstream component into a bot-instance namespace.
Use one bot instance for the pilot; do not treat shared-persona multi-bot separation
as verified. Official QQ identifiers also must not be assumed interchangeable
between private, group and channel scenes.

## How joining is judged

Incoming text passes upstream quality/sampling/anchor gates. A genuine follow-up
can be evaluated earlier; matching a word or sender merely nominates it. The judge
receives speaker-labelled recent messages, topic state and the active persona.
It must return structured action/observation/watch/cooldown fields. It is asked to
prefer silence, avoid interrupting other people's exchanges, and offer an actual
contribution instead of treating every remark as a request for help. Group text
and remembered observations are data, not instructions to change the judge.

The judge's response cannot override the whitelist, cooldown or rolling limit.
The rolling budget persists across restart and counts **accepted attempts**, not
confirmed messages. Failed generation still consumes an attempt conservatively.
Existing Iris state/tickets handle ongoing decisions; accepted messages use the
normal AstrBot pipeline and its search/image tools.

The judge does not need private chain-of-thought output. Use decision logs and
brief structured reasons when tuning. Smaller/faster models may be sufficient;
measure missed follow-ups and irrelevant interruptions before changing models.

## Current limits and next checks

No live QQ/provider requests were sent during development. The pilot must verify
human-note injection, generation/reference inspection, reset, concurrent members,
restart and deliberate silence. Direct ComfyUI background deliveries are not yet
fed into Iris's conversational anchors. The new budget counts attempts, so it
must not be presented as confirmed attachment-delivery accounting.

Generated-profile provenance remains upstream's metadata/confidence model; this
patch does not implement message-level evidence links or a prompt-guard integration.
Markdown notes do not automatically override every RAG item or unrelated profile
field. Review/delete contradictory generated records when necessary.

## Development

Use uv and an isolated environment; do not install development dependencies into
the production AstrBot container:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python 'astrbot==4.29.3' -r requirements.txt -r requirements-dev.txt ruff
uv run --no-project --python .venv/bin/python -m pytest -q -o asyncio_mode=auto
```

Tests use mocks or local storage and must not send chat messages. AstrBot and
upstream plugin dependencies can change; SDK compatibility is tested against
4.29.3 here.

## Validation for v3.2.2

Full suite against an isolated AstrBot 4.29.3 installation: 1923 passed, 1 skipped.
This includes upstream official-QQ adapter, memory, profile, proactive decision,
Dashboard and tool-registration tests, plus new Markdown ownership and budget
checks. No live provider or QQ deployment validation is claimed. Compilation and
focused lint checks pass; inherited files retain upstream lint findings outside
the scope of this patch.
