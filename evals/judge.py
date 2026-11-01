"""LLM-as-judge for faithfulness: is every claim in the answer supported by the Passages?

Only used with --judge and an OPENAI_API_KEY. The judge runs at temperature 0 and
returns structured JSON, so the score is the share of claims it marks as supported.
"""

from __future__ import annotations

import json
from typing import Any

JUDGE_SYSTEM = (
    "You grade answers from a document question-answering system for faithfulness. "
    "Split the ANSWER into short, atomic factual claims (ignore citation markers like [1] "
    "and ignore statements that the documents do not contain something). "
    "For each claim decide whether the PASSAGES fully support it. A claim is unsupported if it "
    "adds a detail, number, condition, or conclusion that the PASSAGES do not state. "
    'Respond with JSON only: {"claims": [{"claim": "...", "supported": true, "reason": "..."}]}'
)


class FaithfulnessJudge:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        from langchain_openai import ChatOpenAI

        self.model_name = model
        self._model = ChatOpenAI(model=model, api_key=api_key, temperature=0).bind(  # type: ignore[arg-type]
            response_format={"type": "json_object"}
        )
        self.input_tokens = 0
        self.output_tokens = 0

    def judge(self, question: str, answer: str, citations: list[dict[str, Any]]) -> dict[str, Any]:
        from langchain_core.messages import HumanMessage, SystemMessage

        passages = "\n\n".join(
            f"[{i}] ({c['document']}, page {c.get('page')})\n{c['excerpt']}"
            for i, c in enumerate(citations, start=1)
        )
        result = self._model.invoke(
            [
                SystemMessage(content=JUDGE_SYSTEM),
                HumanMessage(content=f"QUESTION:\n{question}\n\nANSWER:\n{answer}\n\nPASSAGES:\n{passages}"),
            ]
        )
        usage = getattr(result, "usage_metadata", None) or {}
        self.input_tokens += int(usage.get("input_tokens", 0))
        self.output_tokens += int(usage.get("output_tokens", 0))
        try:
            claims = json.loads(str(result.content)).get("claims", [])
        except json.JSONDecodeError:
            return {"score": None, "claims": [], "error": "judge returned invalid JSON"}
        if not claims:
            return {"score": None, "claims": []}
        supported = sum(1 for claim in claims if claim.get("supported") is True)
        return {"score": supported / len(claims), "claims": claims}
