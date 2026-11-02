import torch
from quake.detector import PreEventBranch
from quake.vendor.microsoft_siam_unet import SiamUnet


def test_pre_event_adapter_matches_upstream_branch_without_training():
    torch.set_num_threads(2)
    torch.manual_seed(42)
    base = SiamUnet(init_features=2).eval()
    branch = PreEventBranch(base).eval()
    image = torch.randn(1, 3, 32, 32)
    before = {k: v.clone() for k, v in base.state_dict().items()}
    with torch.inference_mode():
        expected = base(image, image)[0]
        actual = branch(image)
    torch.testing.assert_close(actual, expected)
    assert all(torch.equal(v, before[k]) for k, v in base.state_dict().items())
