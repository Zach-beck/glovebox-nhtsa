"""Stable instructions. Changing this string changes the context every client caches."""

INSTRUCTIONS = (
    "Glovebox reads public NHTSA data on this machine. "
    "Call vehicle_profile first when you have a VIN or a year, make, and model. "
    "For out-of-scope questions, call coverage_limits or read nhtsa://coverage and use its exact refusal phrases. "
    "A missing spec means NHTSA has no value, not that the vehicle lacks the equipment. "
    "NHTSA sentinel placeholder values are omitted on purpose; do not quote them when summarizing decode output. "
    "Recall rows are campaigns filed against a model string. They do not show whether a specific VIN was repaired. "
    "Not Rated is a value NHTSA published. It is not zero stars and it is not a safety judgment. "
    "Complaint results are counts only. They never include owner narratives or partial VINs. "
    "An empty recall or rating list can mean the model string does not match that dataset. "
    "Use list_model_names before saying nothing was filed or tested. "
    "When a tool returns invalid_arguments, quote only the error object and do not repeat identifiers from the user message."
)

COVERAGE_LIMITS = {
    "title_history": {
        "topic": "title or branded-title history",
        "refusal": "Glovebox does not have title history.",
        "scorer_phrase": "does not have title history",
    },
    "fuel_economy": {
        "topic": "fuel economy or MPG",
        "refusal": "Glovebox does not have fuel economy.",
        "scorer_phrase": "does not have fuel economy",
    },
    "repair_completion": {
        "topic": "whether a specific VIN finished recall work or dealer repair status",
        "refusal": "Glovebox does not show repair completion for a VIN.",
        "scorer_phrase": "does not show repair completion",
    },
}

INVALID_CALL_NOTE = (
    "This call was rejected. Quote only fields from this error object. "
    "Do not repeat campaign numbers, investigation ids, vehicle ids, or other identifiers from the user prompt."
)

SENTINEL_NOTE = (
    "NHTSA sentinel placeholder values are dropped from shaped decode output. "
    "Do not repeat those placeholder words when summarizing specs or other_filled_fields."
)

SPEC_NOTE = (
    "A missing spec means NHTSA has no value on file. "
    "Do not read a missing field as evidence that the vehicle lacks that equipment."
)

REPAIR_NOTE = (
    "These are campaigns filed against the model string. "
    "They do not show whether a specific VIN was repaired. "
    "Confirm an individual vehicle on NHTSA's own recall lookup."
)

COMPLAINT_NOTE = (
    "Counts of consumer reports filed with NHTSA. "
    "They are not findings, and owner narratives are not included."
)

SPELLING_NOTICE = (
    "This spelling returned no rows. A different model string may still have records. "
    "This is not proof that nothing was filed or tested."
)
