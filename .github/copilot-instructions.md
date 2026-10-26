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

## Commit Messages
- Format every suggested commit message as `<type>: <short summary>`.
- Put a blank line after the summary, followed by one or more flat hyphen bullets describing the changes.
- Use a lowercase type from: `feat`, `fix`, `format`, `ci`, `docs`, `test`, `refactor`, `perf`, `build`, `chore`, `misc`.
- Use `misc` only when no more specific type applies.
- Choose `feat` for new functionality, `fix` for bug fixes, `format` for formatting-only changes, and `ci` for CI/workflow changes.
- Always provide a concise but descriptive summary in the commit message.
- Use the imperative mood in the summary (e.g., "Add feature" instead of "Added feature").