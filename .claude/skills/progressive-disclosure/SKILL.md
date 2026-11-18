---
name: progressive-disclosure
description: Create or restructure a project's CLAUDE.md as a short index that points to topic docs in docs/, so agents load detail only when a task needs it. Use when the user wants a CLAUDE.md created, slimmed down, reorganised, or set up with progressive disclosure.
argument-hint: "Optional: topics to emphasise or files to treat as the source of truth"
---

Build a two-level memory for the project. `CLAUDE.md` is always loaded, so it holds only what nearly every task needs and an index of the docs. `docs/*.md` hold the detail, and each one is read only when the task matches it.

## Process

1. **Survey the repo.** Read any existing `CLAUDE.md`, `README`, specs or PRDs, plans, handoff notes and logs, and build or config files such as `pyproject.toml`, `package.json` and `Makefile`. Note what really exists (code, commands, folders) and what is only planned.

2. **Sort every fact into one of three places:**
   - **`CLAUDE.md`:** the project in one or two lines, its current state, the commands that exist, rules that apply to almost every task, how the user wants to work, and the docs index.
   - **A topic doc:** detail needed only for some tasks, such as architecture, domain rules, frontend, testing or workflow.
   - **Nowhere:** anything already in a spec, PRD or the code. Link to it instead of copying it.

3. **Write the topic docs** in `docs/`:
   - one topic per file, with a short kebab-case name
   - open each file with one line saying what it covers and when to read it
   - keep each file under about 100 lines, written as terse bullets with no preamble
   - state rules as rules ("Stock changes go through the safe helper"), not as history ("We decided…")
   - link to the source of truth for full detail

4. **Write `CLAUDE.md`**, aiming for under about 60 lines, in this order:
   1. title and a one-line purpose
   2. current state and the next step
   3. commands: real ones only, with planned ones clearly marked as planned
   4. always-on rules: 5 to 10 bullets that would cause real damage if missed
   5. working with the user
   6. a docs index table with the columns *Read when…* and *File*. The trigger in the first column is what lets an agent decide whether to open the file.

5. **Verify:**
   - every link resolves
   - no fact appears in two places
   - nothing is invented
   - check line counts with `wc -l`

6. **Report** the files created, their line counts, and anything that was moved or dropped.

## Rules

- **Link with plain Markdown, not `@path` imports.** Claude Code loads `@` imports at startup, which defeats progressive disclosure.
- **Never invent commands, paths or conventions.** If something is decided but not built, label it "(planned)".
- **If a `CLAUDE.md` already exists, keep the user's content.** Move detail into docs rather than deleting it, and list what moved.
- **If `docs/` already holds user-facing documentation,** put agent docs in `docs/agents/` instead and say so.
- **Don't duplicate specs.** When a PRD or spec is the source of truth, docs summarise only the rules an agent must not break and point to the spec for everything else.
- **Keep it current.** When a doc's topic changes, update that doc; when a doc is added, add it to the index.
