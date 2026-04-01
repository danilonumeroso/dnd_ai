"""Dice and rules engine — deterministic game mechanics, no LLM involved."""

from __future__ import annotations

import random
import re

from models import AbilityName, Character, DiceRoll, SpellName
from agents.tools import WIZARD_SPELLS, CLERIC_SPELLS


# ---------------------------------------------------------------------------
# Dice rolling
# ---------------------------------------------------------------------------

def roll_dice(notation: str) -> DiceRoll:
    """Parse and roll dice notation like '2d6+3', '1d20', '4d4-1'."""
    match = re.match(r"(\d+)d(\d+)([+-]\d+)?", notation.strip().lower())
    if not match:
        raise ValueError(f"Invalid dice notation: {notation}")

    count = int(match.group(1))
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    rolls = [random.randint(1, sides) for _ in range(count)]

    return DiceRoll(
        notation=notation,
        rolls=rolls,
        modifier=modifier,
        total=sum(rolls) + modifier,
    )


def roll_d20(modifier: int = 0) -> DiceRoll:
    return roll_dice(f"1d20{modifier:+d}" if modifier else "1d20")


# ---------------------------------------------------------------------------
# Ability / skill checks
# ---------------------------------------------------------------------------

def ability_check(character: Character, ability: AbilityName, dc: int) -> tuple[DiceRoll, bool]:
    """Roll an ability check against a difficulty class."""
    mod = character.abilities.modifier(ability)
    result = roll_d20(mod)
    return result, result.total >= dc


# ---------------------------------------------------------------------------
# Combat mechanics
# ---------------------------------------------------------------------------

def attack_roll(attacker: Character, target: Character) -> tuple[DiceRoll, bool]:
    """Roll to hit a target."""
    ability = {
        "fighter": AbilityName.STR,
        "paladin": AbilityName.STR,
        "cleric": AbilityName.WIS,
        "rogue": AbilityName.DEX,
        "wizard": AbilityName.INT,
    }.get(attacker.character_class.value, AbilityName.STR)

    mod = attacker.abilities.modifier(ability)
    result = roll_d20(mod)
    result.rolls
    return result, result.total >= target.armor_class




def weapon_damage_roll(attacker: Character) -> DiceRoll:
    """Roll damage after a successful hit."""
    damage_dice = {
        "fighter": "1d10",
        "rogue": "1d6",
        "paladin": "1d8",
        "wizard": "2d8",
        "cleric": "1d6",
    }.get(attacker.character_class.value, "1d6")

    return roll_dice(damage_dice)

def spell_damage_roll(spell: SpellName) -> DiceRoll:
    """Roll damage for a spell using its defined damage dice."""
    all_spells = {**WIZARD_SPELLS, **CLERIC_SPELLS}
    spell_info = all_spells.get(spell)
    if not spell_info:
        raise ValueError(f"Unknown spell: {spell}")
    return roll_dice(spell_info["damage"])

def apply_damage(target: Character, damage: int) -> None:
    target.hp = max(0, target.hp - damage)


def roll_initiative(character: Character) -> DiceRoll:
    """Roll initiative (d20 + DEX modifier)."""
    mod = character.abilities.modifier(AbilityName.DEX)
    return roll_d20(mod)
