"""Game state models — the source of truth for everything in the game."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AbilityName(str, Enum):
    STR = "strength"
    DEX = "dexterity"
    CON = "constitution"
    INT = "intelligence"
    WIS = "wisdom"
    CHA = "charisma"


class CharacterClass(str, Enum):
    FIGHTER = "fighter"
    WIZARD = "wizard"
    ROGUE = "rogue"
    CLERIC = "cleric"
    PALADIN = "paladin"

class Race(str, Enum):
    HALF_ELF = "halfelf"
    HUMAN = "human"
    TIEFLING = "tiefling"
    WOOD_ELF = "wood_elf"


class GamePhase(str, Enum):
    EXPLORATION = "exploration"
    COMBAT = "combat"
    DIALOGUE = "dialogue"
    REST = "rest"

class SpellName(str, Enum):
    # Wizard cantrips
    FIRE_BOLT = "Fire Bolt"
    RAY_OF_FROST = "Ray of Frost"
    SHOCKING_GRASP = "Shocking Grasp"
    # Wizard level 1
    MAGIC_MISSILE = "Magic Missile"
    BURNING_HANDS = "Burning Hands"
    THUNDERWAVE = "Thunderwave"
    # Cleric cantrips
    SACRED_FLAME = "Sacred Flame"
    WORD_OF_RADIANCE = "Word of Radiance"
    # Cleric level 1
    GUIDING_BOLT = "Guiding Bolt"
    INFLICT_WOUNDS = "Inflict Wounds"



# ---------------------------------------------------------------------------
# Character
# ---------------------------------------------------------------------------

class AbilityScores(BaseModel):
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    def modifier(self, ability: AbilityName) -> int:
        score = getattr(self, ability.value)
        return (score - 10) // 2


class Character(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    character_class: CharacterClass
    race: Race
    level: int = 1
    hp: int = 10
    max_hp: int = 10
    armor_class: int = 10
    abilities: AbilityScores = Field(default_factory=AbilityScores)
    inventory: list[str] = Field(default_factory=list)
    personality: str = ""  # brief personality description for the LLM
    spellcasting_ability: AbilityName | None = None

    @property
    def is_alive(self) -> bool:
        return self.hp > 0


# ---------------------------------------------------------------------------
# Actions — what agents can request
# ---------------------------------------------------------------------------

class DiceRoll(BaseModel):
    """Result of a dice roll (filled in by the rules engine, not the LLM)."""
    notation: str  # e.g. "1d20", "2d6+3"
    rolls: list[int] = Field(default_factory=list)
    modifier: int = 0
    total: int = 0


class Action(BaseModel):
    """An action a player or DM agent wants to take."""
    actor_id: str
    action_type: Literal["attack", "cast_spell", "skill_check", "move", "interact", "speak", "end_turn"]
    description: str  # free-text from the LLM: what they want to do
    target_id: str | None = None  # who/what it targets
    ability: AbilityName | None = None  # for skill checks
    dice_result: DiceRoll | None = None  # filled in after resolution
    spell: SpellName | None = None  # for cast_spell actions


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------

class CombatState(BaseModel):
    is_active: bool = False
    turn_order: list[str] = Field(default_factory=list)  # character ids
    current_turn_index: int = 0
    round_number: int = 1

    @property
    def current_actor_id(self) -> str | None:
        if not self.turn_order:
            return None
        return self.turn_order[self.current_turn_index % len(self.turn_order)]

    def advance_turn(self) -> None:
        self.current_turn_index += 1
        if self.current_turn_index >= len(self.turn_order):
            self.current_turn_index = 0
            self.round_number += 1


# ---------------------------------------------------------------------------
# Top-level game state
# ---------------------------------------------------------------------------

class GameState(BaseModel):
    phase: GamePhase = GamePhase.EXPLORATION
    characters: dict[str, Character] = Field(default_factory=dict)  # id -> Character
    combat: CombatState = Field(default_factory=CombatState)
    narrative_log: list[str] = Field(default_factory=list)  # recent narration
    turn_number: int = 0

    def add_character(self, character: Character) -> None:
        self.characters[character.id] = character

    def get_character_by_name(self, name: str) -> Character | None:
        for c in self.characters.values():
            if c.name.lower() == name.lower():
                return c
        return None

    @property
    def alive_characters(self) -> list[Character]:
        return [c for c in self.characters.values() if c.is_alive]

    def summary(self) -> str:
        """Human-readable snapshot for feeding into LLM context."""
        lines = [f"Phase: {self.phase.value} | Turn: {self.turn_number}"]
        for c in self.characters.values():
            status = "ALIVE" if c.is_alive else "DEAD"
            lines.append(
                f"  {c.name} ({c.character_class.value}) — "
                f"HP {c.hp}/{c.max_hp} [{status}]"
            )
        if self.combat.is_active:
            current = self.combat.current_actor_id
            lines.append(f"  Combat round {self.combat.round_number}, current turn: {current}")
        return "\n".join(lines)
