"""Eval harness for the Enterprise Document Assistant.

Ingests a fixed Corpus (evals/corpus), asks every Question in evals/golden.jsonl, and scores
retrieval, answer accuracy, refusals, citations, latency and cost. Optionally grades
faithfulness with an LLM judge.

    python evals/run_eval.py                      # uses OPENAI_API_KEY from .env if set
    python evals/run_eval.py --offline            # local hash embedder + passage answerer
    python evals/run_eval.py --judge              # add LLM-judged faithfulness
    python evals/run_eval.py --chunk-size 500 --top-k 6 --label small-chunks
    python evals/run_eval.py --compare evals/results/<earlier>.json
    python evals/run_eval.py --fail-under answer_accuracy=0.8 --fail-under refusal_accuracy=1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVALS = Path(__file__).resolve().parent
ROOT = EVALS.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

import document_assistant.assistant as assistant_module  # noqa: E402
from document_assistant.answerers import OpenAIAnswerer  # noqa: E402
from document_assistant.assistant import REFUSAL, Assistant  # noqa: E402
from document_assistant.factory import build_assistant  # noqa: E402
from evals.scoring import score_case, summarize  # noqa: E402

# USD per million tokens. Check current OpenAI pricing; these are estimates for reporting.
CHAT_PRICES = {"gpt-4o-mini": (0.15, 0.60), "gpt-4o": (2.50, 10.00), "gpt-4.1-mini": (0.40, 1.60)}
EMBEDDING_PRICE = 0.02  # text-embedding-3-small
HEADLINE = [
    ("pass_rate", "Pass rate"),
    ("retrieval_hit_rate", "Retrieval hit@k"),
    ("retrieval_recall", "Retrieval recall@k"),
    ("mrr", "MRR"),
    ("page_hit_rate", "PDF page hit"),
    ("answer_accuracy", "Answer accuracy"),
    ("false_refusal_rate", "False refusals"),
    ("refusal_accuracy", "Refusal accuracy"),
    ("citation_marker_validity", "Citation markers valid"),
    ("faithfulness", "Faithfulness (judge)"),
    ("latency_p50_ms", "Latency p50 (ms)"),
    ("latency_p95_ms", "Latency p95 (ms)"),
    ("cost_per_question_usd", "Cost / question ($)"),
]
LOWER_IS_BETTER = {"false_refusal_rate", "latency_p50_ms", "latency_p95_ms", "cost_per_question_usd"}


class MeteredModel:
    """Wraps a LangChain chat model to record token usage the Assistant otherwise discards."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.input_tokens = 0
        self.output_tokens = 0

    def invoke(self, messages: Any) -> Any:
        result = self.inner.invoke(messages)
        usage = getattr(result, "usage_metadata", None) or {}
        self.input_tokens += int(usage.get("input_tokens", 0))
        self.output_tokens += int(usage.get("output_tokens", 0))
        return result


