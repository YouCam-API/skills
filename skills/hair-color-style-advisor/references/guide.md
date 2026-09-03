# Hair Color & Style Advisor — recommendation logic & output

## From analysis to recommendation
- **Face shape / ratios → hairstyle silhouette**:
  - Round → add height on top, keep sides closer; Long → add side volume, avoid very long straight
    drops; Square → soften with layers/fringe; Heart → add volume in the lower half to balance.
- **Skin tone → hair color family**: cool tone → ashy/blue-toned browns, cool blondes; warm tone →
  honey blonde, copper brown, warm chestnut.
- Directional suggestions, not hard rules; respect preference and feasibility (e.g. going much
  lighter needs bleaching).

## Two generation APIs
- **hair-transfer (restyle)**: src = the user's selfie; style source = preset template or a
  reference photo (`--ref_file`).
- **hair-color (recolor)**: `preset` (e.g. "Honey Blonde") is simplest; or `pattern` (full/ombre)
  + `palettes` for custom (ombre needs blend_strength, line_offset).

## Output
1. Recommendation rationale (face shape → style, skin tone → color).
2. **The try-on result image URL (returned exactly as given).**
3. Closing note: "This preview image is AI-generated and for reference only; real results may
   vary. For coloring, consult a professional stylist."

Parameters follow the latest doc version; this file is recommendation guidance.
