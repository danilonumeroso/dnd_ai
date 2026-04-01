from __future__ import annotations

from datetime import datetime
from pathlib import Path

from agents import DMAgent, PlayerAgent
from display import Display
from llm import LLMClient, LLMResponse, QuotaExhaustedError, ServiceUnavailableError
from models import (
    AbilityName,
    Action,
    Character,
    CharacterClass,
    GamePhase,
    Race,
    AbilityScores,
    GameState,
    SpellName,
)
import rules


# ---------------------------------------------------------------------------
# Party creation — customize your adventuring party here
# ---------------------------------------------------------------------------

def create_default_party() -> list[Character]:
    """Create a party of adventurers."""
    return [
        Character(
            name="Thalindra",
            character_class=CharacterClass.WIZARD,
            race=Race.HALF_ELF,
            hp=6, max_hp=6, armor_class=12,
            abilities=AbilityScores(strength=8, dexterity=14, constitution=10,
                                    intelligence=18, wisdom=12, charisma=11),
            inventory=["spellbook", "component pouch", "dagger"],
            personality="Curious. Logic. Good.",
            spellcasting_ability=AbilityName.INT
        ),
        Character(
            name="Seyrie",
            character_class=CharacterClass.FIGHTER,
            race=Race.TIEFLING,
            hp=10, max_hp=10, armor_class=18,
            abilities=AbilityScores(strength=18, dexterity=8, constitution=14,
                                    intelligence=12, wisdom=10, charisma=14),
            inventory=["heavy armor", "shield", "longsword"],
            personality="Good. Brave. Altruistic.",
        ),
        Character(
            name="Alfinn",
            character_class=CharacterClass.CLERIC,
            race=Race.HUMAN,
            hp=10, max_hp=10, armor_class=17,
            abilities=AbilityScores(strength=10, dexterity=12, constitution=14,
                                    intelligence=8, wisdom=18, charisma=11),
            inventory=["shield", "mace", "medium armor"],
            personality="Impulsive. Sarcastic. Light-hearted.",
            spellcasting_ability=AbilityName.WIS
        ),
        Character(
            name="Aerion",
            character_class=CharacterClass.ROGUE,
            race=Race.WOOD_ELF,
            hp=8, max_hp=8, armor_class=14,
            abilities=AbilityScores(strength=10, dexterity=18, constitution=12,
                                    intelligence=14, wisdom=10, charisma=13),
            inventory=["two daggers", "thieves' tools", "shortbow"],
            personality="Enigmatic. Diffident. Selfish.",
        ),
    ]


# ---------------------------------------------------------------------------
# Game loop
# ---------------------------------------------------------------------------

