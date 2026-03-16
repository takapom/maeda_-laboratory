"""LLM client for generating controller patches."""

from __future__ import annotations

from agent_runner.config import Config

PROMPT_TEMPLATE_V1 = """\
You are an expert drone controller engineer.

## Goal
{goal}

## Constraints
{constraints}

## Current Controller Code
```python
{controller_code}
```

## Instructions
Generate a unified diff (git diff format) that modifies only files under controller/.
The diff should improve the controller according to the goal above.
Output ONLY the diff, no explanation.
"""


def build_prompt(
    goal: str,
    constraints: str,
    controller_code: str,
    template_version: str = "v1",
) -> str:
    if template_version != "v1":
        raise ValueError(f"Unknown prompt template version: {template_version}")
    return PROMPT_TEMPLATE_V1.format(
        goal=goal,
        constraints=constraints,
        controller_code=controller_code,
    )


def generate_patch(
    config: Config,
    goal: str,
    constraints: str,
    controller_code: str,
) -> str:
    """Call LLM to generate a patch diff."""
    import openai

    prompt = build_prompt(
        goal=goal,
        constraints=constraints,
        controller_code=controller_code,
        template_version=config.prompt_template_version,
    )

    client = openai.OpenAI(api_key=config.openai_api_key)
    response = client.chat.completions.create(
        model=config.llm_model,
        temperature=config.temperature,
        messages=[{"role": "user", "content": prompt}],
    )

    content = response.choices[0].message.content or ""
    return _extract_diff(content)


def _extract_diff(content: str) -> str:
    """Extract diff block from LLM response, stripping markdown fences if present."""
    lines = content.strip().splitlines()
    # Strip ```diff ... ``` fences
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines) + "\n"
