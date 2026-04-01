"""Player character agent."""

from __future__ import annotations

from typing import Any

from llm import LLMClient, LLMResponse
from models import Character, GameState

from .tools import (
    format_tools_for_prompt,
    format_spells_for_prompt,
    get_player_tools,
    get_spell_list,
)


def player_system_prompt(character: Character, game_state: GameState) -> str:
    char_class = character.character_class.value
    tools = get_player_tools(char_class)
    spells = get_spell_list(char_class)

    spell_section = ""
    if spells:
        spell_section = f"""
YOUR SPELLS (use the cast_spell tool to cast these):
{format_spells_for_prompt(spells)}
"""

    return f"""You are {character.name}, a level {character.level} {char_class}.
Personality: {character.personality}

YOUR STATS:
HP: {character.hp}/{character.max_hp} | AC: {character.armor_class}
STR: {character.abilities.strength} DEX: {character.abilities.dexterity} CON: {character.abilities.constitution}
INT: {character.abilities.intelligence} WIS: {character.abilities.wisdom} CHA: {character.abilities.charisma}

CURRENT GAME STATE:
{game_state.summary()}

YOUR TOOLS:
{format_tools_for_prompt(tools)}
{spell_section}
Play in character. Always speak in first person. Use exactly one of your tools per turn to take actions.
"""


class PlayerAgent:
    """A player character agent."""

    def __init__(self, character: Character, llm: LLMClient):
        self.character = character
        self.llm = llm
        self.messages: list[dict[str, Any]] = []

    async def take_turn(self, game_state: GameState, prompt: str) -> LLMResponse:
        """Decide what to do on this player's turn."""
        char_class = self.character.character_class.value
        system = player_system_prompt(self.character, game_state)
        tools = get_player_tools(char_class)

        parts = []
        if game_state.narrative_log:
            recent = "\n".join(game_state.narrative_log[-5:])
            parts.append(f"\nHere's what happened recently:\n{recent}")
        parts.append(f"DM said:\n{prompt}")
        parts.append("It's your turn. What do you do?")

        self.messages.append({"role": "user", "content": "\n\n".join(parts)})

        response = await self.llm.generate(
            messages=self.messages,
            system=system,
            tools=tools,
        )

        self.messages.append({"role": "assistant", "content": response.text})

        return response
