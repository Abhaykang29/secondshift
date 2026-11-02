# Honesty numbers

Computed by `scripts/honesty_report.py` from stored results - never typed by hand.
Command: `.venv/bin/python scripts/honesty_report.py`

- Clips scored (stored reports from real footage): **1** - fewer than 10 clips, so treat every rate below as a small sample.
- Items scored: **25** (11 answered, 14 cannot-tell).
- Abstain rate (answered CANNOT_TELL): **56.0%**
- Answered accuracy (app Right/Wrong labels): **no data** from 0 labels (0 right, 0 wrong).
- Owner ground truth on test_1.mp4: recall 6/8 (strict item ids 5/8); reported findings outside the owner's list: 1 - FALL-PET-PATH (kitchen, confirmed).
- Wrong-and-confident (confirmed findings labeled Wrong): **0**.
- Clean-room false alarms (09_clean_a / 10_clean_b): **not computable - the clean-room clips were never received.**
- Before/after re-film: 0 cannot-tell items resolved by 3 follow-up clip(s) (0 follow-up findings in stored reports).
- Partner scoring notes (NN_notes.txt): **not received** - scoring against partner notes was not possible.

Definitions: an item is 'answered' when the report carries a hazard verdict
(confirmed / needs a human look / rejected) and 'abstained' when it sits in
cannot_assess. Review-label accuracy counts only hazards a person marked
Right or Wrong in the app.
