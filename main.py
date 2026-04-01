"""Entry point — run the game."""

from __future__ import annotations

import argparse
import asyncio

from display import Display
from game import Game
from llm import AnthropicClient, GeminiClient, OpenRouterClient


async def run_game(provider: str) -> None:
    display = Display()
    display.show_title()

    if provider == "gemini":
        llm = GeminiClient()
    elif provider == "openrouter":
        llm = OpenRouterClient()
    else:
        llm = AnthropicClient()

    game = Game(llm=llm, display=display)
    game.setup()

    await game.run(max_turns=10)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI agents playing D&D")
    parser.add_argument(
        "--provider", choices=["anthropic", "gemini", "openrouter"], default="gemini",
        help="LLM provider to use (default: gemini)",
    )
    args = parser.parse_args()
    asyncio.run(run_game(args.provider))


if __name__ == "__main__":
    main()
