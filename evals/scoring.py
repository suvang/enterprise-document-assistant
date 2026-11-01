"""Pure scoring functions for the Document Assistant evals.

Nothing here calls a model or touches the network, so every score is reproducible
and covered by unit tests (tests/test_eval_scoring.py).
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

# Phrases that mean "the Documents don't answer this". The Assistant's own refusal
# text is checked separately; these catch a model that words its refusal differently.
REFUSAL_PATTERNS = (
    "do not contain",
    "does not contain",
    "don't contain",
    "doesn't contain",
    "no information",
    "not mentioned",
    "not specified",
    "not provided",
    "does not say",
    "doesn't say",
    "does not mention",
    "do not mention",
    "don't mention",
    "doesn't mention",
    "cannot find",
    "can't find",
    "unable to find",
    "no answer",
)

_MARKER = re.compile(r"\[(\d+)\]")


def normalize(text: str) -> str:
    """Lowercase, unify quotes, drop thousands separators, collapse whitespace."""
    text = text.lower().replace("’", "'").replace("‘", "'")
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def matches(text: str, pattern: str) -> bool:
    """True if ``pattern`` occurs in ``text``.

    ``re:`` prefixes a regular expression. A plain pattern that starts and ends with a
    letter or digit must match whole words, so "no" does not match "note".
    """
    if pattern.startswith("re:"):
        return re.search(pattern[3:], text, re.IGNORECASE) is not None
    needle = normalize(pattern)
    haystack = normalize(text)
    if not needle:
        return False
    if needle[0].isalnum() and needle[-1].isalnum():
        return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack) is not None
    return needle in haystack


def missing_facts(answer: str, fact_groups: list[list[str]]) -> list[list[str]]:
    """Each group lists acceptable spellings of one fact. Returns the groups not found."""
    return [group for group in fact_groups if not any(matches(answer, p) for p in group)]


def is_refusal(answer: str, refusal_text: str) -> bool:
    if normalize(answer) == normalize(refusal_text):
        return True
    lowered = normalize(answer)
    return any(pattern in lowered for pattern in REFUSAL_PATTERNS)


def retrieval_scores(retrieved: list[str], expected: list[str]) -> dict[str, float]:
    """Document-level retrieval quality for one Question.

    hit:    1 if any expected Document was retrieved.
    recall: share of expected Documents that were retrieved.
    rr:     reciprocal rank of the first expected Document (0 if none).
    """
    if not expected:
        return {"hit": 0.0, "recall": 0.0, "rr": 0.0}
    found = set(retrieved) & set(expected)
    rr = 0.0
    for rank, document in enumerate(retrieved, start=1):
        if document in expected:
            rr = 1.0 / rank
            break
    return {
        "hit": 1.0 if found else 0.0,
        "recall": len(found) / len(set(expected)),
        "rr": rr,
    }


def page_hit(citations: list[dict[str, Any]], document: str, page: int) -> bool:
    return any(c["document"] == document and c.get("page") == page for c in citations)


def citation_markers(answer: str) -> list[int]:
    return [int(n) for n in _MARKER.findall(answer)]


def markers_valid(answer: str, citation_count: int) -> bool | None:
    """None when the answer has no [n] markers (e.g. the offline answerer)."""
    markers = citation_markers(answer)
    if not markers:
        return None
    return all(1 <= n <= citation_count for n in markers)


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p / 100
    low, high = math.floor(rank), math.ceil(rank)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def score_case(case: dict[str, Any], answer: str, citations: list[dict[str, Any]], refusal_text: str) -> dict[str, Any]:
    """Score one Question. ``citations`` are the Assistant's retrieved Passages, best first."""
    answerable = case.get("answerable", True)
    refused = is_refusal(answer, refusal_text)
    retrieved_docs: list[str] = []
    for citation in citations:
        if citation["document"] not in retrieved_docs:
            retrieved_docs.append(citation["document"])
    result: dict[str, Any] = {
        "refused": refused,
        "markers_valid": markers_valid(answer, len(citations)),
    }
    if answerable:
        result.update(retrieval_scores(retrieved_docs, case.get("expected_documents", [])))
        missing = missing_facts(answer, case.get("expected_facts", []))
        result["missing_facts"] = missing
        result["correct"] = not missing and not refused
        if "expected_page" in case:
            result["page_hit"] = page_hit(citations, case["expected_documents"][0], case["expected_page"])
        result["passed"] = bool(result["correct"] and result["hit"])
    else:
        result["passed"] = refused
    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [r for r in results if r.get("answerable", True)]
    unanswerable = [r for r in results if not r.get("answerable", True)]
    with_page = [r for r in answerable if "page_hit" in r]
    with_markers = [r for r in results if r.get("markers_valid") is not None]
    judged = [r for r in results if r.get("faithfulness") is not None]
    latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]

    by_category: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        by_category[r["category"]].append(bool(r["passed"]))

    return {
        "cases": len(results),
        "pass_rate": _mean([1.0 if r["passed"] else 0.0 for r in results]),
        "retrieval_hit_rate": _mean([r["hit"] for r in answerable]),
        "retrieval_recall": _mean([r["recall"] for r in answerable]),
        "mrr": _mean([r["rr"] for r in answerable]),
        "page_hit_rate": _mean([1.0 if r["page_hit"] else 0.0 for r in with_page]),
        "answer_accuracy": _mean([1.0 if r["correct"] else 0.0 for r in answerable]),
        "false_refusal_rate": _mean([1.0 if r["refused"] else 0.0 for r in answerable]),
        "refusal_accuracy": _mean([1.0 if r["refused"] else 0.0 for r in unanswerable]),
        "citation_marker_validity": _mean([1.0 if r["markers_valid"] else 0.0 for r in with_markers]),
        "faithfulness": _mean([r["faithfulness"] for r in judged]),
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "by_category": {
            name: {"cases": len(passes), "pass_rate": sum(passes) / len(passes)}
            for name, passes in sorted(by_category.items())
        },
    }
