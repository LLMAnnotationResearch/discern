"""Describe pooled themes without treating related candidate tests as replications.

This is an explicitly post hoc, analyst-authored exhibit. Saved candidate results
are never recomputed or relabeled. Candidate-level links remain inspectable.
"""
import argparse
import csv
import hashlib
from html import escape
import json
from pathlib import Path


RUNS = ["ARCHIVE", "R01", "E_DEFAULTS", "E_OPENAI", "P01", "P02"]
LABELS = ["Main run", "Repeat", "Default pool", "OpenAI only", "Placebo 1", "Placebo 2"]
THEMES = [
    ("T01", "Bureaucracy, inefficiency, and decision speed", "F01"),
    ("T02", "Rigidity, tradition, and adaptability", "NF001"),
    ("T03", "Layers, complexity, role clarity, and navigation", "F11 F16 F26 NF005"),
    ("T04", "Redundant or excessive management", "F06"),
    ("T05", "Communication and access to leadership", "F07"),
    ("T06", "Micromanagement, autonomy, and employee voice", "F12 F15 F20 F30"),
    ("T07", "Support, coordination, fairness, and employee care", "F02 F05 F21 NF003 NF007"),
    ("T08", "Career advancement and learning opportunities", "F23 F28 NF002"),
    ("T09", "Management competence and dysfunction", "F03 F31"),
    ("T10", "Power, office politics, and workplace culture", "F09 F10 F29 NF014"),
    ("T11", "Workload, stress, and employee experience", "F19 NF009 NF017"),
    ("T12", "Emotional, personal, and metaphorical framing", "F08 F24 F32 F33"),
    ("T13", "General organizational harms or benefits", "F04"),
    ("T14", "Balanced, conditional, or contextual evaluations", "F14 F22 F25"),
    ("T15", "Understanding or questioning the term 'tall'", "F17"),
    ("T16", "Preference for flatter structures", "NF015"),
    ("T17", "Organizational size, context, and maturity", "F27 NF012 NF018 NF020"),
    ("T18", "Recruitment, posting, and work preferences", "F13 F18 NF011 NF013"),
    ("T19", "Financial costs, pay, and performance", "NF006 NF008 NF016 NF019"),
    ("T20", "Gender and demographic management biases", "NF004"),
    ("T21", "Response length and elaboration", "NF010"),
]

