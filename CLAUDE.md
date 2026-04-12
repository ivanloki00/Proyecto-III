## Approach
- Think before acting. Read existing files before writing code.
- Be concise in output but thorough in reasoning.
- No sycophantic openers ("Sure!", "Glad to help") or closing fluff.
- Prefer editing over rewriting whole files.
- Test your code before declaring done.
- User instructions always override this file.

## Data Analysis & Research
- **Lead with the finding.** Present conclusions first, then methodology.
- **Use tables/bullets** instead of long paragraphs for data.
- **Accuracy:** Never state a number without a source or derivation. If data is missing, say so.
- **Confidence:** If confidence is low, state it explicitly with a reason.
- **No Hallucinations:** Never fabricate data points, statistics, or citations.
- **Inferences:** Distinguish clearly between what the data shows and what is inferred.

## Python & Data Science Coding
- **Simplicity:** Prefer the simplest working solution. No over-engineering or premature abstractions.
- **Libraries:** Use `pandas`, `geopandas`, and `osmnx` efficiently. Prefer vectorized operations.
- **Paths:** Always use `pathlib.Path` for file system operations.
- **Logging:** Use the `logging` module for progress tracking instead of `print()`.
- **Environment:** Use the existing logic for `ROOT` discovery and directory creation.
- **Style:** Follow the existing pattern of clear section headers (e.g., `# CONFIG`, `# UTILIDADES`).

## Workflow Commands
- **Dependency Management:** Use `uv` or `pip` as required by the environment.