class MeteredEmbedder:
    """Counts characters embedded; tokens are estimated at 4 characters per token."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.characters = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.characters += sum(len(text) for text in texts)
        return self.inner.embed(texts)


def load_cases(path: Path, only: set[str] | None) -> list[dict[str, Any]]:
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if only:
        cases = [case for case in cases if case["id"] in only or case["category"] in only]
    return cases


def build(args: argparse.Namespace) -> tuple[Assistant, MeteredModel | None, MeteredEmbedder, str]:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    env = dict(os.environ)
    if args.offline:
        env.pop("OPENAI_API_KEY", None)
    if args.store != "pinecone":
        # Evals use a fresh in-memory Corpus so earlier uploads in Pinecone can't leak in.
        env.pop("PINECONE_API_KEY", None)
        env.pop("PINECONE_INDEX", None)
    base = build_assistant(env)
    meter = None
    if isinstance(base.answerer, OpenAIAnswerer):
        chat = base.answerer._chat  # harness-only access to record token usage
        meter = MeteredModel(chat._model)
        chat._model = meter
    embedder = MeteredEmbedder(base.embedder)
    splitter = RecursiveCharacterTextSplitter(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    assistant_module.TOP_K = args.top_k
    assistant_module.MIN_SIMILARITY = args.min_similarity
    mode = "openai" if meter else "offline"
    return Assistant(embedder=embedder, store=base.store, answerer=base.answerer, splitter=splitter), meter, embedder, mode


def fmt(value: Any, key: str = "") -> str:
    if value is None:
        return "—"
    if key.endswith("_ms"):
        return f"{value:,.0f}"
    if key.endswith("_usd"):
        return f"{value:.5f}"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def print_report(summary: dict[str, Any], results: list[dict[str, Any]], previous: dict[str, Any] | None) -> None:
    print()
    header = f"{'Metric':<26}{'Value':>12}" + (f"{'Previous':>12}{'Change':>10}" if previous else "")
    print(header)
    print("-" * len(header))
    for key, label in HEADLINE:
        line = f"{label:<26}{fmt(summary.get(key), key):>12}"
        if previous:
            old = previous.get(key)
            new = summary.get(key)
            change = ""
            if isinstance(old, (int, float)) and isinstance(new, (int, float)):
                delta = new - old
                better = delta < 0 if key in LOWER_IS_BETTER else delta > 0
                change = ("+" if delta >= 0 else "") + fmt(delta, key) + (" ✓" if better and delta else "")
            line += f"{fmt(old, key):>12}{change:>10}"
        print(line)
    print("\nBy category")
    for name, row in summary["by_category"].items():
        print(f"  {name:<14}{row['pass_rate']:.0%} of {row['cases']}")
    failures = [r for r in results if not r["passed"]]
    if failures:
        print(f"\nFailed cases ({len(failures)})")
        for r in failures:
            why = []
            if r.get("answerable", True):
                if not r["hit"]:
                    why.append(f"retrieved {r['retrieved_documents']} not {r['expected_documents']}")
                if r["refused"]:
                    why.append("refused an answerable question")
                elif r["missing_facts"]:
                    why.append(f"missing {[g[0] for g in r['missing_facts']]}")
            else:
                why.append("answered a question the Documents can't answer")
            print(f"  {r['id']:<10} {'; '.join(why)}")


def write_markdown(path: Path, run: dict[str, Any]) -> None:
    s = run["summary"]
    lines = [
        f"# Document Assistant eval — {run['label'] or run['mode']}",
        "",
        f"Run at {run['started_at']} · mode `{run['mode']}` · {s['cases']} cases · config `{json.dumps(run['config'])}`",
        "",
        "| Metric | Value |",
        "| --- | --- |",
    ]
    lines += [f"| {label} | {fmt(s.get(key), key)} |" for key, label in HEADLINE]
    lines += ["", "| Category | Pass rate | Cases |", "| --- | --- | --- |"]
    lines += [f"| {k} | {v['pass_rate']:.0%} | {v['cases']} |" for k, v in s["by_category"].items()]
    lines += ["", "| Case | Passed | Retrieved | Answer |", "| --- | --- | --- | --- |"]
    for r in run["results"]:
        answer = r["answer"].replace("\n", " ").replace("|", "\\|")[:140]
        lines.append(f"| {r['id']} | {'✅' if r['passed'] else '❌'} | {', '.join(r['retrieved_documents'])} | {answer} |")
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="ignore OPENAI_API_KEY")
    parser.add_argument("--store", choices=["memory", "pinecone"], default="memory")
    parser.add_argument("--judge", action="store_true", help="grade faithfulness with an LLM judge")
    parser.add_argument("--judge-model", default="gpt-4o-mini")
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--chunk-overlap", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=assistant_module.TOP_K)
    parser.add_argument("--min-similarity", type=float, default=assistant_module.MIN_SIMILARITY)
    parser.add_argument("--cases", help="comma-separated case ids or categories")
    parser.add_argument("--golden", default=str(EVALS / "golden.jsonl"))
    parser.add_argument("--corpus", default=str(EVALS / "corpus"))
    parser.add_argument("--label", default="", help="name for this run, e.g. small-chunks")
    parser.add_argument("--compare", help="earlier results JSON to compare against")
    parser.add_argument("--fail-under", action="append", default=[], metavar="METRIC=VALUE")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()

    assistant, meter, embedder, mode = build(args)
    cases = load_cases(Path(args.golden), set(args.cases.split(",")) if args.cases else None)
    judge = None
    if args.judge:
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            parser.error("--judge needs OPENAI_API_KEY")
        from evals.judge import FaithfulnessJudge

        judge = FaithfulnessJudge(key, args.judge_model)

    for document in sorted(Path(args.corpus).iterdir()):
        if document.is_file() and not document.name.startswith("."):
            assistant.add_document(document.name, document.read_bytes())
    ingest_characters = embedder.characters
    print(f"Mode: {mode} · {len(assistant.documents())} Documents · {len(cases)} cases")

    results = []
    for case in cases:
        started = time.perf_counter()
        grounded = assistant.ask(case["question"])
        latency_ms = (time.perf_counter() - started) * 1000
        citations = [
            {"document": c.document, "page": c.page, "excerpt": c.excerpt, "score": c.score}
            for c in grounded.citations
        ]
        scored = score_case(case, grounded.answer, citations, REFUSAL)
        retrieved_documents: list[str] = []
        for c in citations:
            if c["document"] not in retrieved_documents:
                retrieved_documents.append(c["document"])
        row = {
            "id": case["id"],
            "category": case["category"],
            "answerable": case.get("answerable", True),
            "question": case["question"],
            "expected_documents": case.get("expected_documents", []),
            "retrieved_documents": retrieved_documents,
            "answer": grounded.answer,
            "citations": [{k: v for k, v in c.items() if k != "excerpt"} for c in citations],
            "latency_ms": latency_ms,
            "faithfulness": None,
            **scored,
        }
        if judge and citations and not scored["refused"]:
            verdict = judge.judge(case["question"], grounded.answer, citations)
            row["faithfulness"] = verdict["score"]
            row["judge_claims"] = verdict["claims"]
        results.append(row)
        print(f"  {'PASS' if row['passed'] else 'FAIL'}  {case['id']}")

    summary = summarize(results)
    chat_cost = 0.0
    if meter:
        prompt_price, completion_price = CHAT_PRICES.get("gpt-4o-mini", (0.0, 0.0))
        chat_cost = (meter.input_tokens * prompt_price + meter.output_tokens * completion_price) / 1e6
    query_embedding_cost = (embedder.characters - ingest_characters) / 4 * EMBEDDING_PRICE / 1e6 if mode == "openai" else 0.0
    summary["cost_per_question_usd"] = (chat_cost + query_embedding_cost) / len(cases) if cases else None
    summary["tokens"] = {
        "answer_input": meter.input_tokens if meter else 0,
        "answer_output": meter.output_tokens if meter else 0,
        "judge_input": judge.input_tokens if judge else 0,
        "judge_output": judge.output_tokens if judge else 0,
        "embedded_characters_ingest": ingest_characters,
    }

    previous = None
    if args.compare:
        previous = json.loads(Path(args.compare).read_text())["summary"]
    print_report(summary, results, previous)

    run = {
        "label": args.label,
        "mode": mode,
        "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "config": {
            "chunk_size": args.chunk_size,
            "chunk_overlap": args.chunk_overlap,
            "top_k": args.top_k,
            "min_similarity": args.min_similarity,
            "store": args.store,
            "judge_model": args.judge_model if judge else None,
        },
        "summary": summary,
        "results": results,
    }
    if not args.no_save:
        out = EVALS / "results"
        out.mkdir(exist_ok=True)
        stem = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + f"-{mode}" + (f"-{args.label}" if args.label else "")
        (out / f"{stem}.json").write_text(json.dumps(run, indent=2))
        write_markdown(out / "latest.md", run)
        print(f"\nSaved evals/results/{stem}.json and evals/results/latest.md")

    failed = []
    for rule in args.fail_under:
        metric, _, threshold = rule.partition("=")
        value = summary.get(metric)
        if value is None or value < float(threshold):
            failed.append(f"{metric}={fmt(value)} < {threshold}")
    if failed:
        print("\nBelow threshold: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