# Links are semantic judgments based on definitions, not tests or effect sizes.
# Each exception lists ALL links, replacing its inherited family assignment.
# Composite links do not establish that the named component separately validated.
OVERRIDES = {
    ("ARCHIVE", "c_771c575c26ea664d"): [("T13", "focused", "Specific organizational harms"), ("T10", "composite", "Office politics is one example in an OR definition")],
    ("ARCHIVE", "c_03b786107cd0c1c8"): [("T10", "focused", "Workplace culture and interpersonal dynamics")],
    ("ARCHIVE", "c_f64ffd79a929e080"): [("T06", "composite", "Combines control and trust/fairness"), ("T07", "composite", "Combines trust/fairness and control")],
    ("R01", "c_7a1f74292a1cbf95"): [("T03", "composite", "Manageability/navigation combined with advancement"), ("T08", "composite", "Clear advancement paths are an explicit alternative")],
    ("R01", "c_6f30511278475cfd"): [("T07", "composite", "Workload distribution combined with departmentalization"), ("T03", "composite", "Departmental segmentation combined with workload distribution")],
    ("R01", "c_48a7eb1fdc699ab4"): [("T10", "focused", "Protection from office politics, with positive polarity")],
    ("E_DEFAULTS", "c_fefcb403886d7375"): [("T07", "focused", "Teamwork, collaboration, and management support")],
    ("E_DEFAULTS", "c_6dab6591d616fc79"): [("T01", "composite", "Decision speed/bottlenecks combined with adaptability"), ("T02", "composite", "Adaptability combined with decision speed/bottlenecks")],
    ("E_DEFAULTS", "c_093633dc7210d7f6"): [("T06", "composite", "Empowerment combined with trust, fairness, and advancement"), ("T07", "composite", "Trust/fairness combined with empowerment and advancement"), ("T08", "composite", "Merit-based advancement is an explicit alternative")],
    ("E_DEFAULTS", "c_e2ff40de1c305d99"): [("T06", "composite", "Micromanagement combined with delegation/distributed responsibility"), ("T07", "composite", "Delegation/distributed responsibility combined with micromanagement")],
    ("E_DEFAULTS", "c_4df566a316d10c63"): [("T11", "focused", "Employee work costs, including stress and managing managers"), ("T06", "composite", "Lack of autonomy is one example in a broad employee-cost question")],
    ("E_DEFAULTS", "c_315e0f19c76db5bc"): [("T13", "focused", "Broad negative organizational outcomes"), ("T09", "composite", "Dysfunction is one example among multiple outcomes"), ("T04", "composite", "Redundancy is one example among multiple outcomes"), ("T10", "composite", "Power dynamics is one example among multiple outcomes"), ("T03", "composite", "Confusion is one example among multiple outcomes")],
    ("E_DEFAULTS", "c_093a902907008169"): [("T18", "composite", "Remote work is combined with autonomy"), ("T06", "composite", "Autonomy is combined with remote work")],
    ("E_OPENAI", "c_94c409e8ed30c7cc"): [("T13", "composite", "Positive assessment combined with balanced pros and cons"), ("T14", "composite", "Balanced views combined with general positivity"), ("T07", "composite", "Supportiveness/fairness are examples in a broad OR question"), ("T08", "composite", "Opportunity/growth are examples in a broad OR question"), ("T03", "composite", "Structure/clarity are examples in a broad OR question")],
    ("E_OPENAI", "c_d29954f82edfd783"): [("T07", "focused", "Teamwork and collaboration"), ("T06", "composite", "Diversity of input is an alternative to teamwork")],
    ("P01", "c_6752b6e3ec2778ba"): [("T02", "focused", "Rigidity/inflexibility; corrects a narrow reference-family allocation")],
    ("P01", "c_cd0d7d9b82201392"): [("T06", "composite", "Autonomy combined with productivity"), ("T19", "composite", "Productivity combined with autonomy")],
    ("P01", "c_8ebf75f2b6e6eb95"): [("T07", "focused", "Delegation, distributed trust, specialized management")],
    ("P01", "c_9cc14a362426e426"): [("T07", "focused", "Checks and balances to prevent bad decisions")],
    ("P01", "c_7a8e47d7dde40c83"): [("T07", "focused", "Teamwork, collaboration, connectedness")],
    ("P01", "c_14da47c814c5eff6"): [("T12", "focused", "Positive emotional tone, without assuming negative polarity")],
    ("P01", "c_7ab53d5ed2ab9298"): [("T13", "focused", "General judgment of structure, rather than management competence")],
    ("P01", "c_c6a23601cedffa27"): [("T13", "focused", "General approval/acceptance of structures")],
    ("P02", "c_472b498656f4a128"): [("T13", "focused", "General positive framing with many benefit examples"), ("T07", "composite", "Support/fairness are examples in a broad benefits definition"), ("T08", "composite", "Advancement is one example among benefits"), ("T03", "composite", "Clear roles are one example among benefits")],
    ("P02", "c_8db93daa0a56184c"): [("T07", "focused", "Accountability, oversight, fairness, checks and balances")],
    ("P02", "c_45e7350662b6bf7b"): [("T09", "focused", "Management quality"), ("T14", "composite", "Conditional effects of manager quality")],
    ("P02", "c_eaa8baa37fb68821"): [("T08", "composite", "Promotion combined with mentorship/autonomy/efficiency"), ("T07", "composite", "Mentorship combined with promotion/autonomy/efficiency"), ("T06", "composite", "Autonomy combined with promotion/mentorship/efficiency"), ("T01", "composite", "Efficiency combined with promotion/mentorship/autonomy")],
}

