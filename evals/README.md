# Evals

An eval harness for the Document Assistant: a fixed Corpus, a labeled set of Questions, and a
script that scores every answer, so a change to chunking, retrieval, the prompt or the model
shows up as a number instead of a hunch.

## Run

From the project root, with the project's virtualenv active:

```bash
python evals/run_eval.py --offline            # no API calls: hash embedder + passage answerer
python evals/run_eval.py                      # OpenAI embeddings + gpt-4o-mini (uses .env)
python evals/run_eval.py --judge              # also grade faithfulness with an LLM judge
```

The harness always uses a fresh in-memory Corpus, even when Pinecone is configured, so earlier
uploads can't leak into the results (`--store pinecone` overrides this).

Each run prints a scorecard, lists failed cases with the reason, and saves
`evals/results/<timestamp>-<mode>[-label].json` plus a readable `evals/results/latest.md`.

## Experiments

Retrieval settings can be changed per run, and any two runs can be compared:

```bash
python evals/run_eval.py --label baseline
python evals/run_eval.py --chunk-size 500 --chunk-overlap 100 --label small-chunks \
    --compare evals/results/<baseline>.json
```

Options: `--chunk-size`, `--chunk-overlap`, `--top-k`, `--min-similarity`, `--cases <ids or categories>`.

Use it as a regression gate (for example in CI). The command exits with status 1 if a metric falls below its threshold:

```bash
python evals/run_eval.py --fail-under answer_accuracy=0.85 --fail-under refusal_accuracy=1
```

## What's in it

- `corpus/`: seven Documents from a fictional company (Northwind Labs): leave, expense, security,
  remote work, IT onboarding, a contractor guide, and a two-page benefits PDF. The facts are
  invented, so the model can't answer from memory, and some are deliberately close to each other
  (1 hour vs 24 hours to report an incident; employee vs contractor rules).
- `golden.jsonl`: 37 Questions in seven categories:

| Category | What it tests |
| --- | --- |
| factual | The answer is stated directly in one Document |
| paraphrase | The Question uses different words from the Document ("off sick four days in a row") |
| distractor | A similar but wrong Passage exists (contractor vs employee, 1 h vs 24 h) |
| pdf | Answer is in a PDF; checks the cited page number too |
| multi_doc | The answer needs Passages from two Documents |
| unanswerable | The Corpus doesn't answer it; the right behavior is to refuse |

Each case lists `expected_documents`, and `expected_facts` as groups of acceptable spellings
(`[["20 days", "twenty"]]`). Unanswerable cases have `"answerable": false`.

## Metrics

| Metric | Meaning |
| --- | --- |
| Pass rate | Share of cases that passed: the right Document retrieved and every fact present, or a correct refusal |
| Retrieval hit@k | An expected Document is among the top-k retrieved Passages |
| Retrieval recall@k | Share of expected Documents retrieved (matters for multi_doc) |
| MRR | Mean reciprocal rank of the first correct Document |
| PDF page hit | The citation points at the right PDF page |
| Answer accuracy | Every expected fact appears in the answer, and the answer isn't a refusal |
| False refusals | Answerable Questions the Assistant refused |
| Refusal accuracy | Unanswerable Questions the Assistant correctly refused |
| Citation markers valid | Every `[n]` in the answer points at a returned Citation |
| Faithfulness (judge) | Share of the answer's atomic claims an LLM judge finds supported by the cited Passages |
| Latency p50/p95, cost/question | Measured per Question; cost uses the price table in `run_eval.py` |

## Offline baseline

The offline mode is a lexical baseline (bag-of-words hashing, no model). Two runs on the same set:

| Metric | Default (chunk 1000, min sim 0.25) | Chunk 500, min sim 0.10 |
| --- | --- | --- |
| Pass rate | 0.541 | 0.676 |
| Retrieval hit@k | 0.625 | 0.906 |
| Answer accuracy | 0.500 | 0.750 |
| False refusals | 0.375 | 0.031 |
| Refusal accuracy | 0.800 | 0.200 |

Lowering the similarity threshold fixed most false refusals, but the Assistant then answered
4 of 5 unanswerable Questions. This trade-off is what the harness is for. Run the OpenAI mode
next and record its numbers here.

## Adding cases

Add a line to `golden.jsonl`, and a Document to `corpus/` if the case needs one. `tests/test_eval_scoring.py`
checks that ids are unique and every expected Document exists.
