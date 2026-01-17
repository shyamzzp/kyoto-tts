"""
Demo: keep LLM chat payload under provider context-window char limit.

Run:
  uv run python examples/llm_budget_demo.py
or
  python examples/llm_budget_demo.py
"""
from __future__ import annotations

from pocket_tts.utils.context_budget import (
    BudgetConfig,
    OCA_GPT5_CHAR_LIMIT,
    budget_messages,
    messages_size,
)


def make_big_history() -> list[dict[str, str]]:
    # Simulate a long conversation with a very large last user message
    system = {
        "role": "system",
        "content": (
            "You are a helpful assistant. Prioritize accuracy and brevity. "
            "Follow the user's instructions and refuse unsafe requests."
        ),
    }
    user_small = {"role": "user", "content": "Summarize the following text."}
    assistant_small = {
        "role": "assistant",
        "content": "Sure, please provide the text.",
    }
    huge_text = "A" * 3_900_000  # 3.9M chars (simulates an oversized paste)
    user_huge = {"role": "user", "content": huge_text}
    return [system, user_small, assistant_small, user_huge]


def main() -> None:
    msgs = make_big_history()
    before = messages_size(msgs)
    print(f"Original chars: {before:,}")

    cfg = BudgetConfig(char_limit=OCA_GPT5_CHAR_LIMIT, safety_ratio=0.87)
    trimmed = budget_messages(msgs, cfg=cfg, keep_last_n_system=1)
    after = messages_size(trimmed)
    print(f"Trimmed chars:  {after:,} (<= {cfg.max_input():,} target)")

    # Show structure
    for i, m in enumerate(trimmed):
        body = m["content"]
        print(
            f"[{i}] role={m['role']!r}, content_len={len(body):,}, preview={body[:60]!r}"
        )

    # This is where you'd call your provider with `trimmed` instead of `msgs`.
    # e.g. client.chat.completions.create(messages=trimmed, model="oca/gpt5")


if __name__ == "__main__":
    main()