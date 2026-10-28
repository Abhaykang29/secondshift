<!-- prompt: ask_answer | version: 1 | used by: api/ask.py | output schema: AskAnswer -->
Answer the parent's question using only this check-up report. Reply in the same language as the
question, at most 80 words, citing hazard titles where relevant. Never give medical advice; if
asked a medical question, gently suggest asking their doctor.
Question: {{ question }}
Report: {{ report_json }}
Return ONLY JSON: { "answer": string }
