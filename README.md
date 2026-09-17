# Stories

**Turn source material into stories people can use.**

Stories is a smart tool for creating evidence-based presentations, documents and
data-backed communication. Supply the material, describe the audience and purpose,
and receive an artifact with its sources and limitations—not instructions for
doing the work yourself.

The tool brings together research, narrative planning, writing, design and format
adaptation. Claims stay tied to evidence; missing information stays visible.
Creating an artifact does not publish it.

## Use it from your own environment

Stories is designed for people, agents and applications:

- **Command line:** `stories`
- **Python library:** `amplifier_smart_tool_stories`
- **Package:** `amplifier-smart-tool-stories`

Its model-backed capabilities run inside the tool rather than relying on the
caller's agent. Deterministic operations need no model credentials.

**Development status:** not yet implemented or available to install.

## Project documents

- [Vision](docs/VISION.md) — what Stories is for.
- [Invocation contract](contracts/invocation.v1.md) — how callers use the tool.
- [Caller interaction contract](contracts/caller-interaction.v1.md) — context,
  clarification, authority and revision continuity.
- [Storytelling contract](contracts/storytelling.v1.md) — evidence and output quality.
- [Internal execution contract](contracts/internal-execution.v1.md) — bounded
  intelligence, artifact production and review enforcement.
- [Contributor guidance](AGENTS.md) — how to work on the code.
