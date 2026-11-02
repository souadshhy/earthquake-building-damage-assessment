import pytest
from quake.external import external_metrics


def test_source_scores_remain_separate_and_combined_optional():
    rows=[{"dataset":"haitibrd"},{"dataset":"ebd_turkey"},{"dataset":"ebd_turkey"}]
    result=external_metrics(rows,[3,3,0],[3,0,0])
    assert "combined_supplementary" not in result
    assert result["per_source"]["haitibrd"]["support"]==1
    assert result["per_source"]["ebd_turkey"]["support"]==2
    pooled=external_metrics(rows,[3,3,0],[3,0,0],True)
    assert pooled["combined_supplementary"]["support"]==3
    assert pooled["combined_supplementary"]["confusion_matrix"][3][0]==1


def test_minor_to_major_is_wrong_in_each_source_and_pool():
    rows=[{"dataset":"haitibrd"},{"dataset":"ebd_turkey"}]
    result=external_metrics(rows,[1,1],[2,2],True)
    assert all(m["confusion_matrix"][1][2]==1 for m in result["per_source"].values())
    assert result["combined_supplementary"]["confusion_matrix"][1][2]==2


def test_external_scores_reject_missing_predictions():
    with pytest.raises(ValueError,match="lengths"):
        external_metrics([{"dataset":"haitibrd"}],[0],[])
