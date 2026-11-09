"""Generate PLACEHOLDER sample data so the whole pipeline runs end-to-end before real data is collected.
These records are fictional (ids start with SAMPLE-). Replace with real HEC/PSF data in data/raw/."""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    "Renewable Energy": ["solar panel efficiency", "wind turbine blades", "battery storage grid", "biomass energy"],
    "Agriculture": ["wheat yield drought", "cotton pest management", "soil salinity", "precision irrigation"],
    "Public Health": ["dengue vector surveillance", "maternal nutrition", "tuberculosis screening", "hospital waste"],
    "Water Resources": ["groundwater depletion", "canal seepage", "rainwater harvesting", "wastewater reuse"],
    "Artificial Intelligence": ["urdu language model", "crop disease detection", "traffic prediction", "fraud detection"],
    "Materials Science": ["nano coating corrosion", "graphene composite", "recycled concrete", "polymer membrane"],
}
ETHICS = "Ethical approval will be obtained from the institutional review board and informed consent will be collected."


def make():
    rng = random.Random(7)
    approved, golden = [], []
    for fi, (field, topics) in enumerate(FIELDS.items()):
        for ti, topic in enumerate(topics):
            for n in range(2):
                pid = f"SAMPLE-A-{fi}{ti}{n}"
                pilot = "This is a pilot study with a small-scale proof of concept. " if n == 0 and ti == 0 else ""
                approved.append({
                    "project_id": pid,
                    "title": f"{topic.title()} in Pakistan: phase {n+1}",
                    "abstract": (f"This project investigates {topic} to support national priorities in {field.lower()} and industry adoption. "
                                 f"{pilot}The dataset comprises 300 samples collected from partner sites across Punjab and Sindh. {ETHICS}"),
                    "objectives": f"1) Measure baseline {topic}; 2) Develop an improved approach; 3) Validate with stakeholders and publish two papers.",
                    "methodology": (f"We use a mixed-methods design with sample size n = 300, field trials and statistical analysis. "
                                    f"Milestones: prototype by month 12 and two publications. {ETHICS}"),
                    "budget": rng.uniform(4e6, 9e6), "duration_months": rng.choice([24, 36]),
                    "pi": f"Dr. Sample {fi}{ti}", "institute": "Sample University", "field": field,
                    "year": rng.choice([2021, 2022, 2023, 2024]), "funder": rng.choice(["HEC", "PSF"]),
                    "status": "approved", "source_url": "sample://placeholder", "language": "en",
                })
            golden.append({"query": f"{topic} project", "libs": ["approved"],
                           "relevant_ids": [f"SAMPLE-A-{fi}{ti}0", f"SAMPLE-A-{fi}{ti}1"]})
    out_dir = ROOT / "data" / "sample"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "approved.jsonl", "w", encoding="utf-8") as f:
        for r in approved:
            f.write(json.dumps(r) + "\n")
    with open(ROOT / "src" / "evaluation" / "golden_set.json", "w", encoding="utf-8") as f:
        json.dump(golden, f, indent=2)
    print(f"wrote {len(approved)} sample approved records and {len(golden)} golden queries")


if __name__ == "__main__":
    make()
