import pandas as pd

from src.analysis.review_reason_miner import mine_reasons, reasons_in, unaddressed
from src.ingestion.peerread_loader import _review_blob


def test_reasons_need_negative_cue():
    assert "baselines_comparison" in reasons_in("The paper lacks a comparison with a strong baseline method.")
    assert reasons_in("The baseline comparison is described in section three of the paper.") == set()


def test_review_blob_splits_meta():
    body, meta = _review_blob([{"comments": "good", "IS_META_REVIEW": "False"}, {"comments": "reject", "IS_META_REVIEW": "True"}])
    assert body == "good" and meta == "reject"


def test_mine_reasons_lift_and_gap():
    rej = ["The writing is unclear and the paper is hard to follow throughout the introduction."] * 8 + ["Fine paper overall, nothing to add here at all."] * 2
    acc = ["Fine paper overall, nothing to add here at all and it reads well."] * 9 + ["The writing is unclear in one section of this paper."]
    df = pd.DataFrame({"status": ["rejected"] * 10 + ["approved"] * 10, "review_text": rej + acc})
    t = mine_reasons(df).set_index("reason")
    assert t.loc["clarity_writing", "rate_rejected"] == 0.8 and t.loc["clarity_writing", "rate_accepted"] == 0.1
    assert t.loc["clarity_writing", "p_value"] < 0.05
    assert "clarity_writing" in set(unaddressed(t.reset_index())["reason"])


def test_peerread_loader_labels(tmp_path):
    import json
    from src.ingestion.peerread_loader import load_peerread
    d = tmp_path / "iclr_2017" / "train" / "reviews"; d.mkdir(parents=True)
    for i, acc in enumerate(["True", "False"]):
        (d / f"{i}.json").write_text(json.dumps({"id": str(i), "title": f"T{i}", "abstract": "x" * 60, "accepted": acc, "authors": "A",
                                                 "reviews": [{"comments": "Not novel.", "IS_META_REVIEW": "False", "RECOMMENDATION": "4"}]}))
    (tmp_path / "acl_2017" / "train" / "reviews").mkdir(parents=True)
    (tmp_path / "acl_2017" / "train" / "reviews" / "9.json").write_text(json.dumps({"id": "9", "accepted": None, "reviews": []}))
    recs = load_peerread(str(tmp_path))
    assert sorted(r["status"] for r in recs) == ["approved", "rejected"]   # unlabelled ACL skipped
    assert all(r["corpus"] == "peer_review" and r["avg_recommendation"] == 4 for r in recs)
