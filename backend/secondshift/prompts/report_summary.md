<!-- prompt: report_summary | version: 1 | used by: reports/report.py | output schema: SummaryText -->
Write a 2-3 sentence summary of this home check-up report. Warm, specific, plain language, in the
checkup language. No fear-mongering, no guarantees, no medical claims.
Report: {{ report_json }}
Language: {{ language }}
Return ONLY JSON: { "summary": string }
