from document_assistant.types import Passage

GROUNDED_INSTRUCTION = (
    "Answer the Question using only the numbered Passages below. "
    "If they do not contain the answer, say so. Do not add outside facts. "
    "Cite the Passages you used with their numbers in square brackets, like [1] or [2]. "
    "Be concise."
)


def _label(index: int, passage: Passage) -> str:
    where = passage.document
    if passage.page is not None:
        where += f", page {passage.page}"
    return f"[{index}] ({where})\n{passage.text}"


class PassageAnswerer:
    def answer(self, question: str, passages: tuple[Passage, ...]) -> str:
        del question
        return passages[0].text


class OpenAIAnswerer:
    def __init__(self, chat) -> None:
        self._chat = chat

    def answer(self, question: str, passages: tuple[Passage, ...]) -> str:
        passage_text = "\n\n".join(
            _label(index, passage) for index, passage in enumerate(passages, start=1)
        )
        messages = [
            {"role": "system", "content": GROUNDED_INSTRUCTION},
            {
                "role": "user",
                "content": f"Question: {question}\n\nPassages:\n{passage_text}",
            },
        ]
        return self._chat.complete(messages)


class LangChainChat:
    def __init__(self, model) -> None:
        self._model = model

    def complete(self, messages: list[dict[str, str]]) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        converted: list = []
        for message in messages:
            if message["role"] == "system":
                converted.append(SystemMessage(content=message["content"]))
            else:
                converted.append(HumanMessage(content=message["content"]))
        result = self._model.invoke(converted)
        return str(result.content)
