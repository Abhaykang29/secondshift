<!-- prompt: narration_facts | version: 1 | used by: capture/narration.py | output schema: NarrationFact[] -->
Extract routine facts about the SPACE and the daily routine from this narration transcript.
Ignore anything not about the space or routine. Never extract health details - drop them.
Return ONLY JSON: [{ "fact": string, "t": number, "affects": string[] }]
Transcript: {{ transcript }}
