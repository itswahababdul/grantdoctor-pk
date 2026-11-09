"""Data & ethics: five short cards. Static text, so nothing here comes from user data."""
from src.app import ui

ui.page_header("Data & ethics", "What this system can and cannot claim")

ui.grid([
    ui.card("Approved library", [
        "Public HEC/PSF funded-project listings only.",
        "Scrapers check robots.txt and respect site terms."],
        badge=("Public data", "success"), tone="success"),
    ui.card("Rejected library", [
        "Rejected proposals are not public. This library is built from anonymized proposals shared with permission, "
        "and/or synthetic rejected records made by controlled degradation of approved proposals "
        "(inflated budget, vague objectives, missing ethics, short timeline).",
        "Synthetic records are always labelled."],
        badge=("Not public", "warning"), tone="warning"),
    ui.card("Official HEC check", [
        "Hard eligibility rules, required content and preferences come from HEC NRPU documents, each with its source "
        "(see HEC rules & sources).",
        "PSF rules are not yet included."],
        badge=("Sourced", "info"), tone="info"),
    ui.card("Risk score", [
        "Ten rule-based, explainable factors combined with fixed weights. Some are backed by HEC documents, others are "
        "general heuristics (labelled).",
        "It highlights possible weaknesses and is not a prediction of any real HEC/PSF decision. "
        "HEC's internal scoring weights are not public."],
        badge=("Heuristic", "teal"), tone="teal"),
    ui.card("Limitations", [
        "Small or sample data gives optimistic metrics; reviewer scores and confidential reasons are not available.",
        "Answers are generated only from retrieved passages with citations. If evidence is missing the system says so, "
        "and a grounding score estimates how much of an answer is supported by the retrieved text."],
        badge=("Read first", "danger"), tone="danger"),
])
