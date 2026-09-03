---
name: beauty-advisor
description: >-
  Recommend and preview makeup looks based on the user's face shape and skin tone,
  using YouCam (Perfect Corp) AI. Analyzes the selfie, suggests suitable looks, then
  renders a virtual makeup try-on image. Use for "推薦妝容", "幫我上妝", "makeup look",
  "virtual makeup". Do NOT use for skin-condition scoring, hair, or clothes.
version: 1.0.1
requirements:
  credentials:
    - name: YOUCAM_API_KEY
      source: env | credentials.json (in the skill root, next to SKILL.md)
  network:
    - yce-api-01.makeupar.com
  apis:
    - face-attr-analysis
    - skin-tone-analysis
    - makeup-vto
    - look-vto
  permissions:
    - type: exec
      commands: [python]
---

# Beauty Advisor

An analysis + generation skill: analyze face shape and skin tone, then recommend and **preview**
a makeup look. There is no `run.py`: run the flow here through `youcam_core.py`.

## When to trigger
When the user wants a makeup recommendation or a virtual try-on. For skin scores, hair, or
clothes, hand off to the matching skill.

## Ask first (this skill has multiple generation options) and state cost
Before generating, ask the user which they want, and tell them the credit cost of each option:
- **Full look (preset template)** — apply a curated full-face look (`look-vto`)
- **Custom effects** — specify individual items (lip color, eyeshadow, blush, …) (`makeup-vto`)
Get costs with `python scripts/youcam_core.py cost --feature look-vto` and `--feature makeup-vto`
(and `--feature face-attr-analysis` / `--feature skin-tone-analysis` for the analysis step),
tell the user, and only run what they choose.

## Get the latest API spec (do this every run)
Read the doc section(s) for the steps you will run and open the **latest version** for endpoints
/ parameters:
- Facial attributes: https://docs.perfectcorp.com/reference/ai_face_analyzer.md
- Skin tone: https://docs.perfectcorp.com/reference/ai_skin_tone_analysis.md
- Makeup try-on (custom): https://docs.perfectcorp.com/reference/makeup_vto.md
- Full look (template): https://docs.perfectcorp.com/reference/ai_look_vto.md

## Prerequisites
A clear, front-facing selfie. `python scripts/youcam_core.py validate-key` (0 credits); guide the user to
set the key if missing.

## Flow
1. **Analyze** (as needed): `run --feature face-attr-analysis` for face shape,
   `run --feature skin-tone-analysis` for colors.
2. **Recommend**: use `references/guide.md` to pick a look/colors from face shape + skin tone.
3. **Preview** (the option the user chose):
   - Full look: read templates `GET /s2s/<ver>/task/template/look-vto`, then
     `run --feature look-vto --src_file <photo> --param template_id=<id>`
   - Custom: `run --feature makeup-vto --src_file <photo> --param effects='[{...}]'`
     (each `effects` item is one category; see the doc's category schema and pattern catalogs)
4. The generation returns a result image URL in `data.results.url`.

## Output rules
* **Return the result image URL exactly as given** (you may make it a hyperlink, but do not
  modify or shorten it).
* Explain the recommendation (why this look suits their face shape / skin tone).
* **Always end with this note:** "This preview image is AI-generated and for reference only;
  actual makeup results may vary by product, skin, and lighting."
