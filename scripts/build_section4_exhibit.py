"""Make a compact one-page layout proof and a five-run prospective batch.

Only completed run artifacts supply observed cells. Pending runs are shaded,
never assigned zero counts or dashes. Full audit crosswalk remains separate.
"""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern.config import RunConfig
from discern.core import DEFAULT_POOL
from discern.validation import sha256


def build(crosswalk_dir, portable_config, out):
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    source, out = Path(crosswalk_dir).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    with (source / "combined_table.csv").open(encoding="utf-8", newline="") as stream:
        table = list(csv.DictReader(stream))
    with (source / "runs.csv").open(newline="") as stream:
        old_runs = {r["run_id"]: r for r in csv.DictReader(stream)}
    cfg = RunConfig(**json.loads(Path(portable_config).read_text()))
    columns = [("ARCHIVE", "Main run"), ("R01", "Repeat"), ("E_DEFAULTS", "Defaults"),
               ("E_OPENAI", "OpenAI only"), ("P01", "Placebo 1"), ("P02", "Placebo 2")]
    jobs = [
        ("R01", {"discovery_seed": 1001}),
        ("E_DEFAULTS", {"discovery_models": list(DEFAULT_POOL), "rotation_pool": list(DEFAULT_POOL)}),
        ("E_OPENAI", {"discovery_models": ["gpt-4o-mini", "gpt-4.1-mini"],
                      "rotation_pool": ["gpt-4o-mini", "gpt-4.1-mini"]}),
        ("P01", {"condition": "placebo", "run_index": 0}),
        ("P02", {"condition": "placebo", "run_index": 1}),
    ]
    recipes = []
    for rid, overrides in jobs:
        run = RunConfig(**{**asdict(cfg), **overrides,
                           "output_dir": f"/private/tmp/discern-section4-compact-runs/{rid}"})
        run.validate()
        path = out / f"{rid}.config.json"
        path.write_text(json.dumps(asdict(run), indent=2) + "\n")
        recipes.append({"run_id": rid, "config_path": str(path), "sha256": sha256(path),
                        "condition": run.condition, "status": "planned_live_run"})

    # Main-paper anchors are every substantive family validated in the archived
    # main run; no selection based on later stability or placebo outcomes.
    features = [row for row in table if row["ARCHIVE"] == "✓"]
    if len(features) > 14:
        raise ValueError("review layout rather than silently truncate the anchor set")
    count_keys = ["n_proposed", "n_validated", "n_suggestive", "n_families"]
    counts = [next(row for row in table if row["family_id"] == key) for key in count_keys]
    compact = []
    for row in counts + features:
        record = {"feature": row["substantive_family"]}
        for rid, label in columns:
            # Only archived observed results exist in the source at this stage.
            complete = rid in old_runs and old_runs[rid]["status"] == "complete"
            record[label] = row.get(rid, "") if complete else "PENDING"
        compact.append(record)
    with (out / "main_table_layout.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(compact[0]))
        writer.writeheader()
        writer.writerows(compact)

    pdf_path = out / "table_4_crosswalk_layout.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=(612, 792))
    c.setTitle("Section 4 compact crosswalk - layout proof")
    c.setAuthor("Discern paper validation")
    x, width = 43, 526
    label_width = 226
    cell_width = (width - label_width) / 6
    ink, muted = colors.HexColor("#202020"), colors.HexColor("#707070")
    c.setFillColor(ink)
    c.setFont("Times-Bold", 14)
    c.drawString(x, 739, "Table X. Feature stability and placebo validation")
    c.setFont("Times-Roman", 10)
    c.drawString(x, 721, "Women versus men within tall hierarchies")
    c.setFillColor(muted)
    c.setFont("Helvetica", 8)
    c.drawString(x, 701, "LAYOUT PROOF  |  Main run observed; five prospective runs pending")
    top, bottom = 676, 676 - 73 - 4 * 23 - len(features) * 29
    # Shade prospective columns so blanks cannot be mistaken for null findings.
    c.setFillColor(colors.HexColor("#f2f2f2"))
    c.rect(x + label_width + cell_width, bottom, cell_width * 5, top - bottom, stroke=0, fill=1)

    def rule(y, weight=.45):
        c.setStrokeColor(ink)
        c.setLineWidth(weight)
        c.line(x, y, x + width, y)

    rule(top, .9)
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + label_width + 2 * cell_width, top - 16, "REAL CONTRAST")
    c.drawCentredString(x + label_width + 5 * cell_width, top - 16, "LABEL PLACEBOS")
    c.setFont("Times-Bold", 9)
    c.drawString(x + 3, top - 43, "Substantive feature family")
    for i, (_, label) in enumerate(columns):
        center = x + label_width + (i + .5) * cell_width
        label_lines = [label] if label != "OpenAI only" else ["OpenAI", "only"]
        for j, line in enumerate(label_lines):
            c.drawCentredString(center, top - 35 - j * 11, line)
        if i:
            c.setFont("Helvetica", 6.7)
            c.setFillColor(muted)
            c.drawCentredString(center, top - 62, "pending")
            c.setFont("Times-Bold", 9)
            c.setFillColor(ink)
    y = top - 73
    rule(y)
    labels = ["Candidate features suggested", "Candidate features validated", "Suggestive only", "Validated feature families"]
    for record, label in zip(compact[:4], labels):
        c.setFont("Times-Roman", 9.2)
        c.drawString(x + 3, y - 15, label)
        c.setFont("Times-Bold", 10)
        c.drawCentredString(x + label_width + .5 * cell_width, y - 15, record["Main run"])
        y -= 23
    rule(y)
    style = ParagraphStyle("feature", fontName="Times-Roman", fontSize=9.5, leading=11.1, textColor=ink)

    def check(cx, cy):
        c.setStrokeColor(ink)
        c.setLineWidth(1.15)
        p = c.beginPath()
        p.moveTo(cx - 4, cy)
        p.lineTo(cx - 1, cy - 3)
        p.lineTo(cx + 5, cy + 5)
        c.drawPath(p)

    for row in features:
        paragraph = Paragraph(row["substantive_family"], style)
        _, h = paragraph.wrap(label_width - 12, 27)
        paragraph.drawOn(c, x + 3, y - 14 - h / 2)
        check(x + label_width + .5 * cell_width, y - 14)
        y -= 29
        c.setStrokeColor(colors.HexColor("#dcdcdc"))
        c.setLineWidth(.3)
        c.line(x, y, x + width, y)
    rule(y, .9)
    note_style = ParagraphStyle("note", fontName="Times-Roman", fontSize=8.1, leading=10.4, textColor=ink)
    notes = [
        "<b>Reading the final table.</b> A check indicates that a substantively matched feature family "
        "contains a validated candidate (5% FDR); a dash will indicate no validated member. "
        "The shaded cells are pending results, not zeros or absences.",
        "<b>Counts and matching.</b> The main run proposed and measured 35 candidates; 11 validated. "
        "Those 11 candidates occupy 10 draft substantive families because two management features "
        "are grouped together. Family alignment requires review. All anchor families are retained.",
        "<b>Prospective comparison.</b> Repeat keeps the reference settings and changes discovery seed. "
        "Defaults and OpenAI-only change the discovery and measurement pools together. Placebo 1 and 2 "
        "will rerun the full pipeline under shuffled labels. New validated families, including any "
        "placebo-only family, must be reported in the completed table or its linked appendix.",
        "<b>Already completed.</b> The separate 100-shuffle fixed-measurement pilot had at least one "
        "validated feature in 1/100 shuffles (Wilson 95% interval: 0.2%-5.4%). It is a conditional "
        "selection diagnostic; it does not fill the full-pipeline placebo columns above.",
    ]
    y -= 14
    for note in notes:
        p = Paragraph(note, note_style)
        _, h = p.wrap(width, 100)
        p.drawOn(c, x, y - h)
        y -= h + 7
    if y < 35:
        raise ValueError("layout overflow; review before delivery")
    c.save()

    metadata = {"status": "layout proof; not a completed multi-run exhibit", "api_calls": 0,
                "reference_crosswalk_sha256": sha256(source / "combined_table.csv"),
                "script_sha256": sha256(__file__), "main_run_validated_candidates": 11,
                "draft_anchor_families": len(features), "planned_jobs": recipes,
                "paper_design": "four real columns, two full-pipeline placebo columns",
                "appendix": "full run grid and newly appearing families; retain any placebo survivor",
                "key_configuration": "~/.config/discern/.env; credentials are never copied with exhibits"}
    (out / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (out / "README.txt").write_text(
        "Section 4 exhibit layout proof\n\n"
        "table_4_crosswalk_layout.pdf is a one-page visual proof based on the AOM crosswalk layout.\n"
        "Only the main-run results are observed. Shaded columns await new full-pipeline runs.\n"
        "The archived main run has 35 proposed/measured candidates and 11 validated candidates.\n"
        "The ten displayed families group two validated management features together provisionally.\n\n"
        "The compact batch has five prospective jobs: repeat, current defaults, OpenAI only, two placebos.\n"
        "The larger 38-column grid is an appendix planning file, not an evidence exhibit.\n"
        "No completed-run outputs are overwritten by this layout proof.\n", encoding="utf-8")
    print(pdf_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosswalk-dir", required=True)
    parser.add_argument("--portable-config", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    build(args.crosswalk_dir, args.portable_config, args.out)
