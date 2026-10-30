"""compile_rule: one plain-English sentence -> a RuleSpec or a refusal.

Thin wrapper over the rule compiler (Layer 1 safety precheck +
Spark Layer 2). A refusal is a RuleSpec whose status is REFUSED or
NEEDS_CLARIFICATION, with the reason and alternatives attached -
callers show it as-is.
"""

from secondshift.domain.rules import RuleSpec
from secondshift.providers.base import VisionReasoner
from secondshift.rules.compiler import compile_rule as _compile_rule


def compile_rule(sentence: str, vision: VisionReasoner | None = None) -> RuleSpec:
    return _compile_rule(sentence, vision=vision)
