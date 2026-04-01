"""Tool definitions for all agents."""

from __future__ import annotations

from typing import Any

from models import SpellName


def format_tools_for_prompt(tools: list[dict[str, Any]]) -> str:
    """Convert tool definitions into a readable list for system prompts."""
    lines = []
    for tool in tools:
        lines.append(f"- {tool['name']}: {tool['description']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Player tools (shared across all classes)
# ---------------------------------------------------------------------------

PLAYER_TOOLS: list[dict[str, Any]] = [
    {
        "name": "attack",
        "description": "Attack a target with your weapon.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_name": {
                    "type": "string",
                    "description": "Name of the character or creature to attack.",
                },
                "description": {
                    "type": "string",
                    "description": "Brief narrative of how you attack.",
                },
            },
            "required": ["target_name", "description"],
        },
    },
    {
        "name": "skill_check",
        "description": "Attempt a skill check (e.g., perception, stealth, persuasion).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ability": {
                    "type": "string",
                    "enum": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
                    "description": "The ability to use for this check.",
                },
                "description": {
                    "type": "string",
                    "description": "What you're trying to do.",
                },
            },
            "required": ["ability", "description"],
        },
    },
    {
        "name": "speak",
        "description": "Say something in-character to another character or NPC.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "What you say, in character.",
                },
                "target_name": {
                    "type": "string",
                    "description": "Who you're speaking to (optional).",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "move",
        "description": "Move to a location or position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Where you want to go.",
                },
            },
            "required": ["destination"],
        },
    },
]


# ---------------------------------------------------------------------------
# Spellcasting tool (used by wizard and cleric)
# ---------------------------------------------------------------------------

CAST_SPELL_TOOL: dict[str, Any] = {
    "name": "cast_spell",
    "description": "Cast a spell from your spell list.",
    "input_schema": {
        "type": "object",
        "properties": {
            "spell_name": {
                "type": "string",
                "description": "Name of the spell to cast (must be from your spell list).",
            },
            "target_name": {
                "type": "string",
                "description": "Target of the spell.",
            },
            "description": {
                "type": "string",
                "description": "Brief narrative of how you cast the spell.",
            },
        },
        "required": ["spell_name", "target_name", "description"],
    },
}


# ---------------------------------------------------------------------------
# Wizard spells
# ---------------------------------------------------------------------------

WIZARD_SPELLS: dict[SpellName, dict[str, Any]] = {
    # Cantrips (unlimited use)
    SpellName.FIRE_BOLT: {
        "level": 0,
        "damage": "1d10",
        "damage_type": "fire",
        "range": "120 ft",
        "description": "Hurl a mote of fire at a creature. Ranged spell attack.",
    },
    SpellName.RAY_OF_FROST: {
        "level": 0,
        "damage": "1d8",
        "damage_type": "cold",
        "range": "60 ft",
        "description": "A frigid beam of blue-white light streaks toward a creature.",
    },
    SpellName.SHOCKING_GRASP: {
        "level": 0,
        "damage": "1d8",
        "damage_type": "lightning",
        "range": "Touch",
        "description": "Lightning springs from your hand to shock a creature you touch.",
    },
    # Level 1 spells
    SpellName.MAGIC_MISSILE: {
        "level": 1,
        "damage": "3d4+3",
        "damage_type": "force",
        "range": "120 ft",
        "description": "Three glowing darts of magical force strike unerringly. Always hits.",
    },
    SpellName.BURNING_HANDS: {
        "level": 1,
        "damage": "3d6",
        "damage_type": "fire",
        "range": "15 ft cone",
        "description": "A thin sheet of flames shoots forth from your outstretched fingertips.",
    },
    SpellName.THUNDERWAVE: {
        "level": 1,
        "damage": "2d8",
        "damage_type": "thunder",
        "range": "15 ft cube",
        "description": "A wave of thunderous force sweeps out from you.",
    },
}


# ---------------------------------------------------------------------------
# Cleric spells (damage only)
# ---------------------------------------------------------------------------

