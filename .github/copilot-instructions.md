## Tests
- Run tests with `uv run pytest`, not system `pytest`.
- Run a focused test with `uv run pytest path/to/test_file.py`.
- Visual tests are excluded from the default test run.

## Commit Messages
- Format every suggested commit message as `<type>: <short summary>`.
- Put a blank line after the summary, followed by one or more flat hyphen bullets describing the changes.
- Use a lowercase type from: `feat`, `fix`, `format`, `ci`, `docs`, `test`, `refactor`, `perf`, `build`, `chore`, `misc`.
- Use `misc` only when no more specific type applies.
- Choose `feat` for new functionality, `fix` for bug fixes, `format` for formatting-only changes, and `ci` for CI/workflow changes.
- Always provide a concise but descriptive summary in the commit message.
- Use the imperative mood in the summary (e.g., "Add feature" instead of "Added feature").