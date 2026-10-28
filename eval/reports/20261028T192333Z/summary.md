# SecondShift eval summary

Dataset: synthetic scenarios (mock labels - NOT human-labelled ground truth)

| Config | Precision | Recall | F1 | Est. cost | Wall time |
|---|---|---|---|---|---|
| spark_only | 0.9412 | 1.0 | 0.9697 | $0.083 | 0.04s |
| spark_sam | 1.0 | 1.0 | 1.0 | $0.1331 | 0.02s |
| wonder_only | 0.9412 | 1.0 | 0.9697 | $0.276 | 0.02s |
| wonder_sam | 1.0 | 1.0 | 1.0 | $0.326 | 0.02s |

Rule compiler: status accuracy 1.0, primitive accuracy 1.0 on 40 Appendix B sentences.

Honest note: mock numbers validate the harness, not the product.
Real accuracy requires TODO(TEAM) human-labelled captures.
