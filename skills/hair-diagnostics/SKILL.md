---
name: hair-diagnostics
description: >-
  Diagnose hair-health metrics — density, type, frizziness, length — from a single
  selfie using YouCam (Perfect Corp) AI, and return one combined report. Use for
  "頭髮體檢", "髮質分析", "hair diagnostics", "hair health report". Do NOT use for
  hairstyle/color try-on (that's hair-color-style-advisor), skin, makeup, or clothes.
version: 1.0.1
requirements:
  credentials:
    - name: YOUCAM_API_KEY
      source: env | credentials.json (in the skill root, next to SKILL.md)
  network:
    - yce-api-01.makeupar.com
  apis:
    - hair-density-detection
    - hair-type-detection
    - hair-frizziness-detection
    - hair-length-detection
  permissions:
    - type: exec
      commands: [python]
---

# Hair Diagnostics

A detection skill that can call up to four hair-diagnostic APIs and combine them into one
report. There is no `run.py`.

## When to trigger
When the user wants hair-health insight (density / type / frizziness / length). For hairstyle or
color try-on, hand off to hair-color-style-advisor.

## Ask first (this skill has multiple detections) and state cost
Before running, ask the user which metrics they want and tell them the credit cost of each:
- **Density** (`hair-density-detection`)
- **Type** (`hair-type-detection`)
- **Frizziness** (`hair-frizziness-detection`)
- **Length** (`hair-length-detection`)
- **All four (full report)**
Get costs with `python scripts/youcam_core.py cost --feature hair-density-detection` (and the others),
tell the user the total, and only run what they choose.

## Get the latest API spec (do this every run)
Open the doc section(s) for the chosen metrics and read the **latest version**:
- https://docs.perfectcorp.com/reference/ai_hair_density_detection.md
- https://docs.perfectcorp.com/reference/ai_hair_type_detection.md
- https://docs.perfectcorp.com/reference/ai_hair_frizziness_detection.md
- https://docs.perfectcorp.com/reference/ai_hair_length_detection.md

## Prerequisites (photo)
- **Density and Length: a single clear, front-facing selfie that shows the hair.**
- **Type and Frizziness need 3 angle photos instead of one** — front-facing, right-facing, and
  left-facing, in that order (the API requires exactly 3).
- **Only if Density is selected**, ask for a photo with the **head tilted down ~45° so the
  hairline and scalp are visible** (density needs to see scalp visibility). If the user only wants
  type/frizziness/length, do NOT require the tilted pose.
- `python scripts/youcam_core.py validate-key` (0 credits); guide the user to set the key if missing.

## Run (only the chosen metrics)
```
python scripts/youcam_core.py run --feature hair-density-detection    --src_file <photo>
python scripts/youcam_core.py run --feature hair-type-detection       --src_files <front.jpg> <right.jpg> <left.jpg>
python scripts/youcam_core.py run --feature hair-frizziness-detection --src_files <front.jpg> <right.jpg> <left.jpg>
python scripts/youcam_core.py run --feature hair-length-detection     --src_file <photo>
```
Each returns JSON (`data.results.hair_*{mapping, term}`). Interpret with `references/guide.md`
and assemble one report.

## Output rules
* For each selected metric, give the term + a plain-language note; end with an overall summary
  and gentle care directions.
* If a metric is missing in the response, skip it — do not fill it in.
* **Always end with this note:** "This is an AI-based hair detection, not a medical diagnosis or
  treatment. Results are for reference only; for hair-loss or scalp concerns, consult a
  dermatologist. Photo quality and pose can affect the results."
