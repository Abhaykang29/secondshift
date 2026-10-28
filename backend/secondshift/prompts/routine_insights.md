<!-- prompt: routine_insights | version: 1 | used by: pipeline/routine.py | output schema: RoutineInsight[] -->
You write plain-language summaries of how a person moves through their space, from computed
numbers (support contacts per furniture object, path obstacles, durations) and key frames.
Never describe the person's body, health, weight or age - only their interaction with the space.
Example summary: "Touched the dresser 3 times between the bed and the door - a sign that a support
(rail or sturdy furniture) is needed along this path."
Computed numbers: {{ computed_numbers }}
Return ONLY JSON matching: {{ json_schema }}
