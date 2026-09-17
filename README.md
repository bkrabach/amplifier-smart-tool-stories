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

**Development status:** HTML presentations and structured documents with shared review.

```sh
uv sync --extra dev
uv run stories --help
uv run stories manifest
```

Import or generate HTML, open a material-first review surface, add caller highlights,
and submit anchored comments that can answer or revise through embedded Amplifier
Agent. The library, CLI and dashboard share retained state. Provider choices are
OpenAI, ChatGPT, Copilot, Anthropic and Gemini; credentials and runtime preparation
are explicit. Documents support continuous/paginated reading, zoom and a toolbar
that appears when needed. PDF and editable Word exports are available with explicit
layout limits. Provider settings offer session-only selection, model discovery, connection tests and native sign-in. PowerPoint and spreadsheet work remain deferred.

Generation selects packaged expertise for case studies, releases, technical explanations,
public and community communication, executive briefs, adaptation, editorial plans and
metrics interpretation. Callers describe purpose and audience; they do not route agents.
See [storytelling coverage](docs/STORYTELLING.md) for the bundle mapping and limits.
Generation uses native structured submissions.
Every generated or revised artifact receives source-fidelity and static rendered-page
model review, with at most one repair. Review findings and limits stay attached to
the exact artifact. Static rendering requires Pango; imports and reading do not.

See [usage and limits](docs/USAGE.md) and the
[operating guide](src/amplifier_smart_tool_stories/SMART_TOOL.md).

## Project documents

- [Vision](docs/VISION.md) — what Stories is for.
- [Invocation contract](contracts/invocation.v1.md) — how callers use the tool.
- [Caller interaction contract](contracts/caller-interaction.v1.md) — context,
  clarification, authority and revision continuity.
- [Dashboard contract](contracts/dashboard.v1.md) — optional review workspace,
  shared feedback/settings and presentation lifecycle.
- [Storytelling contract](contracts/storytelling.v1.md) — evidence and output quality.
- [Internal execution contract](contracts/internal-execution.v1.md) — bounded
  intelligence, artifact production and review enforcement.
- [Contributor guidance](AGENTS.md) — how to work on the code.
