import numpy as np
import pytest
from quake.labels import common_label, common_probabilities, display_result


def test_native_mappings_and_exclusions():
    assert [common_label("xbd", c) for c in ("no-damage", "minor-damage", "major-damage", "destroyed")] == [0,1,1,2]
    assert common_label("xbd", "un-classified") is None
    with pytest.raises(ValueError):
        common_label("unknown", "5")


def test_sum_before_argmax_not_remap_hard_label():
    # Native winner is destroyed, grouped winner is damaged.
    p = [.05,.30,.30,.35]
    assert np.argmax(p) == 3
    result = display_result(p)
    assert result["category"] == "damaged" and result["priority"] == "medium"
    assert result["probabilities"] == [.05,.60,.35]


@pytest.mark.parametrize("p", [[1,0,0], [.2,.2,.2,.2], [-.1,.1,.2,.8], [float('nan'),0,0,1]])
def test_invalid_probabilities_rejected(p):
    with pytest.raises(ValueError):
        common_probabilities(p)


def test_machine_contract_matches_code():
    import json
    from pathlib import Path
    from quake.labels import VERSION, COMMON_CLASSES, XBD_TO_COMMON
    contract = json.loads((Path(__file__).resolve().parents[1] / "configs/label_contract.json").read_text())
    assert contract["version"] == VERSION
    assert contract["common_class_order"] == list(COMMON_CLASSES)
    assert contract["xbd_native_to_common"] == XBD_TO_COMMON
    assert contract["native_taxonomies_equivalent"] is False
    assert contract["active_external_dataset"] == "haitibrd_and_ebd_external_suite"
    assert contract["source_specific_reporting_required"] is True
    assert contract["haitibrd_original_palette_index_to_severity_code"]["1"] == 3
    assert contract["external_class_order"] == contract["native_training_class_order"]
    assert contract["external_probability_grouping_for_scoring"] is False
    from quake.ebd import mask_class_index
    assert contract["ebd_damage_mask_to_classifier"] == {str(i):mask_class_index(i) for i in range(5)}
