## Communication Style

Communicate concisely and directly, but never at the expense of completeness, accuracy, or clarity.

- Prioritize essential information, actionable guidance, and relevant technical details.
- Avoid unnecessary explanations, repetition, filler, generic background, and tangential information.
- Do not omit important caveats, assumptions, limitations, risks, edge cases, or trade-offs simply to make a response shorter.
- Explain the reasoning behind recommendations or decisions when it is important for understanding or making an informed choice.
- For technical explanations, include enough context to ensure the underlying concepts and implications are clear.
- Use concise bullet points, tables, or examples when they improve readability. Avoid excessive formatting.
- When presenting alternatives, explain the meaningful differences and trade-offs rather than listing options without context.
- For implementation work, clearly summarize what changed, why it changed, and any relevant testing, limitations, or follow-up considerations.
- If a detail is important for me to know or could affect a decision, include it even if doing so makes the response longer.

**Guiding principle:** Be as brief as possible, but as detailed as necessary. Never sacrifice essential information for brevity.

## Tests
- Run tests with `uv run pytest`, not system `pytest`.
- Run a focused test with `uv run pytest path/to/test_file.py`.
- Visual tests are excluded from the default test run.

## Python docstrings and style
- Follow PEP 257 conventions and use Google-style sections: Args:, Returns:, Yields:, Raises:, and Attributes: where relevant.
- Write a concise summary line, followed by a blank line before any additional explanation or sections.
- Document public classes and functions when their behavior is not self-evident. Keep trivial private helpers and straightforward test methods concise; do not add boilerplate sections.
- Include only sections that add useful information. Describe behavior, side effects, constraints, units, and meaningful exceptions; do not repeat type annotations or defaults from the signature unless needed to clarify behavior.
- Keep documented names and behavior accurate to the implementation. Do not invent exceptions, guarantees, or examples.
- Use consistent English spelling and punctuation; match the surrounding code where a project-wide choice has not been established.

## Python type hints
- Annotate function parameters and return values when their contracts can be verified; keep existing annotations accurate when changing behavior.
- Use modern Python typing compatible with the project's declared Python versions, including parameterized containers and `X | None` for nullable values.
- Reflect accepted inputs and actual return values; avoid guessing, unnecessary `Any`, casts, or suppressions to satisfy a checker.
- Check relevant callers and run the project's available type checks or diagnostics after changing annotations.

## Commit Messages
- Format every suggested commit message as `<type>: <short summary>`.
- Put a blank line after the summary, followed by one or more flat hyphen bullets describing the changes.
- Use a lowercase type from: `feat`, `fix`, `format`, `ci`, `docs`, `test`, `refactor`, `perf`, `build`, `chore`, `misc`.
- Use `misc` only when no more specific type applies.
- Choose `feat` for new functionality, `fix` for bug fixes, `format` for formatting-only changes, and `ci` for CI/workflow changes.
- Always provide a concise but descriptive summary in the commit message.
- Use the imperative mood in the summary (e.g., "Add feature" instead of "Added feature").