NOTES = (
    "Validation uses candidate-level 5% FDR; composite components are not separately tested. "
    "Theme grouping is post hoc; wording varies across runs. "
    "Real runs share 800 evaluation responses; placebos shuffle labels."
)


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(source, out):
    source, out = Path(source), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    candidates = list(csv.DictReader((source / "feature_memberships_for_review.csv").open()))
    old_counts = list(csv.DictReader((source / "table_4_crosswalk.csv").open()))
    lookup = {f: tid for tid, _, families in THEMES for f in families.split()}
    keys = {(r["run_id"], r["candidate_id"]) for r in candidates}
    assert len(keys) == len(candidates) == 208
    assert not (set(OVERRIDES) - keys), "Unknown override would silently be ignored"
    links, specification = [], []
    for r in candidates:
        choices = OVERRIDES.get((r["run_id"], r["candidate_id"]), [
            (lookup[r["family_id"]], "focused", "Core topic of the source definition, using pooled theme grouping")])
        assert len({t for t, _, _ in choices}) == len(choices)
        for tid, kind, rationale in choices:
            assert kind in {"focused", "composite"}
            label = next(label for t, label, _ in THEMES if tid == t)
            links.append({"theme_id": tid, "theme": label, "link_type": kind,
                          "link_rationale": rationale, **r})
            specification.append({"run_id": r["run_id"], "candidate_id": r["candidate_id"],
                                  "theme_id": tid, "link_type": kind, "rationale": rationale})
    full, counts = [], []
    for tid, label, _ in THEMES:
        row = {"theme_id": tid, "theme": label}
        for rid in RUNS:
            matches = [r for r in links if r["theme_id"] == tid and r["run_id"] == rid]
            confirmed = [r for r in matches if r["tier"] == "confirmed"]
            focused = [r for r in confirmed if r["link_type"] == "focused"]
            row[rid] = "check" if focused else "composite" if confirmed else "proposed" if matches else "absent"
            counts.append({"theme_id": tid, "theme": label, "run_id": rid,
                           "proposed_candidates": len(matches), "validated_candidates": len(confirmed),
                           "focused_validated_candidates": len(focused),
                           "composite_validated_candidates": len(confirmed) - len(focused),
                           "marker": row[rid]})
        full.append(row)
    main = [r for r in full if any(r[rid] in {"check", "composite"} for rid in RUNS)]
    # Verify exact raw counts, no lost candidates, no hidden placebo survivor.
    nrows = [r for r in old_counts if r["family_id"] in {"n_proposed", "n_measured", "n_validated"}]
    for rid in RUNS:
        raw = [r for r in candidates if r["run_id"] == rid]
        assert len(raw) == int(next(r for r in nrows if r["family_id"] == "n_proposed")[rid])
        assert sum(r["tier"] == "confirmed" for r in raw) == int(next(r for r in nrows if r["family_id"] == "n_validated")[rid])
        assert {r["candidate_id"] for r in raw} == {r["candidate_id"] for r in links if r["run_id"] == rid}
    for r in links:
        if r["run_id"] in {"P01", "P02"} and r["tier"] == "confirmed":
            assert r["theme_id"] in {x["theme_id"] for x in main}
    write_csv(out / "theme_crosswalk.csv", main)
    write_csv(out / "appendix_all_themes.csv", full)
    write_csv(out / "appendix_theme_counts.csv", counts)
    write_csv(out / "appendix_candidate_links.csv", links)
    (out / "semantic_link_specification.json").write_text(json.dumps({
        "status": "post_hoc_analyst_authored_descriptive_grouping",
        "themes": [{"theme_id": t, "theme": label} for t, label, _ in THEMES],
        "links": specification}, indent=2) + "\n")
    symbols = {"check": "✓", "composite": "~", "proposed": "○", "absent": "-"}
    def table(rows, numbers=False):
        head = "<tr><th>Substantive theme</th>" + "".join(f"<th>{x}</th>" for x in LABELS) + "</tr>"
        body = []
        if not numbers:
            for row in nrows:
                name = {"n_proposed": "Candidates proposed", "n_measured": "Candidates measured", "n_validated": "Candidates validated (5% FDR)"}[row["family_id"]]
                body.append("<tr class='count'><th>" + name + "</th>" + "".join(f"<td>{row[r]}</td>" for r in RUNS) + "</tr>")
        for row in rows:
            cells = []
            for rid in RUNS:
                group = [r for r in links if r["theme_id"] == row["theme_id"] and r["run_id"] == rid]
                tip = "\n\n".join(f"{r['feature_name']} [{r['tier']}; {r['link_type']}]\n{r['definition']}\n{r['classification_question']}\nEffect women minus men: {r['mean_effect']}\n{r['link_rationale']}" for r in group)
                value = f"{sum(r['tier']=='confirmed' for r in group)}/{len(group)}" if numbers else symbols[row[rid]]
                cells.append(f"<td class='{row[rid]}' title='{escape(tip,quote=True)}'>{value}</td>")
            body.append(f"<tr><th>{escape(row['theme'])}</th>{''.join(cells)}</tr>")
        return "<table><thead>" + head + "</thead><tbody>" + "".join(body) + "</tbody></table>"
    # Visible, explicit links rather than result-dependent merging of old families.
    review = []
    for row in full:
        group = [r for r in links if r["theme_id"] == row["theme_id"]]
        review.append("<details><summary>" + escape(row["theme"]) + "</summary>" + "".join(
            f"<article><b>{escape(r['run_id'])}: {escape(r['feature_name'])}</b> "
            f"<span>[{escape(r['tier'])}; {r['link_type']}]</span><p>{escape(r['definition'])}</p>"
            f"<p><i>Question:</i> {escape(r['classification_question'])}</p>"
            f"<p><i>Link:</i> {escape(r['link_rationale'])}</p>"
            f"<p>Women minus men: {float(r['mean_effect']):+.4f}; permutation p = {float(r['perm_p']):.5f}. "
            "Effects refer to different questions; polarity is not harmonized.</p></article>" for r in group) + "</details>")
    (out / "theme_crosswalk.html").write_text("""<!doctype html><html><head><meta charset='utf-8'><title>Thematic recurrence and candidate validation</title>
<style>body{font:16px Georgia,serif;color:#232827;background:#f0f1ed;margin:0;padding:32px}main{max-width:1160px;background:white;margin:auto;padding:40px}h1{font-size:27px}h2{font-size:20px;margin-top:32px}.status{font:12px Arial;color:#5a6661;letter-spacing:.4px}table{width:100%;border-collapse:collapse;border-top:2px solid #35473e;border-bottom:2px solid #35473e;font-size:14px}th,td{padding:10px 8px;border-bottom:1px solid #e0e4e0;text-align:center}th:first-child{text-align:left;width:43%;font-weight:normal}thead th{font:600 12px Arial;background:#f1f4ef}th:nth-child(6),td:nth-child(6){border-left:1px solid #35473e}.count{background:#f8f9f5}.count td{font-weight:bold}.check{color:#183f32;font-weight:bold}.composite{color:#a15a22;font-weight:bold}.proposed{color:#717a76}.absent{color:#a5aaa7}.notes{font-size:13px;line-height:1.5}summary{cursor:pointer;margin:18px 0;font:600 14px Arial}article{border-left:2px solid #dce5dd;margin:14px 0;padding:8px 16px;font-size:14px;line-height:1.4}article p{margin:7px 0}article span{font:12px Arial;color:#66736c}@media print{body{padding:0;background:white}main{padding:0}details{display:none}}</style></head><body><main>
<h1>Thematic recurrence and candidate validation</h1><p>Women versus men within tall hierarchies</p><p class='status'>PROPOSED MAIN EXHIBIT · DESCRIPTIVE THEME GROUPING · SAVED RESULTS UNCHANGED</p>
""" + table(main) + "<p class='notes'><b>✓</b> Focused candidate validated &nbsp; <b>~</b> Composite candidate validated &nbsp; <b>○</b> Proposed only &nbsp; <b>-</b> Not proposed</p><p class='notes'>" + escape(NOTES) + "</p><details><summary>Alternative display: validated / proposed candidate counts</summary><p class='notes'>Counts are per theme and may overlap across rows. A composite candidate counts once in each theme to which it links. The full candidate, not its components, was tested.</p>" + table(main, True) + "</details><details><summary>All themes, including those without any validation</summary>" + table(full) + "</details><h2>Definitions and link decisions</h2><p class='notes'>These semantic decisions are inspectable and provisional. They are not independent human coding or a reliability estimate.</p>" + "".join(review) + "</main></body></html>", encoding="utf-8")
    pdf(out / "theme_crosswalk.pdf", main, nrows, NOTES)
    manifest = {"status": "post_hoc_descriptive_proposal", "candidates": len(candidates),
                "candidate_theme_links": len(links), "all_themes": len(full), "displayed_themes": len(main),
                "source_sha256": hashlib.sha256((source / "feature_memberships_for_review.csv").read_bytes()).hexdigest(),
                "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "notes": NOTES, "checks": "Raw counts preserved; all 208 candidates linked; all placebo survivors visible; original mapping preserved in source directory"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "README.txt").write_text("Proposed revised exhibit: thematic recurrence and candidate validation.\n\n"
        "The original table and automated family crosswalk remain unchanged. This version groups all candidate banks into broader, analyst-authored themes, with explicit composite links.\n"
        "theme_crosswalk.pdf: one-page main exhibit.\n"
        "theme_crosswalk.html: main exhibit, alternative count display, full theme table, and exact definitions/questions/results/link rationales.\n"
        "appendix_candidate_links.csv: all 208 candidates with inspectable theme links and unchanged saved results.\n"
        "semantic_link_specification.json: exact semantic decisions, without validation tiers or effects.\n\n"
        "Interpretation: broad topic recurrence is stronger than exact-measure stability. The exhibit does not establish identical measurement, independently replicated effects, or calibration from two placebo draws.\n\n" + NOTES + "\n")
    print(json.dumps(manifest, indent=2))


