"""
Utilities for enforcing model input character budgets (useful for providers with
strict context-window character limits like oca/gpt5).

Key ideas
- Always leave headroom below the advertised limit (providers may count hidden/system text).
- Prefer to keep the most recent messages; roll up older history into a summary.
- If a single message is too large, truncate its content rather than failing.

This module is model-agnostic and safe to import anywhere.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List, Mapping, MutableMapping, Sequence

# Default character limit for the user's provider in the report
OCA_GPT5_CHAR_LIMIT = 1_088_000


@dataclass
class BudgetConfig:
    char_limit: int = OCA_GPT5_CHAR_LIMIT
    safety_ratio: float = 0.87  # keep ~13% headroom for provider overhead
    # Extra fixed chars to budget for system/tool content that may be added later
    extra_overhead: int = 0
    # When the last message still exceeds the budget, try truncating it to fit
    truncate_last_if_needed: bool = True

    def max_input(self) -> int:
        return int(self.char_limit * self.safety_ratio) - max(self.extra_overhead, 0)


def message_size(msg: Mapping[str, str]) -> int:
    """Return approximate char count of a chat message (role + content).
    This is a heuristic; providers may count more (e.g., JSON), hence headroom.
    """
    return len(msg.get("role", "")) + len(msg.get("content", ""))


def messages_size(messages: Sequence[Mapping[str, str]]) -> int:
    return sum(message_size(m) for m in messages)


def budget_messages(
    messages: Sequence[Mapping[str, str]],
    cfg: BudgetConfig | None = None,
    keep_last_n_system: int = 1,
) -> List[MutableMapping[str, str]]:
    """Return a trimmed copy of messages that stays within cfg.max_input().

    Strategy:
    - Keep up to the last `keep_last_n_system` system messages (from anywhere in history).
    - Then include messages from the end backwards until the budget would be exceeded.
    - If even the final message doesn't fit, optionally truncate its content.
    """
    cfg = cfg or BudgetConfig()
    max_input = cfg.max_input()

    # Separate system and non-system to allow pinning important instructions
    system_msgs: List[MutableMapping[str, str]] = [
        dict(m) for m in messages if m.get("role") == "system"
    ]
    non_system: List[MutableMapping[str, str]] = [
        dict(m) for m in messages if m.get("role") != "system"
    ]

    pinned: List[MutableMapping[str, str]] = system_msgs[-keep_last_n_system:] if keep_last_n_system > 0 else []
    pinned_budget = messages_size(pinned)

    out: List[MutableMapping[str, str]] = []
    total = pinned_budget

    # Walk from the end of non-system messages backwards
    for idx in range(len(non_system) - 1, -1, -1):
        m = dict(non_system[idx])
        m_size = message_size(m)
        if total + m_size <= max_input:
            out.append(m)
            total += m_size
        else:
            # Can't add this full message; maybe we can include a truncated version
            if idx == len(non_system) - 1 and cfg.truncate_last_if_needed and m.get("content"):
                allowed = max(0, max_input - total - len(m.get("role", "")))
                if allowed > 0:
                    m["content"] = truncate_text(m["content"], allowed)
                    out.append(m)
                    total += message_size(m)
            break

    out.reverse()

    # Prepend pinned system messages (they count towards budget)
    final: List[MutableMapping[str, str]] = []
    # If pinned themselves don't fit, keep only the last one or an empty system
    for m in pinned[-keep_last_n_system:]:
        if messages_size(final) + message_size(m) <= max_input:
            final.append(m)
        else:
            # Try to truncate the last system if allowed
            if cfg.truncate_last_if_needed and m.get("content"):
                allowed = max(0, max_input - messages_size(final) - len(m.get("role", "")))
                if allowed > 0:
                    m = dict(m)
                    m["content"] = truncate_text(m["content"], allowed)
                    final.append(m)
            break

    final.extend(out)
    return final


def truncate_text(text: str, max_chars: int, placeholder: str = "…") -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    # Reserve space for placeholder if possible
    if max_chars >= len(placeholder) + 1:
        return text[: max_chars - len(placeholder)] + placeholder
    return text[:max_chars]


def rollup_history(
    messages: Sequence[Mapping[str, str]],
    summarize: Callable[[Sequence[Mapping[str, str]]], Mapping[str, str] | str],
    keep_last_n: int = 6,
) -> List[MutableMapping[str, str]]:
    """Summarize older turns into a compact memory message and keep the recent tail.

    The summarizer should return either a message dict or a content string.
    """
    if len(messages) <= keep_last_n:
        return [dict(m) for m in messages]

    head = messages[:-keep_last_n]
    tail = [dict(m) for m in messages[-keep_last_n:]]

    summary = summarize(head)
    if isinstance(summary, str):
        mem_msg: MutableMapping[str, str] = {
            "role": "system",
            "content": f"Conversation memory (summarized):\n{summary}",
        }
    else:
        mem_msg = dict(summary)
        mem_msg.setdefault("role", "system")
    return [mem_msg] + tail


def chunk_text(doc: str, chunk_size: int) -> Iterable[str]:
    """Yield doc in fixed-size character chunks."""
    for i in range(0, len(doc), max(1, chunk_size)):
        yield doc[i : i + chunk_size]


def budget_document(doc: str, cfg: BudgetConfig | None = None) -> str:
    """Ensure a single long string fits within budget; truncate if needed."""
    cfg = cfg or BudgetConfig()
    return truncate_text(doc, cfg.max_input())