"""Build a populated compact paper crosswalk plus its complete audit appendix.

Run counts come directly from saved artifacts. Semantic mappings remain draft.
The main panel anchors on the archived validated families and always includes
any placebo survivor; other recurring/new families remain visible in the appendix.
"""
import argparse
import csv
from html import escape
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from discern.stability import presence_table, crosswalk
from discern.validation import sha256


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(anchors, batch, matches, out, artifacts=None):
    anchors, matches, out = Path(anchors).resolve(), Path(matches).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with (anchors / "runs.csv").open() as stream:
        archive = next(r for r in csv.DictReader(stream) if r["run_id"] == "ARCHIVE")
    with (anchors / "family_memberships.csv").open() as stream:
        members = list(csv.DictReader(stream))
    jobs = json.loads(Path(batch).read_text())["planned_jobs"]
    runs = [{**archive, "condition": "real"}]
    family_names = {m["family_id"]: m["family_label"] for m in members}
    novel = json.loads((matches / "novel_groups.json").read_text())
    novel_lookup = {}
    for i, group in enumerate(novel["groups"], 1):
        for node in group["members"]:
            origin = novel["origin"][node]
            novel_lookup[(origin["run_id"], origin["candidate_id"])] = (f"NF{i:03}", group["family_label"])
    for job in jobs:
        rid = job["run_id"]
        cfg = json.loads(Path(job["config_path"]).read_text())
        root = Path(artifacts).resolve() / rid if artifacts else Path(cfg["output_dir"]) / rid
        if not (root / "04_selected.json").exists():
            raise ValueError(f"{rid}: no completed selection artifact; refusing to fabricate a result")
        mapping = json.loads((matches / f"{rid}.json").read_text())
        if mapping["candidate_bank_sha256"] != sha256(root / "02_consolidated.json"):
            raise ValueError(f"{rid}: matching bank hash differs")
        runs.append({"run_id": rid, "status": "complete", "artifact_path": str(root),
                     "condition": cfg["condition"], "config_path": job["config_path"]})
        for match in mapping["matches"]:
            fid, new_label = ((match["family_id"], match["family_label"]) if match["family_id"]
                              else novel_lookup[(rid, match["candidate_id"])])
            label = family_names.setdefault(fid, new_label)
            members.append({"family_id": fid, "family_label": label, "run_id": rid,
                            "candidate_id": match["candidate_id"],
                            "relation": match["relation"] if match["family_id"] else "anchor",
                            "orientation": match.get("orientation", "same"),
                            "rationale": match.get("rationale", ""),
                            "mapping_status": "draft"})

    full = presence_table(runs, members)
    ids = [run["run_id"] for run in runs]
    count_rows = [r for r in full if r["family_id"].startswith("n_")]
    features = [r for r in full if not r["family_id"].startswith("n_")]
    main_ids = {r["family_id"] for r in features if r["ARCHIVE"] == "✓"}
    placebo_ids = {r["family_id"] for r in features if any(r[rid] == "✓" for rid in ["P01", "P02"])}
    displayed = [r for r in features if r["family_id"] in main_ids | placebo_ids]
    if len(displayed) > 20:
        raise ValueError("more than 20 necessary rows; review layout rather than silently omit survivors")
    additional = {"family_id": "additional", "substantive_family": "Additional validated families (appendix)"}
    for rid in ids:
        additional[rid] = sum(r[rid] == "✓" and r["family_id"] not in main_ids | placebo_ids for r in features)
    main = count_rows + displayed + [additional]
    write_csv(out / "table_4_crosswalk.csv", main)
    write_csv(out / "appendix_full_crosswalk.csv", full)
    write_csv(out / "appendix_proposed_features.csv", presence_table(runs, members, stage="proposed"))
    write_csv(out / "appendix_feature_details.csv", crosswalk(runs, members))
    # Preserve all decisions behind a family check, with full candidate text and estimates.
    detail = []
    for run in runs:
        root, rid = Path(run["artifact_path"]), run["run_id"]
        bank = {c["candidate_id"]: c for c in json.loads((root / "02_consolidated.json").read_text())["candidates"]}
        result = {r["candidate_id"]: r for r in json.loads((root / "04_selected.json").read_text())["results"]}
        for m in [member for member in members if member["run_id"] == rid]:
            c, r = bank[m["candidate_id"]], result.get(m["candidate_id"])
            detail.append({**m, "orientation": m.get("orientation", "same"),
                           "rationale": m.get("rationale", "Reference family anchor"),
                           "feature_name": c["feature_name"], "definition": c["definition"],
                           "classification_question": c["classification_question"],
                           "tier": r["tier"] if r else "unmeasurable",
                           "mean_effect": r["mean_effect"] if r else "",
                           "perm_p": r["perm_p"] if r else ""})
    write_csv(out / "feature_memberships_for_review.csv", detail)
    # A separate randomized form can be shared with raters without exposing run
    # identities, model families, validation tiers, effects or proposed matches.
    order = np.random.default_rng(260026).permutation(len(detail))
    blinded, key = [], {}
    for i, index in enumerate(order, 1):
        item, opaque = detail[index], f"I{i:03}"
        blinded.append({"item_id": opaque, "feature_name": item["feature_name"],
                        "definition": item["definition"], "classification_question": item["classification_question"],
                        "rater1_family": "", "rater1_relation": "", "rater2_family": "", "rater2_relation": ""})
        key[opaque] = {"run_id": item["run_id"], "candidate_id": item["candidate_id"]}
    write_csv(out / "blinded_matching_review.csv", blinded)
    (out / "blinded_matching_key.json").write_text(json.dumps(key, indent=2) + "\n")

    labels = {"ARCHIVE": "Main run", "R01": "Repeat", "E_DEFAULTS": "Default pool",
              "E_OPENAI": "OpenAI only", "P01": "Placebo 1", "P02": "Placebo 2"}
    notes = (
        "Checks indicate at least one member of a substantive family validated at 5% FDR; dashes indicate none. "
        "Counts are candidate counts except rows explicitly labeled families. A candidate may have different "
        "wording or breadth across runs. Semantic alignment is an automated draft requiring review. "
        "All main-run validated families and any validated placebo-only families are displayed. Additional "
        "validated families and all proposed features are in the appendix. Repeat changes the discovery "
        "seed with the same data partition and reference pool; Default pool and OpenAI-only change both "
        "discovery and measurement pools while keeping sample size and other settings fixed. Both placebos regenerate candidates and measurements under "
        "permuted labels using the reference pool. Two placebos are illustrative, not a precise "
        "calibration estimate. Each run reserves 800 evaluation responses (400 per active label).")
    count_names = {"n_proposed": "Features proposed", "n_measured": "Features measured",
                   "n_validated": "Features validated (5% FDR)", "n_suggestive": "Suggestive only (10% FDR)",
                   "n_families": "Validated feature families"}
    short_names = {
        "Emphasis on Bureaucracy and Inefficiency": "Bureaucracy and inefficiency",
        "Reference to Positive Organizational Culture or Values": "Positive organizational culture / values",
        "References to Management Competence or Dysfunction": "Management quality / dysfunction",
        "Reference to Specific Negative Consequences": "Specific negative consequences",
        "Positive Framing of Management Layers": "Benefits of management layers",
        "References to Superfluous or Redundant Positions": "Redundant management positions",
        "Focus on Communication Barriers": "Communication barriers",
        "Emotional Intensity or Valence": "Emotional intensity / valence",
        "References to Hierarchy and Power Dynamics": "Hierarchy and power",
        "Reference to Negative Office Politics or Distrust": "Office politics / distrust",
    }

    def display_name(row):
        return count_names.get(row["family_id"], short_names.get(row["substantive_family"], row["substantive_family"]))

    def html_table(rows):
        header = "<tr><th>Substantive feature family</th>" + "".join(f"<th>{escape(labels[rid])}</th>" for rid in ids) + "</tr>"
        body = []
        for row in rows:
            name = display_name(row)
            style = ' class="count"' if row["family_id"].startswith("n_") else ""
            cells = []
            for rid in ids:
                matching = [d for d in detail if d["run_id"] == rid and d["family_id"] == row["family_id"]]
                tooltip = "\n\n".join(f"{d['feature_name']} [{d['tier']}]\n{d['definition']}\n{d['classification_question']}" for d in matching)
                cells.append(f'<td title="{escape(tooltip, quote=True)}">{escape(str(row[rid]))}</td>')
            body.append(f"<tr{style}><th>{escape(name)}</th>{''.join(cells)}</tr>")
        return "<table><thead>" + header + "</thead><tbody>" + "".join(body) + "</tbody></table>"
    html = ("<!doctype html><html><head><meta charset='utf-8'><title>Section 4 crosswalk</title>"
            "<style>body{font:16px Georgia,serif;color:#222;background:#f1f1ef;margin:0;padding:40px}"
            "main{max-width:1100px;margin:auto;background:white;padding:40px}h1{font-size:26px}"
            "h2{font-size:20px;margin-top:34px}.status{font:13px Arial;color:#666}"
            "table{border-collapse:collapse;width:100%;font-size:14px;border-top:2px solid #222;border-bottom:2px solid #222}"
            "th,td{padding:10px 9px;border-bottom:1px solid #ddd;text-align:center}"
            "th:first-child{text-align:left;width:42%;font-weight:400}thead th{font:600 13px Arial;background:#f5f5f3}"
            ".count{background:#fafaf8}.count td{font-weight:bold}.notes{font-size:12px;line-height:1.5}"
            "td:hover{background:#ecf0ef}summary{cursor:pointer;font:16px Arial;margin:25px 0}"
            "@media print{body{padding:0;background:white}main{padding:0}details{display:none}}</style></head><body><main>"
            "<h1>Feature stability and placebo validation</h1><p>Women versus men within tall hierarchies</p>"
            "<p class='status'>COMPLETED PILOT RUNS · Draft substantive matching · Hover cells for original features</p>" +
            html_table(main) + "<p class='notes'>" + escape(notes) + "</p>"
            "<details><summary>Full feature-family crosswalk and counts</summary>" + html_table(full) + "</details>"
            "</main></body></html>")
    (out / "table_4_crosswalk.html").write_text(html, encoding="utf-8")

    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph
    c = canvas.Canvas(str(out / "table_4_crosswalk.pdf"), pagesize=(612, 792))
    c.setTitle("Feature stability and placebo validation - completed pilot runs")
    x, width, label_width = 43, 526, 226
    cell = (width - label_width)/6
    ink = colors.HexColor("#222222")
    c.setFillColor(ink)
    c.setFont("Times-Bold", 14)
    c.drawString(x, 739, "Table X. Feature stability and placebo validation")
    c.setFont("Times-Roman", 10)
    c.drawString(x, 721, "Women versus men within tall hierarchies")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#666666"))
    c.drawString(x, 701, "COMPLETED PILOT RUNS  |  Draft substantive feature alignment")
    top, y = 677, 615

    def rule(ypos, weight=.5):
        c.setStrokeColor(ink);c.setLineWidth(weight);c.line(x,ypos,x+width,ypos)
    rule(top, .9)
    c.setFillColor(ink);c.setFont("Helvetica-Bold",8)
    c.drawCentredString(x+label_width+2*cell,top-15,"REAL CONTRAST")
    c.drawCentredString(x+label_width+5*cell,top-15,"LABEL PLACEBOS")
    c.setFont("Times-Bold",9)
    c.drawString(x+3,top-40,"Substantive feature family")
    for i,rid in enumerate(ids):
        center=x+label_width+(i+.5)*cell
        words=(["OpenAI","only"] if rid=="E_OPENAI" else
               ["Default","pool"] if rid=="E_DEFAULTS" else [labels[rid]])
        for j,word in enumerate(words):c.drawCentredString(center,top-34-j*11,word)
    rule(y)
    name_style=ParagraphStyle("name",fontName="Times-Roman",fontSize=9.3,leading=10.5,textColor=ink)
    row_height=min(27, (y-225-5*20-23)/max(1,len(displayed)))
    if row_height < 18:raise ValueError("too many rows for a legible one-page exhibit")

    def check(cx,cy):
        c.setStrokeColor(ink);c.setLineWidth(1.1)
        p=c.beginPath();p.moveTo(cx-3.5,cy);p.lineTo(cx-1,cy-3);p.lineTo(cx+5,cy+4.5);c.drawPath(p)
    for row in main:
        height=20 if row["family_id"].startswith("n_") else (23 if row["family_id"]=="additional" else row_height)
        name=display_name(row)
        p=Paragraph(escape(name),name_style);_,ph=p.wrap(label_width-10,height)
        p.drawOn(c,x+3,y-height/2-ph/2)
        for i,rid in enumerate(ids):
            center=x+label_width+(i+.5)*cell
            value=row[rid]
            if value=="✓":check(center,y-height/2)
            elif value=="–":
                c.setStrokeColor(colors.HexColor("#888888"));c.setLineWidth(.6)
                c.line(center-3,y-height/2,center+3,y-height/2)
            else:
                c.setFillColor(ink);c.setFont("Times-Bold" if row["family_id"].startswith("n_") else "Times-Roman",10)
                c.drawCentredString(center,y-height/2-3,str(value))
        y-=height
        c.setStrokeColor(colors.HexColor("#dedede"));c.setLineWidth(.3);c.line(x,y,x+width,y)
        if row["family_id"]=="n_families":rule(y)
    rule(y,.9)
    note_style=ParagraphStyle("notes",fontName="Times-Roman",fontSize=8.2,leading=10.6,textColor=ink)
    p=Paragraph("<b>Notes.</b> "+escape(notes),note_style);_,ph=p.wrap(width,200)
    p.drawOn(c,x,y-13-ph)
    if y-13-ph<40:raise ValueError("notes overflow; review layout")
    c.save()
    sources={r["run_id"]:{name:sha256(Path(r["artifact_path"])/name) for name in
                          ["00_config.json","00_partition.json","02_consolidated.json","03_measured.json","04_selected.json"]} for r in runs}
    metadata={"status":"completed_pilot_runs_with_draft_automated_semantic_matching", "runs":runs,
              "sources_sha256":sources,"script_sha256":sha256(__file__),
              "matching_sha256":{p.name:sha256(p) for p in matches.glob("*.json")},
              "main_anchor_family_ids":sorted(main_ids),"placebo_survivor_family_ids":sorted(placebo_ids),
              "main_rows":len(displayed),"all_feature_families":len(features),
              "display_rule":"All archived validated families and any placebo survivors; all other families in appendix with additional-family counts.",
              "notes":notes}
    (out/"manifest.json").write_text(json.dumps(metadata,indent=2)+"\n")
    (out/"README.txt").write_text("Completed engineering pilot crosswalk.\n\n"
        "table_4_crosswalk.pdf: compact one-page main exhibit.\n"
        "table_4_crosswalk.html: main table plus full expandable crosswalk, with feature tooltips.\n"
        "appendix_full_crosswalk.csv: every family and every completed run.\n"
        "feature_memberships_for_review.csv: underlying definitions, questions and draft matches.\n\n"+notes+"\n")
    print(json.dumps({"main_rows":len(displayed),"all_families":len(features),"out":str(out)},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchors",required=True)
    parser.add_argument("--batch",required=True)
    parser.add_argument("--matches",required=True)
    parser.add_argument("--out",required=True)
    parser.add_argument("--artifacts",help="archived completed-run root; defaults to each config's output path")
    args=parser.parse_args()
    build(args.anchors,args.batch,args.matches,args.out,args.artifacts)
