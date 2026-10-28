"""Meta provider package - the ONLY place with Meta HTTP details.

Phase 7 fills these adapters in after `make smoke-meta`. Until then every
class raises ProviderUnavailable so a misconfiguration fails loudly,
never silently. TODO(API): verify all endpoints against dev.meta.ai docs.
"""