class Game:
    """Main game orchestrator."""

    def __init__(self, llm: LLMClient, display: Display):
        self.llm = llm
        self.display = display
        self.state = GameState()
        self.dm = DMAgent(llm)
        self.players: dict[str, PlayerAgent] = {}
        self.log_lines: list[str] = []

    def setup(self) -> None:
        """Initialize the game with a party of characters."""
        party = create_default_party()
        for character in party:
            self.state.add_character(character)
            self.players[character.id] = PlayerAgent(character, self.llm)
        self.display.show_party(list(self.state.characters.values()))

    def _log(self, line: str) -> None:
        self.log_lines.append(line)

    def save_session(self, directory: str = "sessions") -> Path:
        """Save the session log as a markdown file."""
        path = Path(directory)
        path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = path / f"session_{timestamp}.md"
        filepath.write_text("\n\n".join(self.log_lines))
        return filepath

    async def run(self, max_turns: int = 10) -> None:
        """Run the game for a number of turns."""
        self._log("# D&D Agents Session")
        self._log(f"*Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

        # Log party
        self._log("## The Adventuring Party")
        for c in self.state.characters.values():
            self._log(
                f"- **{c.name}** — {c.character_class.value.capitalize()} "
                f"({c.race.value}) | HP {c.hp}/{c.max_hp} | AC {c.armor_class}  \n"
                f"  *{c.personality}*"
            )

        try:
            for turn in range(max_turns):
                self.state.turn_number = turn + 1
                self.display.show_turn_header(turn + 1)
                self._log(f"---\n\n## Turn {turn + 1}")

                # 1. DM narrates
                dm_response = await self.dm.take_turn(self.state)
                narration = self.process_dm_response(dm_response)
                self.display.show_dm_narration(narration)
                self._log(f"### Dungeon Master\n\n{narration}")

                # 2. Each player acts
                for char_id, player in self.players.items():
                    character = self.state.characters[char_id]
                    if not character.is_alive:
                        continue
                    response = await player.take_turn(self.state, narration)
                    actions = self.process_player_response(character, response)
                    for action in actions:
                        result = self.resolve_action(action)
                        self.display.show_action_result(character, action, result)
                        self._log(f"### {character.name}\n\n{result}")

                # 3. Show state summary
                self.display.show_state_summary(self.state)
                self._log(f"```\n{self.state.summary()}\n```")

        except QuotaExhaustedError:
            self.display.show_error("Quota exhausted. Saving session and shutting down.")
            self._log("---\n\n*Session interrupted because of reached quota limits.*")

        except ServiceUnavailableError:
            self.display.show_error("Service unavailable after 3 retries. Saving session and shutting down.")
            self._log("---\n\n*Session interrupted because the LLM service was unavailable.*")

        finally:
            filepath = self.save_session()
            self.display.console.print(f"\n[dim]Session saved to {filepath}[/dim]")

    def process_dm_response(self, response: LLMResponse) -> str:
        """Extract narration and handle DM tool calls (start_combat, etc)."""
        narration_parts: list[str] = []

        # Any plain text from the DM counts as narration
        if response.text:
            narration_parts.append(response.text)

        for tool_call in response.tool_calls:
            name = tool_call["name"]
            args = tool_call["input"]

            if name == "narrate":
                narration_parts.append(args["narration"])

            elif name == "start_combat":
                self.state.phase = GamePhase.COMBAT
                # Create enemy characters and add them to the game
                for enemy_data in args["enemies"]:
                    enemy = Character(
                        name=enemy_data["name"],
                        character_class=CharacterClass.FIGHTER,  # for simplicity, all enemies are assumed to be warriors.
                        race=Race.HUMAN,
                        hp=enemy_data["hp"],
                        max_hp=enemy_data["hp"],
                        armor_class=enemy_data["armor_class"],
                        personality="enemy",
                    )
                    self.state.add_character(enemy)
                # Roll initiative for all alive characters
                initiative_order = []
                for char in self.state.alive_characters:
                    init_roll = rules.roll_initiative(char)
                    initiative_order.append((char.id, init_roll.total))
                    self.display.show_dice_roll(
                        init_roll.notation, init_roll.total,
                        f"{char.name} initiative",
                    )
                initiative_order.sort(key=lambda x: x[1], reverse=True)
                self.state.combat.is_active = True
                self.state.combat.turn_order = [cid for cid, _ in initiative_order]
                self.state.combat.current_turn_index = 0
                self.state.combat.round_number = 1
                narration_parts.append(args.get("description", "Combat begins!"))

            elif name == "enemy_attack":
                result = self._resolve_enemy_attack(
                    args["enemy_name"], args["target_name"], args["description"],
                )
                narration_parts.append(result)

            elif name == "request_skill_check":
                target = self.state.get_character_by_name(args["target_name"])
                if target:
                    ability = AbilityName(args["ability"])
                    dc = args["dc"]
                    roll, success = rules.ability_check(target, ability, dc)
                    self.display.show_dice_roll(
                        roll.notation, roll.total,
                        f"{target.name} {ability.value} check (DC {dc})",
                    )
                    outcome = "succeeds" if success else "fails"
                    narration_parts.append(
                        f"{target.name} {outcome} the {ability.value} check "
                        f"(rolled {roll.total} vs DC {dc}). {args['description']}"
                    )

            elif name == "end_combat":
                self.state.phase = GamePhase.EXPLORATION
                self.state.combat.is_active = False
                self.state.combat.turn_order = []
                # Remove dead enemies (keep dead players for narrative)
                enemy_ids = [
                    cid for cid, c in self.state.characters.items()
                    if c.personality == "enemy" and not c.is_alive
                ]
                for cid in enemy_ids:
                    del self.state.characters[cid]
                narration_parts.append(args.get("description", "Combat ends."))

        narration = "\n\n".join(narration_parts)
        self.state.narrative_log.append(narration)
        return narration

    def _resolve_enemy_attack(self, enemy_name: str, target_name: str, description: str) -> str:
        """Resolve an enemy attacking a player through the rules engine."""
        enemy = self.state.get_character_by_name(enemy_name)
        target = self.state.get_character_by_name(target_name)

        if not enemy or not target:
            return f"{enemy_name} tries to attack {target_name}, but something goes wrong."

        roll, hits = rules.attack_roll(enemy, target)
        self.display.show_dice_roll(roll.notation, roll.total, f"{enemy_name} attacks {target_name}")

        if hits:
            dmg = rules.weapon_damage_roll(enemy)
            rules.apply_damage(target, dmg.total)
            self.display.show_dice_roll(dmg.notation, dmg.total, "Damage")
            return (
                f"{description} {enemy_name} hits {target_name} for {dmg.total} damage! "
                f"({target_name}: {target.hp}/{target.max_hp} HP)"
            )
        else:
            return f"{description} {enemy_name} swings at {target_name} but misses! (rolled {roll.total} vs AC {target.armor_class})"

    def process_player_response(self, character: Character, response: LLMResponse) -> list[Action]:
        """Convert player LLM response into Action objects."""
        actions: list[Action] = []

        for tool_call in response.tool_calls:
            name = tool_call["name"]
            args = tool_call["input"]

            if name == "attack":
                target = self.state.get_character_by_name(args["target_name"])
                actions.append(Action(
                    actor_id=character.id,
                    action_type="attack",
                    description=args["description"],
                    target_id=target.id if target else None,
                ))

            elif name == "cast_spell":
                target = self.state.get_character_by_name(args["target_name"])
                actions.append(Action(
                    actor_id=character.id,
                    action_type="cast_spell",
                    description=args["description"],
                    target_id=target.id if target else None,
                    spell=SpellName(args["spell_name"]) if args.get("spell_name") in [s.value for s in SpellName] else None,
                ))

            elif name == "skill_check":
                actions.append(Action(
                    actor_id=character.id,
                    action_type="skill_check",
                    description=args["description"],
                    ability=AbilityName(args["ability"]),
                ))

            elif name == "speak":
                actions.append(Action(
                    actor_id=character.id,
                    action_type="speak",
                    description=args["message"],
                    target_id=None,
                ))

            elif name == "move":
                actions.append(Action(
                    actor_id=character.id,
                    action_type="move",
                    description=args["destination"],
                ))

        # If the LLM didn't use tools, treat its text as a speak action
        if not actions and response.text:
            actions.append(Action(
                actor_id=character.id,
                action_type="speak",
                description=response.text,
            ))

        return actions

    def resolve_action(self, action: Action) -> str:
        """Run an action through the rules engine and update game state."""
        actor = self.state.characters.get(action.actor_id)
        if not actor:
            return "Unknown actor."

        if action.action_type == "attack":
            if not action.target_id:
                return f"{actor.name} tries to attack but can't find the target."
            target = self.state.characters.get(action.target_id)
            if not target:
                return f"{actor.name} tries to attack but the target is gone."

            roll, hits = rules.attack_roll(actor, target)
            self.display.show_dice_roll(roll.notation, roll.total, f"{actor.name} attacks {target.name}")

            if hits:
                dmg = rules.weapon_damage_roll(actor)
                rules.apply_damage(target, dmg.total)
                self.display.show_dice_roll(dmg.notation, dmg.total, "Damage")
                result = (
                    f"{action.description}\n"
                    f"Hits {target.name} for {dmg.total} damage! "
                    f"({target.name}: {target.hp}/{target.max_hp} HP)"
                )
                if not target.is_alive:
                    result += f"\n{target.name} has fallen!"
                    self.state.narrative_log.append(f"{target.name} was slain by {actor.name}!")
                return result
            else:
                return (
                    f"{action.description}\n"
                    f"Misses {target.name}! (rolled {roll.total} vs AC {target.armor_class})"
                )
            
        if action.action_type == "cast_spell":

            if not action.spell:
                return f"{actor.name} tries to cast a spell but fails."
            
            if not action.target_id:
                return f"{actor.name} tries to cast but can't find the target."

            target = self.state.characters.get(action.target_id)
            if not target:
                return f"{actor.name} tries to attack but the target is gone."
            
            # For simplicity, attack roll is used even for spells that require saving throws (yes, even magic missile!).
            roll, hits = rules.attack_roll(actor, target) 
            self.display.show_dice_roll(roll.notation, roll.total, f"{actor.name} attacks {target.name}")

            if hits:
                dmg = rules.spell_damage_roll(action.spell)
                rules.apply_damage(target, dmg.total)
                self.display.show_dice_roll(dmg.notation, dmg.total, "Damage")
                result = (
                    f"{action.description}\n"
                    f"Hits {target.name} for {dmg.total} damage! "
                    f"({target.name}: {target.hp}/{target.max_hp} HP)"
                )
                if not target.is_alive:
                    result += f"\n{target.name} has fallen!"
                    self.state.narrative_log.append(f"{target.name} was slain by {actor.name}!")
                return result
            else:
                return (
                    f"{action.description}\n"
                    f"Misses {target.name}! (rolled {roll.total} vs AC {target.armor_class})"
                )

        elif action.action_type == "skill_check":
            dc = 12 # Default DC 12 when the DM agent didn't set one
            ability = action.ability or AbilityName.STR
            roll, success = rules.ability_check(actor, ability, dc)
            self.display.show_dice_roll(roll.notation, roll.total, f"{actor.name} {ability.value} check (DC {dc})")
            outcome = "Success!" if success else "Failure."
            return f"{action.description}\nRolled {roll.total} vs DC {dc}: {outcome}"

        elif action.action_type == "speak":
            self.state.narrative_log.append(f'{actor.name}: "{action.description}"')
            return f'"{action.description}"'

        elif action.action_type == "move":
            self.state.narrative_log.append(f"{actor.name} moves to {action.description}.")
            return f"{actor.name} moves to {action.description}."

        return f"{actor.name} does something unclear: {action.description}"
