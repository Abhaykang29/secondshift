<!-- prompt: fix_plan | version: 1 | used by: pipeline/fixes.py | output schema: FixPlanChoice -->
Pick the best fix for this hazard from the library ONLY. You may not invent products, brands or
prices. Write at most 5 short plain-language steps, about grade-6 reading level, in the checkup
language.
Hazard: {{ hazard }}
Home context: {{ home_context }}
Fix library: {{ fix_library }}
Language: {{ language }}
Return ONLY JSON: { "chosen_fix_id": string, "alternative_fix_ids": string[], "plain_language_steps": string[] (<= 5) }
