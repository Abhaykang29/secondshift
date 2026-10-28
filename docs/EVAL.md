# Evaluation

Protocol: spec section 15.

## Datasets
TODO(TEAM): Person A films 10-15 spaces, some hazards deliberately staged, some spaces clean (hard negatives). Videos are NOT committed; manifests (`EvalCapture`) live in `eval/datasets/`. Falls ground truth: CDC "Check for Safety" applied by hand. Babyproofing: pack items.

## Labeling
Labeling page at `/eval/label` (dev only, Phase 5): play video, mark time ranges, pick item_id + room, save to manifest.

## Matching and metrics
A prediction matches ground truth if same item_id, same room, evidence timestamp within a GT range +/- 3s; one-to-one greedy by descending risk score. Report precision, recall, F1 (overall + per item), confirmed-only precision, needs-human rate, cannot-assess rate, cost and latency per scan.

## Ablations
Configs in `eval/configs/`: spark_only, spark_sam, wonder_only, wonder_sam. Headline: what SAM's cross-check does to false positives and recall - computed, never assumed.

## Rule compiler eval
`eval/rules/sentences.yaml` (Appendix B, 40 sentences). Metrics: correct status, correct primitives, schema-valid rate, alternatives-offered rate. Ablation: precheck on/off.

## Watch eval
TODO(TEAM): 20-30 short clips per demo rule, with hard negatives and obstructions. Metrics: event precision/recall, false alarms/hour, CANNOT TELL correctness during obstructions, median detection latency, provider calls/hour.

## Running
`python eval/run_eval.py --dataset <id> --config <name>` -> `eval/reports/<timestamp>/summary.md|json` + charts. The `/eval` page reads the latest JSON.

## Scope valve (decide Oct 30 evening)
If confirmed precision < 0.6 or recall < 0.4 on the first 3 real spaces: cut the falls pack to the 6 most reliable items, re-run, note it in DECISIONS.md.
