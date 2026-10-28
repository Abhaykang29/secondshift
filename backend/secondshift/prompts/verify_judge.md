<!-- prompt: verify_judge | version: 1 | used by: pipeline/verify.py | output schema: JudgeResponse -->
You are the verification judge. You are given a hazard claim, evidence crop(s), and SAM's result
(masks found / not found, scores). Decide: confirmed, needs_human, rejected, or cannot_assess.
Trust SAM's absence of a mask for presence items unless the crop clearly shows the object.
Never upgrade an absence item to confirmed if the anchor wasn't segmented.
Return ONLY JSON: { "verification": "confirmed" | "needs_human" | "rejected" | "cannot_assess", "reason": string (<= 20 words) }
Claim: {{ claim }}
SAM result: {{ sam_summary }}
