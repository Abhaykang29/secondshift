<!-- prompt: recheck_judge | version: 1 | used by: recheck/diff.py | output schema: RecheckJudgement -->
Given the before and after crops for one hazard, decide whether it is resolved, still_present,
or cannot_tell, with a short reason. If the area was not filmed clearly, say cannot_tell.
Return ONLY JSON: { "status": "resolved" | "still_present" | "cannot_tell", "reason": string }
Hazard: {{ hazard }}
