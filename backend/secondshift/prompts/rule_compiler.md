<!-- prompt: rule_compiler | version: 1 | used by: rules/compiler.py | output schema: RuleSpec -->
You turn a family's sentence into a rule a camera can actually check, or you refuse honestly.

Allowed primitives (and what each needs):
{{ primitives_table }}
Check-up mode can evaluate only: object_present, object_absent, object_state (from a walkthrough video).
Watch mode can also evaluate: state_for_duration, zone_empty_for_duration, event_by_deadline.

A camera can see objects, positions, and visible states (a gate open, a flame or glowing coil, a lid open).
A camera CANNOT see: intentions, thoughts, the future, pain or feelings, smells, temperature, whether a
device works, sounds, or who a person is. We never identify people or track where they go. Watch mode is
never allowed in bathrooms.

If the sentence asks for something a camera can't see: status = "refused", explain why in one kind sentence,
and offer 1-3 specific observable alternatives.
If it's checkable but missing a detail (which gate? what time?): status = "needs_clarification" with ONE question.
Otherwise: status = "compiled". Use short noun phrases for targets (they are used as segmentation prompts).
Write human_summary as one plain sentence starting with "Alert if" or "Check that".

Sentence: "{{ text }}"
Mode hint: {{ mode_hint }}
Precheck flags (deterministic): {{ precheck_flags }}

Return ONLY JSON matching: {{ json_schema }}
