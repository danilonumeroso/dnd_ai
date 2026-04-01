"""Rich terminal display — makes the game look good in the terminal."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from models import Action, Character, GameState


class Display:
    def __init__(self):
        self.console = Console()

    def show_title(self) -> None:
        title = Text("D&D Agents", style="bold magenta")
        subtitle = Text("AI-powered Dungeons & Dragons", style="dim")
        self.console.print(Panel(title + Text("\n") + subtitle, border_style="magenta"))

    def show_party(self, characters: list[Character]) -> None:
        table = Table(title="The Adventuring Party", border_style="green")
        table.add_column("Name", style="bold")
        table.add_column("Class")
        table.add_column("HP", justify="right")
        table.add_column("AC", justify="right")
        table.add_column("Personality", max_width=40)

        for c in characters:
            table.add_row(
                c.name,
                c.character_class.value.capitalize(),
                f"{c.hp}/{c.max_hp}",
                str(c.armor_class),
                c.personality,
            )
        self.console.print(table)

    def show_turn_header(self, turn: int) -> None:
        self.console.rule(f"[bold yellow]Turn {turn}[/bold yellow]")

    def show_dm_narration(self, narration: str) -> None:
        self.console.print(Panel(
            narration,
            title="[bold red]Dungeon Master[/bold red]",
            border_style="red",
        ))

    def show_action_result(self, character: Character, action: Action, result: str) -> None:
        color = {
            "fighter": "bold red",
            "wizard": "bold blue",
            "rogue": "bold green",
            "cleric": "bold yellow",
        }.get(character.character_class.value, "white")

        self.console.print(Panel(
            result, # f"[italic]{action.description}[/italic]\n\n{result}",
            title=f"[{color}]{character.name}[/{color}]",
            border_style=color.replace("bold ", ""),
        ))

    def show_state_summary(self, state: GameState) -> None:
        self.console.print(f"\n[dim]{state.summary()}[/dim]\n")

    def show_dice_roll(self, notation: str, total: int, context: str = "") -> None:
        prefix = f"{context}: " if context else ""
        self.console.print(f"  [cyan]{prefix}rolled {notation} = {total}[/cyan]")

    def show_error(self, message: str) -> None:
        self.console.print(f"[bold red]Error:[/bold red] {message}")
