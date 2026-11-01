"""Unit tests for the eval harness scorers, plus an offline smoke run of the harness."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.scoring import (  # noqa: E402
    is_refusal,
    markers_valid,
    matches,
    missing_facts,
    percentile,
    retrieval_scores,
    score_case,
    summarize,
)

REFUSAL = "The documents do not contain an answer to that question."


def test_short_patterns_match_whole_words_only():
    assert matches("No, contractors are not eligible.", "no")
    assert not matches("A doctor's note is required.", "no")


def test_numbers_match_with_or_without_thousands_separator():
    assert matches("The budget is $1,500 per year.", "$1500")
    assert matches("The budget is $1500 per year.", "1,500")


def test_regex_patterns():
    assert matches("Use it by 31 March.", r"re:(march 31|31 march)")


def test_each_fact_group_needs_one_spelling():
    groups = [["20 days", "twenty"], ["march 31"]]
    assert missing_facts("You get twenty days; use them by March 31.", groups) == []
    assert missing_facts("You get 20 days.", groups) == [["march 31"]]


def test_refusal_detection():
    assert is_refusal(REFUSAL, REFUSAL)
    assert is_refusal("The documents don't mention a dress code.", REFUSAL)
    assert not is_refusal("Contractors are not eligible for paid vacation.", REFUSAL)


def test_retrieval_scores_rank_and_recall():
    scores = retrieval_scores(["a.md", "b.md", "c.md"], ["b.md", "z.md"])
    assert scores == {"hit": 1.0, "recall": 0.5, "rr": 0.5}
    assert retrieval_scores(["a.md"], ["b.md"])["hit"] == 0.0


def test_citation_markers_must_point_at_a_retrieved_passage():
    assert markers_valid("Twenty days [1].", 2) is True
    assert markers_valid("Twenty days [3].", 2) is False
    assert markers_valid("Twenty days.", 2) is None


def test_percentile_interpolates():
    assert percentile([10, 20, 30, 40], 50) == 25
    assert percentile([], 50) is None


def test_answerable_case_passes_only_with_right_document_and_facts():
    case = {"id": "x", "expected_documents": ["leave.md"], "expected_facts": [["20 days"]]}
    good = score_case(case, "You get 20 days [1].", [{"document": "leave.md", "page": None}], REFUSAL)
    wrong_doc = score_case(case, "You get 20 days.", [{"document": "other.md", "page": None}], REFUSAL)
    refused = score_case(case, REFUSAL, [], REFUSAL)
    assert good["passed"] and good["markers_valid"]
    assert not wrong_doc["passed"]
    assert not refused["passed"] and refused["refused"]


def test_unanswerable_case_passes_only_when_refused():
    case = {"id": "y", "answerable": False}
    assert score_case(case, REFUSAL, [], REFUSAL)["passed"]
    assert not score_case(case, "Interns get 20 days.", [{"document": "leave.md"}], REFUSAL)["passed"]


def test_summary_separates_answerable_and_unanswerable_rates():
    results = [
        {"category": "factual", "answerable": True, "passed": True, "hit": 1.0, "recall": 1.0, "rr": 1.0,
         "correct": True, "refused": False, "markers_valid": None, "latency_ms": 10},
        {"category": "factual", "answerable": True, "passed": False, "hit": 0.0, "recall": 0.0, "rr": 0.0,
         "correct": False, "refused": True, "markers_valid": None, "latency_ms": 30},
        {"category": "unanswerable", "answerable": False, "passed": True, "refused": True,
         "markers_valid": None, "latency_ms": 20},
    ]
    summary = summarize(results)
    assert summary["answer_accuracy"] == 0.5
    assert summary["false_refusal_rate"] == 0.5
    assert summary["refusal_accuracy"] == 1.0
    assert summary["latency_p50_ms"] == 20
    assert summary["by_category"]["factual"] == {"cases": 2, "pass_rate": 0.5}


def test_offline_harness_runs_end_to_end_and_enforces_thresholds(tmp_path):
    command = [sys.executable, str(ROOT / "evals" / "run_eval.py"), "--offline", "--no-save"]
    ok = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
    assert ok.returncode == 0, ok.stderr
    assert "Retrieval hit@k" in ok.stdout
    gated = subprocess.run(command + ["--fail-under", "pass_rate=1.01"], capture_output=True, text=True, cwd=ROOT)
    assert gated.returncode == 1
    assert "Below threshold" in gated.stdout


def test_golden_set_is_well_formed():
    corpus = {p.name for p in (ROOT / "evals" / "corpus").iterdir()}
    ids = set()
    for line in (ROOT / "evals" / "golden.jsonl").read_text().splitlines():
        case = json.loads(line)
        assert case["id"] not in ids
        ids.add(case["id"])
        if case.get("answerable", True):
            assert case["expected_facts"], case["id"]
            assert set(case["expected_documents"]) <= corpus, case["id"]