def pdf(path, main, nrows, notes):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph
    c = canvas.Canvas(str(path), pagesize=(612, 792))
    c.setTitle("Thematic recurrence and candidate validation")
    ink = colors.HexColor("#26332d")
    muted = colors.HexColor("#7c8580")
    x, width, name_width = 37, 538, 241
    cell = (width-name_width)/6
    def rule(y, weight=.5):
        c.setStrokeColor(ink); c.setLineWidth(weight); c.line(x,y,x+width,y)
    c.setFillColor(ink); c.setFont("Times-Bold", 14)
    c.drawString(x,752,"Table X. Thematic recurrence and candidate validation")
    c.setFont("Times-Roman",10); c.drawString(x,735,"Women versus men within tall hierarchies")
    c.setFont("Helvetica",7.5); c.setFillColor(muted)
    c.drawString(x,718,"PROPOSED MAIN EXHIBIT  |  Post hoc descriptive grouping; saved candidate tests unchanged")
    top=700; rule(top,1)
    c.setFillColor(ink); c.setFont("Helvetica-Bold",7.5)
    c.drawCentredString(x+name_width+2*cell,top-13,"REAL CONTRAST")
    c.drawCentredString(x+name_width+5*cell,top-13,"LABEL PLACEBOS")
    c.setFont("Times-Bold",8.5); c.drawString(x+3,top-34,"Substantive theme")
    for i,label in enumerate(LABELS):
        words=label.split() if i in {2,3} else [label]
        for j,w in enumerate(words): c.drawCentredString(x+name_width+(i+.5)*cell,top-29-j*10,w)
    y=top-49; rule(y)
    style=ParagraphStyle("label",fontName="Times-Roman",fontSize=8.7,leading=10.2,textColor=ink)
    def mark(value,cx,cy):
        c.setStrokeColor(ink); c.setFillColor(ink); c.setLineWidth(.95)
        if value=="check":
            p=c.beginPath(); p.moveTo(cx-3,cy); p.lineTo(cx-1,cy-2.7); p.lineTo(cx+4,cy+3.4); c.drawPath(p)
        elif value=="composite":
            c.setFillColor(colors.HexColor("#98612c")); c.setFont("Times-Bold",13); c.drawCentredString(cx,cy-4,"~")
        elif value=="proposed":
            c.setStrokeColor(muted); c.setLineWidth(.8); c.circle(cx,cy,2.6)
        elif value=="absent":
            c.setStrokeColor(muted); c.setLineWidth(.6); c.line(cx-2.5,cy,cx+2.5,cy)
        else:
            c.setFont("Times-Bold",10); c.drawCentredString(cx,cy-3,str(value))
    def row(label, values, h, shade=False):
        nonlocal y
        if shade:
            c.setFillColor(colors.HexColor("#f3f5f0")); c.rect(x,y-h,width,h,fill=1,stroke=0)
        p=Paragraph(escape(label),style); _,ph=p.wrap(name_width-10,h)
        assert ph <= h-2, f"Row label overflow: {label}"
        p.drawOn(c,x+3,y-h/2-ph/2)
        for i,value in enumerate(values): mark(value,x+name_width+(i+.5)*cell,y-h/2)
        y-=h
        c.setStrokeColor(colors.HexColor("#dce1dc")); c.setLineWidth(.3); c.line(x,y,x+width,y)
    for r in nrows:
        name={"n_proposed":"Candidates proposed", "n_measured":"Candidates measured", "n_validated":"Candidates validated (5% FDR)"}[r["family_id"]]
        row(name,[r[rid] for rid in RUNS],19,True)
    rule(y,.7)
    for r in main: row(r["theme"],[r[rid] for rid in RUNS],20)
    rule(y,1)
    c.setStrokeColor(ink); c.setLineWidth(.65)
    c.line(x+name_width+4*cell,top,x+name_width+4*cell,y)
    y-=18
    for value,cx,label in [("check",x+4,"Focused measure validates"),("composite",x+155,"Composite measure validates"),("proposed",x+327,"Proposed only"),("absent",x+441,"Not proposed")]:
        mark(value,cx,y); c.setFillColor(ink); c.setFont("Times-Roman",7.5); c.drawString(cx+8,y-2.5,label)
    ns=ParagraphStyle("notes",fontName="Times-Roman",fontSize=7.7,leading=9.6,textColor=ink)
    p=Paragraph("<b>Notes.</b> "+escape(notes),ns); _,ph=p.wrap(width,200)
    p.drawOn(c,x,y-15-ph)
    assert y-15-ph>30, "Page notes overflow"
    c.save()


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    build(args.source,args.out)
