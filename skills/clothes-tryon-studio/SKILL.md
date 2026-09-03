---
name: clothes-tryon-studio
description: >-
  Virtual clothes try-on studio using YouCam (Perfect Corp) AI. Swap outfits onto the
  user's photo, optionally change the background, and optionally turn the result into a
  short motion video (turn / runway / pose). Use for "換衣", "虛擬試穿", "outfit try-on",
  "try on clothes". Do NOT use for makeup, hair, or skin analysis.
version: 1.0.1
requirements:
  credentials:
    - name: YOUCAM_API_KEY
      source: env | credentials.json (in the skill root, next to SKILL.md)
  network:
    - yce-api-01.makeupar.com
  apis:
    - cloth-v4
    - bg-replace
    - image-to-video
  permissions:
    - type: exec
      commands: [python]
---

# Clothes Try-on Studio

A generation skill: try on clothes, optionally change the background, optionally turn the result
into a short motion video. There is no `run.py`.

## When to trigger
When the user wants to try clothes on virtually. For makeup, hair, or skin, hand off to the
matching skill.

## Ask first (this skill has multiple generation steps) and state cost
Before generating, ask the user which steps they want and tell them the credit cost of each:
- **Try on clothes** (`cloth-v4`) — required base step
- **Change background** (`bg-replace`) — optional
- **Motion video** (`image-to-video`) — optional; note video is billed per second
Get costs with `python scripts/youcam_core.py cost --feature cloth-v4` (and `--feature bg-replace`,
`--feature image-to-video`), tell the user the total, and only run what they choose.

## Get the latest API spec (do this every run)
- Clothes: https://docs.perfectcorp.com/reference/ai_clothes.md (latest engine cloth-v4)
- Background change: https://docs.perfectcorp.com/reference/ai_photo_background_change.md
- Video generator: https://docs.perfectcorp.com/reference/ai_video_generator.md
Pass `--version` if newer than `api-fallback.yaml`.

## Prerequisites
1. A photo of the person (full-body or upper-body) plus one garment reference image (product or
   worn photo) or a template_id.
2. `python scripts/youcam_core.py validate-key` (0 credits); guide the user to set the key if missing.

## Flow (only the chosen steps)
1. **Try on** (cloth-v4):
   ```
   python scripts/youcam_core.py run --feature cloth-v4 --src_file <person.jpg> --ref_file <garment.jpg> \
       --param garment_category=full_body
   ```
   (or use a template: `--param template_id=<id>`; confirm the exact `garment_category` value from
   the latest doc — see Notes.)
2. **(Optional) Change background** (bg-replace): on the result or original image,
   `run --feature bg-replace --src_file <img> --param type=prompt --param prompt="A sunny beach"`
   or `--param type=template --param template_id=<id>`.
3. **(Optional) Motion video** (image-to-video):
   `run --feature "image-to-video" --src_file <img> --param resolution=720 --param dst_duration=5 --param prompt="turn around / runway walk"`
4. Each generation returns a result image/video URL in `data.results.url`.

## Output rules
* **Return the result image/video URL exactly as given** (hyperlink is OK; do not modify or
  shorten it).
* Video takes longer (the poll timeout is set higher); wait for `success`.
* **Always end with this note:** "This try-on image/video is AI-generated and for reference only;
  actual fit and appearance may vary."

## Notes
`cloth-v4` `garment_category` is confirmed for `full_body`; the upper/lower-body token spelling is
not yet 100% confirmed, so verify it against the latest doc parameter table before running (see
the handoff GAPS).
