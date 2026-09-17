# Working on Stories

Read [the vision](docs/VISION.md) for product intent and [the contracts](contracts/)
for caller-facing requirements and internal execution obligations.

## Code structure

- Put the Python library in `src/amplifier_smart_tool_stories/`.
- Keep the `stories` CLI thin: argument parsing and I/O call library functions.
- Package prompts, styles and templates as resources; do not depend on a checkout.
- Use `amplifier-agent` for model-backed execution. Keep its integration behind the
  library boundary and off import, help and deterministic code paths.
- Put executable checks and fixtures in `tests/`.

## Changes

- Preserve source references and uncertainty through research, generation and conversion.
- Test library behavior as well as the CLI, including missing credentials, invalid
  inputs and incomplete artifacts.
- Check installation from an unrelated directory without relying on developer state.
- Keep generated outputs, credentials and private source material out of the repository.
- Preserve upstream licenses and attribution when reusing code or assets.
- Keep work items and their acceptance criteria in Work Tracker, not planning documents.
- Keep this file to durable contributor guidance; do not add session status or deliberation.
