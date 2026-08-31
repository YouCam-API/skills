# YouCam Skills

This repository packages YouCam (Perfect Corp) AI features as a set of Agent Skills: skin
analysis, facial consultation, makeup, hairstyling, hair diagnostics, and clothes try-on. Install
a skill's folder into an agent environment that supports Skills, and the agent can call the right
YouCam API straight from a natural-language request such as "how does my skin look" or "let me
try on this jacket". Every skill also runs on its own from the command line through its bundled
`scripts/youcam_core.py`, so nothing stops you from calling it directly instead of going through
an agent.

## Before you start

- Python 3, with pip.
- A YouCam API key. Get one at https://yce.perfectcorp.com/api-console.
- The dependencies listed in `requirements.txt` — `requests` and `PyYAML`. From inside a skill's
  folder, run:

  ```
  python scripts/youcam_core.py setup
  ```

  to create a local `.venv` and install them, or install them yourself with `pip install -r scripts/requirements.txt`.

## Setting your API key

`youcam_core.py` looks for your key in this order:

1. The `YOUCAM_API_KEY` environment variable.
2. `credentials.json`, in the skill's root folder, next to `SKILL.md` (see
   `credentials.example.json` there for the expected format).

Set the environment variable however your shell or agent host lets you set one, or create
`credentials.json` yourself with `{"api_key": "..."}`. Since this file lives in each skill's own
folder, it's set per skill — configuring one skill doesn't configure the others.

Confirm it works with:

```
python scripts/youcam_core.py validate-key
```

This costs 0 credits and also returns your current balance.

## Checking cost before you run anything

```
python scripts/youcam_core.py cost --feature skin-analysis
python scripts/youcam_core.py credits
```

Both are free to call, and both are what each skill uses to tell you the price before it runs
anything on your behalf.

## Running a skill

If your agent host supports Skills, just describe what you want and it will pick the right skill
and ask whatever follow-up questions that skill's `SKILL.md` calls for. You can also call
`youcam_core.py` yourself:

```
python scripts/youcam_core.py run --feature skin-analysis --src_file selfie.jpg \
    --param format=json --param dst_actions='["hd_pore","hd_skin_type"]'
```

`run` uploads the file, creates a task, and polls it until it finishes, printing the result as
JSON. `--src_file` takes a local path or a URL; some features also take a `--ref_file` for a
second input, such as a garment photo. `--param` can be repeated for each extra field an API
needs, and `--version` overrides the API version if the agent has learned of a newer one. Photos
need to be jpg, jpeg, or png (mp4 for video) — `youcam_core.py` doesn't convert files for you.

If a task is still running when polling gives up, or you just want to check on it later, use its
`task_id` with:

```
python scripts/youcam_core.py status --feature skin-analysis --task_id <task_id>
```

## The skills

| Skill | What it does |
| --- | --- |
| Skin Analysis Expert | Scores 16 skin concerns plus skin type from one selfie, at your choice of HD or SD detail and overlay or mask visualization. |
| Facial Consultant | Reads skin tone (skin/eyes/brows/lips/hair color) and facial-feature shapes and proportions, including golden-ratio measurements. |
| Beauty Advisor | Recommends a makeup look from your face shape and skin tone, then renders it on your photo — a curated full look or a custom combination of individual effects. |
| Hair Color & Style Advisor | Recommends a hairstyle and/or hair color from your face shape and skin tone, then previews it via a template, a reference photo, or a color preset/custom palette. |
| Hair Diagnostics | Checks hair density, type, frizziness, and length from a selfie and combines them into one report. |
| Clothes Try-on Studio | Swaps an outfit onto your photo, with the option to change the background and turn the result into a short motion video (turn, runway walk, or pose). |

Each skill asks which of its steps you actually want and tells you the credit cost of each one
before calling anything, so you only pay for what you choose.

## A note on the results

Every skill closes its report with a reminder that the result is AI-generated and for reference
only — none of this is medical, cosmetic, or styling advice. Photo quality, angle, and lighting
affect accuracy, and some fields (face shape, for instance) may occasionally be missing from a
response; the skill will leave those out rather than guess.
