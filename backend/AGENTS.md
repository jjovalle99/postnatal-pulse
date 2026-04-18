## Skills
Load `python-style-always`, `tdd` before any work.

## Gates
All pass before commit:
- `uv run ruff check`
- `uv run ty check`
- `uv run pytest`

## API Gotchas
- Mistral SDK: `from mistralai.client import Mistral``.