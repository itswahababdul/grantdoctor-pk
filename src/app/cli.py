"""CLI:  python -m src.app.cli sample | build | app | ask "question" | diagnose proposal.json | trends | eval"""
import argparse
import json
import shutil
import sys

from src.config import abs_path, load_config


def main(argv=None):
    ap = argparse.ArgumentParser(prog="grantdoctor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sample", help="generate placeholder sample data into data/raw")
    sub.add_parser("build", help="run the Spark pipeline and build both libraries")
    a = sub.add_parser("ask"); a.add_argument("question")
    d = sub.add_parser("diagnose"); d.add_argument("file")
    pr = sub.add_parser("peerread", help="import PeerRead (git clone allenai/PeerRead) into data/raw"); pr.add_argument("data_dir")
    pp = sub.add_parser("psf-pdf", help="import PSF completed-projects PDF into data/raw"); pp.add_argument("pdf")
    sub.add_parser("hf-iclr", help="import HF Vidushee/iclr-rejected-papers-with-code-1k (needs internet + `pip install datasets`)")
    sub.add_parser("reasons", help="print rejection-reason table + reasons GrantDoctor does not check yet")
    sub.add_parser("trends")
    sub.add_parser("eval")
    sub.add_parser("app", help="launch the web UI")
    args = ap.parse_args(argv)
    cfg = load_config()

    if args.cmd == "sample":
        from scripts.make_sample_data import make
        make()
        dst = abs_path(cfg["paths"]["raw_dir"]); dst.mkdir(parents=True, exist_ok=True)
        shutil.copy(abs_path("data/sample/approved.jsonl"), dst / "approved.jsonl")
        print("copied sample to data/raw/approved.jsonl")
    elif args.cmd == "peerread":
        from src.ingestion.peerread_loader import write_peerread
        print(write_peerread(args.data_dir, str(abs_path(cfg["paths"]["raw_dir"]))))
    elif args.cmd == "psf-pdf":
        from src.ingestion.psf_list_parser import write_psf
        print(write_psf(args.pdf, str(abs_path(cfg["paths"]["raw_dir"]))))
    elif args.cmd == "hf-iclr":
        from src.ingestion.hf_iclr_loader import write_hf_iclr
        print(write_hf_iclr(str(abs_path(cfg["paths"]["raw_dir"]))))
    elif args.cmd == "reasons":
        import pandas as pd
        from src.analysis.review_reason_miner import peer_review_frame, mine_reasons, unaddressed
        from src.services.library_service import load_projects
        t = mine_reasons(peer_review_frame(load_projects(cfg)))
        print(t[["reason", "rate_rejected", "rate_accepted", "lift", "p_value", "significant_bonferroni", "covered_by_hidden_factor"]].to_string(index=False))
        print("\nNOT checked by the 10 hidden factors yet:")
        for _, r in unaddressed(t).iterrows():
            print(f"- {r['reason']} ({r['rate_rejected']:.0%} of rejected papers): {r['grant_analogue']} -> {r['suggested_fix']}")
    elif args.cmd == "build":
        from src.pipeline import build
        print(build(cfg=cfg))
    elif args.cmd == "ask":
        from src.pipeline import answer
        r = answer(args.question, cfg)
        print(f"[libraries: {', '.join(r['libraries'])}]\n{r['answer']}")
    elif args.cmd == "diagnose":
        from src.analysis.improvement_suggester import suggest
        from src.analysis.rejection_diagnoser import diagnose
        from src.pipeline import load_runtime
        retriever, _, _, stats = load_runtime(cfg)
        proposal = json.load(open(args.file, encoding="utf-8"))
        rep = diagnose(proposal, retriever, stats, cfg["priority_keywords"])
        print(json.dumps({"overall_risk": rep["overall_risk"], "rubric": rep["rubric"]}, indent=2))
        for s in suggest(rep):
            print(f"- [{s['risk']:.2f}] {s['factor']}: {s['why']} -> {s['fix']}")
    elif args.cmd == "trends":
        import pandas as pd
        from src.analysis import approved_gap_analyzer as gap, trend_analytics_spark as tr
        from src.preprocessing.spark_session import get_spark
        spark = get_spark()
        df = spark.read.parquet(str(abs_path(cfg["paths"]["processed_dir"]) / "projects.parquet"))
        df = df.filter("corpus IS NULL OR corpus != 'peer_review'")   # grant analytics only
        tr.funding_by_year_funder(df).show(); gap.field_profile(df.filter("status='approved'")).show()
        gap.underfunded_fields(df.filter("status='approved'")).show(); gap.extension_candidates(df.filter("status='approved'")).show(truncate=60)
    elif args.cmd == "app":
        import subprocess
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(abs_path("src/app/streamlit_app.py"))])
    elif args.cmd == "eval":
        from src.evaluation.retrieval_metrics import ablation
        from src.pipeline import load_runtime
        _, emb, idxs, _ = load_runtime(cfg)
        golden = json.load(open(abs_path("src/evaluation/golden_set.json")))
        print(json.dumps(ablation(idxs, emb, golden), indent=2))


if __name__ == "__main__":
    sys.exit(main())
