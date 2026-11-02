"""Research prototype. Outputs are visual estimates, never safety determinations."""

CLASSES = ("no-damage", "minor-damage", "major-damage", "destroyed")
EVENT_SPLITS = {
    "hurricane-harvey": "train",
    "hurricane-michael": "train",
    "hurricane-florence": "validation",
    "hurricane-matthew": "test",
    "mexico-earthquake": "train",
}
