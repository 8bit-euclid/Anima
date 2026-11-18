## Engineering Principles

- Prefer the simplest correct solution. Favor readability and consistency over cleverness.
- Follow existing project conventions and architecture; change them only with a clear, demonstrated reason.
- Make dependencies, data flow, and side effects explicit. Avoid hidden state and mutable global state.
- Do not add abstractions, configuration options, or optimizations for hypothetical requirements. Avoid duplicated logic, but do not merge unrelated behavior into a shared abstraction to remove repetition.
- Use inheritance where the project already uses a base class as the extension point (e.g., `Effect`, `Triangulator`); otherwise prefer composition.
- Consider edge cases and failure modes, not just the happy path.
- Do not add a dependency unless the standard library or existing dependencies cannot do the job.
- Give each class and function a single clear responsibility, and keep modules cohesive. Depend on the existing abstractions (e.g., `Effect`, `Triangulator`) rather than concrete subclasses, and make subclasses honor the base class contract.
- Introduce a design pattern only when it removes real complexity in the current code, not to anticipate future needs.


## Communication Style

Be as brief as possible, but as detailed as necessary. Never sacrifice completeness, accuracy, or clarity for brevity.

- Prioritize essential information, actionable guidance, and relevant technical details. Avoid filler, repetition, generic background, and tangential information.
- Always include caveats, assumptions, limitations, risks, edge cases, and trade-offs that could affect a decision, even if this makes the response longer.
- Explain the reasoning behind recommendations when it matters for an informed choice. When presenting alternatives, explain the meaningful differences and trade-offs.
- For technical explanations, include enough context to make the underlying concepts and implications clear.
- Use concise bullet points, tables, or examples when they improve readability. Avoid excessive formatting.
- For implementation work, summarize what changed, why, and any relevant testing, limitations, or follow-up considerations.

## Implementation Workflow

- Before changing code, read the relevant code, its call sites, and its existing tests.
- Address root causes rather than symptoms. Keep changes focused; do not reformat or modify unrelated code.
- Update affected tests, docs, and in-repository callers when behavior or interfaces change. Remove code and imports made obsolete by your change.
- Do not leave placeholder logic, unexplained TODOs, or swallowed errors.
- When requirements are ambiguous, ask if the answer changes behavior; otherwise state the assumption you made.
- Review your diff for correctness and unnecessary complexity before reporting completion.

## Error Handling

- Handle errors where they can be acted on. Catch exceptions narrowly; never silently swallow them.
- Validate external input at system boundaries (user files, CLI arguments, subprocess output). Do not re-validate trusted internal data.
- Keep secrets and environment-specific values out of source code; read them from configuration.

## Testing and Verification

- Run tests with `uv run pytest`, not system `pytest`. Run one file with `uv run pytest path/to/test_file.py`.
- Visual tests are excluded from the default test run.
- Before reporting work complete, run `make format`, `make lint` (ruff), and `make test`.
- Add or update tests for new behavior and bug fixes. A bug fix needs a regression test that fails without the fix.
- Test observable behavior, not implementation details. Mock only external boundaries, such as `bpy`, `easybpy` (imported as `ebpy`), and LaTeX or subprocess calls. Do not mock internal collaborators.
- Keep tests deterministic and independent of each other.
- Never claim checks passed unless you ran them. Report any check you could not run and why.

## Python Docstrings

- Follow PEP 257 conventions and use Google-style sections: Args:, Returns:, Yields:, Raises:, and Attributes: where relevant.
- Write a concise summary line, followed by a blank line before any additional explanation or sections.
- Document public classes and functions when their behavior is not self-evident. Keep trivial private helpers and straightforward test methods concise; do not add boilerplate sections.
- Include only sections that add useful information. Describe behavior, side effects, constraints, units, and meaningful exceptions; do not repeat type annotations or defaults from the signature unless needed to clarify behavior.
- Keep documented names and behavior accurate to the implementation. Do not invent exceptions, guarantees, or examples.
- Use American English spelling (e.g., `color`, `behavior`) and consistent punctuation.

## Python Type Hints

- Annotate function parameters and return values when their contracts can be verified; keep existing annotations accurate when changing behavior.
- Use Python 3.13 syntax (the project requires `>=3.13,<3.14`): built-in generics such as `list[int]` and `X | None` for nullable values.
- Reflect accepted inputs and actual return values; avoid guessing, unnecessary `Any`, casts, or suppressions.
- No type checker is configured. After changing annotations, check relevant callers by inspection.

## Commit Messages

- Format every suggested commit message as `<type>: <short summary>`.
- Use a lowercase type from: `feat`, `fix`, `format`, `ci`, `docs`, `test`, `refactor`, `perf`, `build`, `chore`, `misc`.
- Choose `feat` for new functionality, `fix` for bug fixes, `format` for formatting-only changes, and `ci` for CI/workflow changes. Use `misc` only when no more specific type applies.
- Write a concise but descriptive summary in the imperative mood (e.g., "Add feature", not "Added feature").
- Put a blank line after the summary, followed by one or more flat hyphen bullets describing the changes.

## API Compatibility

- Treat the checked-in repository as the complete usage surface.
- Do not preserve old signatures or add compatibility shims for hypothetical external callers; update in-repository call sites and tests when simplifying APIs.
- Prioritize backward compatibility only when the user explicitly requests it.
