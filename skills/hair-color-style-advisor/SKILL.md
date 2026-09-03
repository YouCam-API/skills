---
name: hair-color-style-advisor
description: >-
  Recommend a hairstyle and hair color based on the user's face shape and skin tone,
  then preview them with YouCam (Perfect Corp) AI. Use for "推薦髮型", "換髮色",
  "hairstyle advice", "hair color try-on". Do NOT use for hair health diagnostics
  (that's hair-diagnostics), skin, makeup, or clothes.
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
    - hair-transfer
    - hair-color
  permissions:
    - type: exec
      commands: [python]
---

# Hair Color & Style Advisor

An analysis + generation skill: analyze face shape and skin tone, then recommend and **preview**
a hairstyle and/or hair color. There is no `run.py`.

## When to trigger
When the user wants a hairstyle/color recommendation or try-on. For hair-health diagnostics,
hand off to hair-diagnostics.

## Ask first (this skill has multiple generation options) and state cost
Before generating, ask the user what they want and tell them the credit cost of each:
- **Restyle (change hairstyle)** — `hair-transfer`
- **Recolor (change hair color)** — `hair-color`
- **Both**
Get costs with `python scripts/youcam_core.py cost --feature hair-transfer` and `--feature hair-color`
(plus the analysis features if you run them), tell the user, and only run what they choose.

## Get the latest API spec (do this every run)
- Facial attributes: https://docs.perfectcorp.com/reference/ai_face_analyzer.md
- Skin tone: https://docs.perfectcorp.com/reference/ai_skin_tone_analysis.md
- Restyle: https://docs.perfectcorp.com/reference/ai_hairstyle.md (latest may be hair-transfer v2.1)
- Recolor: https://docs.perfectcorp.com/reference/ai_hair_color.md
Pass `--version` if newer than `api-fallback.yaml`.

## Prerequisites
A clear, **front-facing** selfie that shows the hair. `python scripts/youcam_core.py validate-key`
(0 credits); guide the user to set the key if missing.

## Flow
1. **Analyze** (as needed): `run --feature face-attr-analysis` for face shape,
   `run --feature skin-tone-analysis` for colors.
2. **Recommend**: use `references/guide.md` — face shape → hairstyle silhouette, skin tone →
   color family.
3. **Restyle** (hair-transfer): style source can be a preset template or a reference photo.
   - Template: read `GET /s2s/<ver>/task/template/hair-transfer`, then
     `run --feature hair-transfer --src_file <photo> --param template_id=<id>`
   - Reference photo: `run --feature hair-transfer --src_file <photo> --ref_file <style.jpg>`
4. **Recolor** (hair-color): `run --feature hair-color --src_file <photo> --param preset="Honey Blonde"`
   (or custom pattern + palettes; ombre needs blend_strength / line_offset — see the doc).
5. The generation returns a result image URL in `data.results.url`.

## Output rules
* **Return the result image URL exactly as given** (hyperlink is OK; do not modify it).
* Explain the recommendation (face shape → style, skin tone → color).
* **Always end with this note:** "This preview image is AI-generated and for reference only;
  real hairstyle/color results may vary. For coloring, consult a professional stylist."
