"""Mine WHY papers get rejected from real reviewer text (PeerRead / HF ICLR), then translate each reason
into a grant-proposal risk and check whether GrantDoctor' 10 hidden factors already cover it.

Method (explainable on purpose, no black box):
  1. split every review into sentences;
  2. a sentence counts as a *criticism of reason R* if it matches R's pattern AND contains a negative cue;
  3. per paper: reason R is "raised" if any review of that paper has such a sentence;
  4. compare the share of rejected vs accepted papers raising R (lift + two-proportion z-test, Bonferroni).
Limit: keyword rules measure what reviewers talk about, not why the committee decided. Treat as evidence, not proof.
"""
import math
import re

import pandas as pd

NEG = re.compile(r"\b(lack\w*|not|no|n't|without|missing|insufficient|limited|unclear|weak\w*|poor\w*|fail\w*|only|"
                 r"unconvincing|unsupported|too|hard|difficult|concern\w*|doubt\w*|incremental|marginal|toy|minor|"
                 r"confus\w*|vague|unfair|questionable|not\s+clear)\b", re.I)

# reason -> (regex, covered_by hidden factor or None, grant analogue, suggested fix)
TAXONOMY = {
    "novelty": (r"novel|originalit|incremental|already (been )?(proposed|known|studied)|prior work|similar to",
                "duplicate_overlap", "Overlaps with already funded work / unclear what is new",
                "State in one sentence what no funded project has done; cite the nearest approved projects."),
    "baselines_comparison": (r"baseline|compar(e|ed|ison)|state[- ]of[- ]the[- ]art|sota|benchmark",
                             None, "No comparison with the current practice or existing solution",
                             "Add a baseline: what is done today, what it achieves, and the target improvement over it."),
    "evaluation_evidence": (r"experiment|evaluat|empirical|results|dataset|evidence",
                            "data_sample_unclear", "Weak evidence plan: sample, data, evaluation criteria",
                            "Give sample size, data source, and the metric that decides success."),
    "clarity_writing": (r"unclear|clarity|poorly (written|organi[sz]ed)|hard to (follow|understand)|confus|writing|not (well )?(explained|motivated)",
                        None, "Proposal hard to follow: structure, language, undefined terms",
                        "One-page summary first, define terms, objectives numbered, have a non-expert read it."),
    "justification_rigor": (r"theor|proof|justif|rigor|principled|motivat|assumption|why (does|is|should)",
                            None, "Problem and approach not justified (why this method, why now)",
                            "Add a short problem-justification section with evidence of the need in Pakistan."),
    "significance_impact": (r"significan|impact|importance|marginal|contribution|usefulness|interesting",
                            "priority_alignment", "Impact or national-priority link not convincing",
                            "Name the beneficiary, the priority theme, and a measurable outcome."),
    "reproducibility_details": (r"reproduc|implementation detail|hyper-?parameter|missing detail|released?|open[- ]source|code",
                                None, "No data-management / open-data / reproducibility plan",
                                "Add a data management plan: what is shared, where, in what format, after how long."),
    "overclaiming": (r"over-?claim|too strong|not supported|unsupported|claims? (that|are)|conclusion",
                     None, "Claims larger than the budget, time or method can deliver",
                     "Match each claim to a work package; drop outcomes you cannot measure within the duration."),
    "scale_generality": (r"toy|small[- ]scale|simple (task|dataset|setting)|generali[sz]|scal(e|ab)",
                         "timeline_unrealistic", "Pilot-scale evidence for a large-scale promise",
                         "Show a pilot result or a staged plan (pilot -> scale-up) with a go/no-go point."),
    "related_work": (r"related work|literature|citation|missing reference|survey|references?",
                     None, "Literature review thin or missing local/prior-funded work",
                     "Cite previous HEC/PSF-funded work in the area and the gap it leaves."),
    "analysis_risk": (r"ablation|analysis|insight|understand why|failure case|limitation",
                      None, "No risk analysis, limitations or contingency plan",
                      "Add a risk table: top 3 risks, likelihood, mitigation, fallback deliverable."),
}
_COMPILED = {k: re.compile(v[0], re.I) for k, v in TAXONOMY.items()}
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


def reasons_in(text: str) -> set[str]:
    hit = set()
    for s in _SENT.split(text or ""):
        if len(s) < 20 or not NEG.search(s):
            continue
        for k, rx in _COMPILED.items():
            if rx.search(s):
                hit.add(k)
    return hit


def _ztest(x1, n1, x2, n2) -> tuple[float, float]:
    if min(n1, n2) == 0:
        return 0.0, 1.0
    p1, p2, p = x1 / n1, x2 / n2, (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0
    z = (p1 - p2) / se
    return z, math.erfc(abs(z) / math.sqrt(2))


def mine_reasons(df: pd.DataFrame) -> pd.DataFrame:
    """df needs: status, review_text (+ optional meta_review). Only papers that HAVE review text are used."""
    d = df[df["review_text"].fillna("").str.len() > 40].copy()
    d["_blob"] = d["review_text"].fillna("") + "\n" + d.get("meta_review", pd.Series("", index=d.index)).fillna("")
    d["_hit"] = d["_blob"].map(reasons_in)
    rej, acc = d[d["status"] == "rejected"], d[d["status"] == "approved"]
    rows = []
    for k, (_, cov, analog, fix) in TAXONOMY.items():
        x1, x2 = sum(k in h for h in rej["_hit"]), sum(k in h for h in acc["_hit"])
        n1, n2 = len(rej), len(acc)
        r1, r2 = (x1 / n1 if n1 else 0), (x2 / n2 if n2 else 0)
        z, p = _ztest(x1, n1, x2, n2)
        rows.append({"reason": k, "n_rejected": n1, "n_accepted": n2,
                     "rate_rejected": round(r1, 3), "rate_accepted": round(r2, 3),
                     "lift": round(r1 / r2, 2) if r2 else None, "z": round(z, 2), "p_value": round(p, 4),
                     "significant_bonferroni": p < 0.05 / len(TAXONOMY),
                     "covered_by_hidden_factor": cov or "NONE", "grant_analogue": analog, "suggested_fix": fix})
    out = pd.DataFrame(rows).sort_values("z", ascending=False).reset_index(drop=True)
    out["not_addressed_by_grantdoctor"] = (out["covered_by_hidden_factor"] == "NONE") & (out["z"] > 0)
    return out


def unaddressed(table: pd.DataFrame, min_rate: float = 0.15, alpha: float = 0.05) -> pd.DataFrame:
    """Reasons raised significantly more for rejected papers (p < alpha, uncorrected) that none of the 10 hidden factors checks."""
    return table[table["not_addressed_by_grantdoctor"] & (table["rate_rejected"] >= min_rate) & (table["p_value"] < alpha)]


def peer_review_frame(projects: pd.DataFrame) -> pd.DataFrame:
    if "corpus" not in projects.columns or "review_text" not in projects.columns:
        return pd.DataFrame(columns=["status", "review_text"])
    return projects[projects["corpus"] == "peer_review"]
