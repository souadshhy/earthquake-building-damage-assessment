import numpy as np
import pytest
from quake.ebd import mask_class_index, extract_regions, alignment_check


def test_four_class_encoding_preserves_minor_major_errors():
    assert [mask_class_index(v) for v in (0,1,2,3,4)] == [None,0,1,2,3]
    assert mask_class_index(2) != mask_class_index(3)
    with pytest.raises(ValueError):
        mask_class_index(255)


def test_reference_region_rules_do_not_invent_majority_labels():
    localization = np.zeros((32,32), dtype=np.uint8)
    severity = np.zeros_like(localization)
    localization[4:10,4:10] = 255
    severity[4:10,4:10] = 2
    eligible, excluded = extract_regions(localization, severity)
    assert len(eligible) == 1 and not excluded
    assert eligible[0]["class_index"] == 1
    severity[4,4] = 3
    eligible, excluded = extract_regions(localization, severity)
    assert not eligible
    assert "mixed_or_missing_damage_class" in excluded[0]["reasons"]


def test_border_and_uncovered_regions_are_logged():
    localization = np.zeros((32,32), dtype=np.uint8)
    severity = np.zeros_like(localization)
    localization[:6,:6] = 255
    severity[:6,:6] = 4
    eligible, excluded = extract_regions(localization, severity)
    assert not eligible and "border_truncated_region" in excluded[0]["reasons"]
    localization[:] = 0
    localization[10:16,10:16] = 255
    severity[:] = 0
    eligible, excluded = extract_regions(localization, severity)
    assert not eligible
    assert "localization_damage_coverage_below_0_95" in excluded[0]["reasons"]


def test_no_features_is_inconclusive_not_verified():
    empty = (np.empty((0,2),dtype=np.float32), None)
    assert alignment_check(empty, empty)["status"] == "inconclusive"


def test_minor_major_error_stays_an_error_in_external_scoring():
    from quake.metrics import classification_metrics
    result = classification_metrics([mask_class_index(2)], [mask_class_index(3)])
    assert result["confusion_matrix"][1][2] == 1
    assert sum(result["confusion_matrix"][c][c] for c in range(4)) == 0


def test_display_mapping_is_not_used_as_external_reference():
    from quake.labels import common_label
    assert common_label("ebd", 0) is None
    assert [common_label("ebd", v) for v in (1,2,3,4)] == [0,1,1,2]
    assert [mask_class_index(v) for v in (1,2,3,4)] == [0,1,2,3]
