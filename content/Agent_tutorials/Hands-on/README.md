# Hands-on Agent Examples

Use one launcher for all ADK examples in this folder.

## Unified Commands

From `content/Agent_tutorials/Hands-on`:

```bash
uv run python launch_agent.py list
```

Launch an example from the list:

```bash
uv run python launch_agent.py run <example>
```

Shortcut form (same behavior):

```bash
uv run python launch_agent.py <example>
```

## Notes

- The launcher auto-discovers examples using `.adk` metadata.
- It starts each example with `adk web <example-root>`.
- This keeps the run workflow consistent across `D8_S1`, `Day11_S1`, and `Day2/my-py-agent`.