CLERIC_SPELLS: dict[SpellName, dict[str, Any]] = {
    # Cantrips (unlimited use)
    SpellName.SACRED_FLAME: {
        "level": 0,
        "damage": "1d8",
        "damage_type": "radiant",
        "range": "60 ft",
        "description": "Flame-like radiance descends on a creature. DEX save to avoid.",
    },
    SpellName.WORD_OF_RADIANCE: {
        "level": 0,
        "damage": "1d6",
        "damage_type": "radiant",
        "range": "5 ft",
        "description": "You utter a divine word and burning radiance erupts around you.",
    },
    # Level 1 spells
    SpellName.GUIDING_BOLT: {
        "level": 1,
        "damage": "4d6",
        "damage_type": "radiant",
        "range": "120 ft",
        "description": "A flash of light streaks toward a creature. Next attack has advantage.",
    },
    SpellName.INFLICT_WOUNDS: {
        "level": 1,
        "damage": "3d10",
        "damage_type": "necrotic",
        "range": "Touch",
        "description": "You channel negative energy through your touch into a creature.",
    },
}


# ---------------------------------------------------------------------------
# Helper to build per-class tool lists
# ---------------------------------------------------------------------------

def get_player_tools(character_class: str) -> list[dict[str, Any]]:
    """Return the full tool list for a given character class."""
    tools = list(PLAYER_TOOLS)
    if character_class in ("wizard", "cleric"):
        tools.append(CAST_SPELL_TOOL)
    return tools


def get_spell_list(character_class: str) -> dict[SpellName, dict[str, Any]] | None:
    """Return the spell list for a given class, or None."""
    if character_class == "wizard":
        return WIZARD_SPELLS
    elif character_class == "cleric":
        return CLERIC_SPELLS
    return None


def format_spells_for_prompt(spells: dict[SpellName, dict[str, Any]]) -> str:
    """Format a spell dict into readable text for a system prompt."""
    lines = []
    cantrips = {k: v for k, v in spells.items() if v["level"] == 0}
    leveled = {k: v for k, v in spells.items() if v["level"] > 0}

    if cantrips:
        lines.append("Cantrips (at will):")
        for name, info in cantrips.items():
            lines.append(f"  - {name.value}: {info['damage']} {info['damage_type']} | {info['range']} | {info['description']}")

    if leveled:
        lines.append("Level 1 spells:")
        for name, info in leveled.items():
            lines.append(f"  - {name.value}: {info['damage']} {info['damage_type']} | {info['range']} | {info['description']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DM tools
# ---------------------------------------------------------------------------

DM_TOOLS: list[dict[str, Any]] = [
    {
        "name": "narrate",
        "description": "Describe the scene, environment, or what happens next.",
        "input_schema": {
            "type": "object",
            "properties": {
                "narration": {
                    "type": "string",
                    "description": "The narrative text to present to the players.",
                },
            },
            "required": ["narration"],
        },
    },
    {
        "name": "start_combat",
        "description": "Initiate combat with enemies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "enemies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "hp": {"type": "integer"},
                            "armor_class": {"type": "integer"},
                        },
                        "required": ["name", "hp", "armor_class"],
                    },
                    "description": "List of enemies entering combat.",
                },
                "description": {
                    "type": "string",
                    "description": "How combat begins.",
                },
            },
            "required": ["enemies", "description"],
        },
    },
    {
        "name": "enemy_attack",
        "description": "An enemy attacks a player character.",
        "input_schema": {
            "type": "object",
            "properties": {
                "enemy_name": {
                    "type": "string",
                    "description": "Name of the attacking enemy.",
                },
                "target_name": {
                    "type": "string",
                    "description": "Name of the player being attacked.",
                },
                "description": {
                    "type": "string",
                    "description": "How the enemy attacks.",
                },
            },
            "required": ["enemy_name", "target_name", "description"],
        },
    },
    {
        "name": "request_skill_check",
        "description": "Ask a player to make a skill check.",
        "input_schema": {
            "type": "object",
            "properties": {
                "target_name": {
                    "type": "string",
                    "description": "Which player must roll.",
                },
                "ability": {
                    "type": "string",
                    "enum": ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
                },
                "dc": {
                    "type": "integer",
                    "description": "Difficulty class for the check.",
                },
                "description": {
                    "type": "string",
                    "description": "What the check is for.",
                },
            },
            "required": ["target_name", "ability", "dc", "description"],
        },
    },
    {
        "name": "end_combat",
        "description": "End the current combat encounter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "How combat ends.",
                },
            },
            "required": ["description"],
        },
    },
]
