# Rules (read and follow always)

## Before writing code
- Read and follow skills `python-style-always` and `tdd`.
- Use `colgrep` as the primary search tool. Load `bun` skill before JS/npm work.

## Design
- Prefer battle-tested libraries over custom code. Research modern options via subagents when you don't already know a library that fits.
- Dependency injection: pass I/O and service dependencies as arguments. Module-level constants, loggers, and config are fine as globals.
- YAGNI: only build what was requested.

## TDD process
- One red-green-refactor cycle per behavior (a behavior = one observable input/output or side effect change). Never more than one failing test at once.
  Example: "read canvas" = 3 cycles: (1) test it calls files.info, green; (2) test it fetches HTML and converts to markdown, green; (3) test error on missing file, green; then $simplify, commit.
- NEVER commit after a cycle. The only commit point is after `$simplify`. Full flow:
  1. Cycle 1: red -> green -> refactor -> pass gates (`uv run pytest`, `uv run ruff check`, `uv run ty check`). NO commit.
  2. Cycle 2: red -> green -> refactor -> pass gates. NO commit.
  3. ... repeat for all cycles ...
  4. Use `$claude-code-thoughts` on the current diff for an adversarial design/architecture review.
  5. Fix structural issues if any.
  6. Run `$simplify`. Address every finding. If a finding conflicts with an explicit user decision, skip it and note why.
  7. Pass gates again (`uv run pytest`, `uv run ruff check`, `uv run ty check`).
  8. NOW commit.
  9. Next feature.

## Testing
- Mock the narrowest target (e.g. `asyncio.create_subprocess_exec`, not `asyncio`).
- Realistic mocks: correct types, sync/async signatures, state transitions. Quality over quantity.

## Code style
- Avoid inline comments. Express intent through naming and structure. Inline comments are a last resort, only for non-obvious WHY (hidden constraints, workarounds, regulatory rules). Never explain WHAT. All languages (Python, JS).

## After each feature
- Update `progress.md`: mark done, summarize what was built and tradeoffs. Flag uncertain edge cases (flagging does not mean building preemptive handling).

## Skill conflicts
- If a skill (`python-style-always`, `tdd`, etc.) contradicts a rule in this file, this file wins.
- If the user contradicts this file, the user wins.
