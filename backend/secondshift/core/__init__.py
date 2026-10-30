"""SecondShift core - the reusable engine layer (Pass 3 P4).

Public interface (see docs/ENGINE.md):

    compile_checklist(source, vision) -> Checklist
    check(video_path, checklist, providers, settings, work_dir) -> Report
    recheck(previous, video_path, checklist, providers, settings, work_dir) -> Recheck
    compile_rule(sentence, vision) -> RuleSpec
    live(providers, on_event) -> LiveWatch

The engine is domain-agnostic: a checklist is data, a video is a
file, and the outputs are verdicts with evidence. Nothing in this
package imports the app layer (secondshift.api) or any UI/pack-
specific code - packs enter only as data through the loader.
"""

from secondshift.core.check import check, recheck
from secondshift.core.compile import Checklist, compile_checklist
from secondshift.core.live import live
from secondshift.core.rules import compile_rule

__all__ = ["Checklist", "check", "compile_checklist", "compile_rule", "live", "recheck"]
