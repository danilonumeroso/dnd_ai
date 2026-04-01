# D&D Agents

This repo contains a minimal code implementations for AI agents playing Dungeons & Dragons. This was done mainly to
experiment with agentic AI workflows as well as low-code tools such as Claude Code.
Architectural choices were done by myself whereas annoying implementation details were left for Claude to finish up.
All in all I had a lot of fun doing this, and the results were quite nice!

In a nutshell, this code implements a Dungeon Master agent narrating the story and running encounters, while player agents each control a character with a distinct personality, class and abilities.

## Architecture

```
models.py       — Game entities
rules.py        — Game engine and mechanics (deterministic)
agents/
  dm.py         — DM agent
  player.py     — Player agent
  tools.py      — Tool definitions (e.g., spells, attacks, actions, ...)
game.py         — Game loop: orchestrates agents
display.py      — Rich terminal UI
llm.py          — LLM client abstraction + implementations (e.g., Anthropic/Gemini)
main.py         — Main
```

The LLM handles narrative and decision-making; all dice rolls and stat tracking are done in code.
This repo has some limitations

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API key
```

Set your API key in `.env`:
```
ANTHROPIC_API_KEY=your-key-here
# or
GEMINI_API_KEY=your-key-here
```

## Usage

```bash
python main.py --provider <gemini|anthropic>
```

## Party

The default party (in case you're wondering: yes! They're taken from my real DnD campaign):

| Name | Class | Personality |
|------|-------|-------------|
| Thalindra | Wizard | Curious, logical |
| Seyrie | Fighter | Brave, altruistic |
| Alfinn | Cleric | Impulsive, sarcastic |
| Aerion | Rogue | Enigmatic, selfish |

You can experiment with new characters and personalities by modifying game.py::create_default_party().

## Demo

Sessions are saved as markdown to the `sessions/` directory after each run. Check the existing ones for examples.

## Limitations

- Some D&D 5e rules were simplified for code economy (e.g., no competence/mastery, no crits, no saving throws, modified spell mechanics and a lot more)
- No local LLMs supported (but they're easy to add by implementing the LLMClient interface in llm.py)
- Only four classes supported (i.e., fighter, wizard, rogue and cleric)
- Only experimented with Gemini since it's the only provider that offers a properly functioning free tier (and I'm tight we money :) )

