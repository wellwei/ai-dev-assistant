# LangGraph Project Knowledge Assistant Development History

Date: 2026-07-08

## Recording Rule

Every implementation change, behavior change, design update, retrieval or ranking adjustment, schema migration, safety boundary change, and documentation rule change must add an entry to the dated history file for the active work date before the task is considered complete.

### Project-Level LangGraph Skills Import

- Date/session: 2026-07-08.
- Change summary: Imported the downloaded LangGraph and LangChain skill bundle into this repository as project-level skills.
- Completed or modified functionality:
  - Added `config/skills/` with the 14 skills from `/Users/cltx/Downloads/langgraph`, including LangGraph, LangChain, deep-agents, RAG, persistence, CLI, human-in-the-loop, middleware, and swarm guidance.
  - Preserved the `swarm/scripts/` supporting TypeScript files alongside `swarm/SKILL.md`.
  - Updated `skills-lock.json` hashes so every lock entry points at the checked-in project skill file content.
  - Removed macOS `.DS_Store` metadata from the imported project skill tree.
- Affected files or modules:
  - `config/skills/`
  - `skills-lock.json`
  - `docs/superpowers/history/2026-07-08-development-history.md`
- Verification:
  - Listed the imported project skill files under `config/skills/` and confirmed every expected `SKILL.md` plus `swarm/scripts/` support file exists.
  - Recomputed SHA-256 hashes for all `skills-lock.json` entries and verified every referenced project skill file matches its lock hash.
- Follow-ups:
  - If these skills are later edited rather than imported verbatim, use the skill-writing TDD workflow for each changed skill.

### Low-Context AGENTS.md Routing

- Date/session: 2026-07-08.
- Change summary: Reworked agent-facing repository guidance so Codex, Claude Code, and similar agents use `AGENTS.md` as a concise routing layer instead of reading the full README by default.
- Completed or modified functionality:
  - Reorganized `AGENTS.md` around common AGENTS.md best-practice sections: project overview, document routing, project skills, environment, build/test commands, style, git/PR workflow, boundaries, and development history.
  - Added explicit project-skill routing for `config/skills/<skill-name>/SKILL.md`, including LangGraph, LangChain, deep-agents, RAG, persistence, CLI, human-in-the-loop, middleware, swarm, and ecosystem guidance.
  - Clarified that Codex should treat `config/skills/` as task-specific project documentation and should not assume automatic skill loading.
  - Changed both `AGENTS.md` and `CLAUDE.md` so agents do not read `README.md` by default and instead read focused docs or relevant README sections only when needed.
  - Replaced the fixed-date history example with a current-date rule that creates today's history file when missing and never appends new entries to a prior-day latest file.
- Affected files or modules:
  - `AGENTS.md`
  - `CLAUDE.md`
  - `tests/test_agent_guides.py`
  - `docs/superpowers/history/2026-07-08-development-history.md`
- Verification:
  - Added guide tests covering project-skill routing, `README.md` non-default reading, and current-date history wording.
  - Focused guide tests passed with `4 passed`.
