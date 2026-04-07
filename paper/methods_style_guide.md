# Methods Writing Style Guide

Conventions for writing the methods and results sections of the belief sensitivity paper.

## Tense

- **Present tense throughout.** Describe the pipeline, analyses, and results as ongoing facts, not past events.
  - Yes: "Cross-model DAGs are significantly more similar..."
  - No: "Cross-model DAGs were significantly more similar..."
- **Exception**: Subjunctive mood is fine ("as if it were the model's own reasoning").
- **Exception**: Text inside quoted prompts keeps its original tense.

## Reporting Results

- **Lead with the result**, not the method that produced it. State findings directly.
  - Yes: "Zero DAG nodes are derived from the spurious background (0/116 contamination rate)."
  - No: "The judge found zero DAG nodes derived from the spurious background."
- **Include effect sizes and test statistics inline**: metric name, value, CI or p-value in parentheses.
- **Use standard statistical notation**: Spearman $\rho$, $\beta$, $p < .001$, nGED, MAE.
- **Round consistently**: correlations to 3 decimal places, p-values to 3 or use $< .001$, probabilities to 2--3.

## Terminology

Use these terms consistently. The left column is correct; the right column is deprecated.

| Use | Do not use |
|-----|------------|
| outcome mediation | path relevance |
| edge permutation condition | scrambled DAG |
| Structural Challenge (probe category) | Spurious |
| betweenness centrality | node importance (generic) |
| absolute log-odds shift, $|\Delta\text{logit}|$ | raw shift, probability shift |
| probe direction (negate/strengthen) | probe valence |
| irrelevant (probe type) | control probe (ambiguous) |
| edge_structural | edge_fabricate, edge_spurious |
| causal DAG / causal network | causal graph (acceptable but less precise) |
| factor node | causal factor (when referring to the graph element) |
| probed forecast | updated forecast |
| Stage 1 / Stage 2 / Stage 3 / Stage 4 | step 1, phase 1 (in paper context) |

## Model Names

Use these short forms in running text:

| Full name | Short form |
|-----------|------------|
| Llama 3.1 8B Instruct | Llama 8B |
| Llama 3.3 70B Instruct | Llama 70B |
| DeepSeek V3 | DeepSeek V3 |
| Qwen3 235B | Qwen3 235B |
| Qwen3 32B | Qwen3 32B |
| Gemini 2.5 Flash Lite | Gemini Flash Lite |
| GPT-OSS 120B | GPT-OSS |

First mention in a section should include parameter count. Subsequent mentions use the short form.

## Structure

- **Methods paragraphs** describe what we do (procedure), then why (motivation/rationale).
- **Results paragraphs** lead with the finding, then provide supporting statistics, then interpret.
- **Do not mix methods and results** within the same paragraph unless it's a self-contained robustness check where procedure + result fit naturally together (e.g., the spurious context or test-retest subsections).

## Prompt Descriptions

- When describing a prompt, state its purpose and key instructions in running text.
- Full prompt text goes in the appendix, referenced as "Appendix~\ref{app:...}".
- For robustness analyses that use specific prompts (e.g., spurious context generation, judge evaluation), include the prompt text in a `\begin{quote}` block in the relevant appendix subsection.

## Formatting

- **LaTeX commands**: Use `\textbf{}` for key terms on first definition, `\texttt{}` for probe type names and code identifiers.
- **Ranges**: Use en-dash ($6$--$10$, not $6$-$10$).
- **Approximate counts**: Use ${\sim}$ (e.g., ${\sim}$21 probes).
- **Variable references**: Use math mode for variables ($p_0$, $\beta_1$, $G = (V, E)$).
- **Cross-references**: Always use `\S\ref{}` for sections, `Table~\ref{}`, `Figure~\ref{}`, `Appendix~\ref{}`.

## What Not to Include

- Implementation details: no batch sizes, retry logic, rate limiting, API endpoints.
- Software versions unless methodologically relevant (R package versions for LME are relevant; Python version is not).
- Exact token counts or cost figures.
- Temperature and max_tokens are mentioned once; do not repeat per-analysis.
