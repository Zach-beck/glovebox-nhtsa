"""Stable instructions. Changing this string changes the context every client caches."""

INSTRUCTIONS = (
    "Glovebox reads public NHTSA data on this machine. "
    "Call vehicle_profile first when you have a VIN or a year, make, and model. "
    "A missing spec means NHTSA has no value, not that the vehicle lacks the equipment. "
    "Not Applicable values are omitted on purpose. "
    "Recall rows are campaigns filed against a model string. They do not show whether a specific VIN was repaired. "
    "Not Rated is a value NHTSA published. It is not zero stars and it is not a safety judgment. "
    "Complaint results are counts only. They never include owner narratives or partial VINs. "
    "An empty recall or rating list can mean the model string does not match that dataset. "
    "Use list_model_names before saying nothing was filed or tested."
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
