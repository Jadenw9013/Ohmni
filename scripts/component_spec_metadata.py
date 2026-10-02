"""Shared authoring metadata; source status is never rewritten."""


def library_metadata(record, uncertainties, *, provisional_reasons=(), **extra):
    return {
        "provisional": record["status"] != "complete" or bool(provisional_reasons),
        "uncertain_values": list(dict.fromkeys([*uncertainties, *provisional_reasons])),
        "appearance_confidence": record["confidence"]["materials_appearance"],
        "electrical_admission": "NOT_EVALUATED",
        "footprint_binding": None,
        **extra,
    }
