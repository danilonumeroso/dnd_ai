"""Dungeon Master agent."""

from __future__ import annotations

from typing import Any

from llm import LLMClient, LLMResponse
from models import GameState

from .tools import DM_TOOLS, format_tools_for_prompt


def dm_system_prompt(game_state: GameState) -> str:
    return f"""You are a Dungeon Master running a D&D 5e adventure.

CURRENT GAME STATE:
{game_state.summary()}

YOUR TOOLS (use these to drive the game — do NOT describe actions in plain text):
{format_tools_for_prompt(DM_TOOLS)}

GUIDELINES:
- Always open with a narration to set the scene before using other tools.
- During combat, narrate each enemy's turn, then use enemy_attack for each enemy that attacks.
- Keep difficulty fair.
- Alternate between exploration, dialogue, and combat to keep the game going.
- Describe scenes vividly but concisely (2-4 sentences at most).
"""


class DMAgent:
    """The Dungeon Master agent."""

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.messages: list[dict[str, Any]] = []

    async def take_turn(self, game_state: GameState) -> LLMResponse:
        """Ask the DM what happens next."""
        system = dm_system_prompt(game_state)

        if game_state.narrative_log:
            recent = "\n".join(game_state.narrative_log[-5:])
            user_msg = f"Here's what happened recently:\n{recent}\n\nContinue the adventure."
        else:
            user_msg = "Begin the adventure."

        self.messages.append({"role": "user", "content": user_msg})

        response = await self.llm.generate(
            messages=self.messages,
            system=system,
            tools=DM_TOOLS,
        )

        self.messages.append({"role": "assistant", "content": response.text})

        return response
