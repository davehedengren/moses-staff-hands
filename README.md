# Moses' Staff

A webcam game inspired by **Exodus 17:8–13**. Hold a staff overhead and the
Israelite army advances against Amalek. Let your arms drop and Amalek gains
ground. When your arms tire, have friends step in and hold them up for you —
the pose detector only cares that the arms are raised, not who's lifting them.
That's the point: *"So his hands were steady until the going down of the sun."*

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Put your Gemini API key in `.env`:

```
GEMINI_API_KEY=...
```

Optional tunables (also in `.env`, all seconds):

```
DURATION_EASY=90
DURATION_DEFAULT=180
DURATION_HARD=300
DEFAULT_DURATION=default
WARMUP_SECONDS=3
```

## Run

```bash
python main.py                        # default 2 min
python main.py --duration easy        # 1 min
python main.py --duration hard        # 3 min
python main.py --duration-seconds 90  # custom
python main.py --regen-art            # force regenerate sprites
python main.py --camera 1             # pick a different webcam
```

First launch generates sprites with Gemini and caches them to `assets/`.
Later launches reuse the cache and run fully offline.

## Props

A broomstick or light dowel works best. A shovel will be genuinely punishing
at 2–3 minutes — which is the point. Either way, invite two friends: when your
shoulders give out, they can step in as Aaron and Hur.

## Controls

- `R` — restart
- `Q` / `Esc` — quit
