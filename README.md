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
```

Export your API key:
```
ANTHROPIC_API_KEY=your-key-here
# or
GEMINI_API_KEY=your-key-here
# or
OPENROUTER_API_KEY=your-key-here
```

## Usage

```bash
python main.py --provider <gemini|anthropic|openrouter|huggingface>
```

### Running local models via HuggingFace TGI

You can run the code with a locally hosted model using [Text Generation Inference](https://github.com/huggingface/text-generation-inference). This requires Docker and an Nvidia GPU.

**1. Start a TGI server**

Mount a local directory so model weights are cached across restarts:

```bash
docker run --gpus all -p 8080:80 \
  -v $HOME/.cache/huggingface:/data \
  ghcr.io/huggingface/text-generation-inference \
  --model-id Qwen/Qwen2.5-7B-Instruct --quantize eetq
```

Wait until you see `Connected` in the logs before proceeding. The first run will download the model weights (~15GB).

**2. Run the code**

```bash
python main.py --provider huggingface
```

**Notes**
- The `--quantize eetq` flag reduces VRAM usage enough to fit a 7B model on a 12GB GPU
- Models with strong tool calling support work best (e.g. Qwen2.5, Llama-3.1); smaller or general-purpose models may struggle with structured tool use
- To use a different model or a non-default endpoint, instantiate `HuggingFaceClient` directly with `model` and `base_url` parameters

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
- Only four classes supported (i.e., fighter, wizard, rogue and cleric)
- Only experimented with free models: OpenRouter/Gemini/locally deployed ones (I'm tight with money :) )

