from pprint import pprint
from typing import Any, Optional, TypeVar

TState = TypeVar("TState")


class BaseTextBuilder:
    def __init__(self, state: TState = None):  # TODO: make non-optional
        self.state = state
        self.parts = []

    def raw(self, text: str, end=""):
        return self._append_with_end(text, end)

    def spc(self):
        self.parts.append(" ")
        return self

    def br(self):
        self.parts.append("\n")
        return self

    def para(self):
        self.parts.append("\n\n")
        return self

    def _append(self, text: str):
        self.parts.append(text)
        return self

    def _append_with_end(self, text: str, end: Optional[str]):
        self.parts.append(self._apply_end(text, end))
        return self

    @staticmethod
    def _apply_end(text: str, end: Optional[str]) -> str:
        if text is None:
            raise ValueError("Trying to append None value.")

        text = str(text)

        if text is None:
            raise ValueError(f"Cannot append '{text}' to message.")
        if end in ["", None]:
            return text
        else:
            return text + str(end)

    def render(self) -> str:
        result = "".join(self.parts)
        if not result or result.isspace():
            return "\xad"  # zero-width char
        return result
