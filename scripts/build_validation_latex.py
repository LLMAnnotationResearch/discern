"""Export manuscript-ready LaTeX and complete, traceable per-run appendices.

The standalone proofs inline all content for the native single-file compiler.
Manuscript fragments inherit the parent document's font and counter settings.
"""
import argparse
import csv
import hashlib
from html import escape
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_theme_crosswalk import RUNS, LABELS, NOTES

FULL_THEME_NOTES = NOTES.replace(
    "Displayed themes have at least one validated link in any run; all remaining themes and exact definitions appear in the appendix.",
    "All 21 pooled themes are shown, including those with no validation in any run.")

TIER = {"confirmed": "V", "suggestive": "S", "uncorrected": "U", "not_validated": "N", "unmeasurable": "M"}
DESIGNS = {
    "ARCHIVE": "Archived reference run; three-model discovery and measurement pool.",
    "R01": "Same data partition and reference pool; discovery seed changed from 100 to 1001.",
    "E_DEFAULTS": "Current default discovery and measurement pools, including DeepSeek; discovery seed 100.",
    "E_OPENAI": "OpenAI-only discovery and measurement pools; discovery seed 100.",
    "P01": "Full-pipeline placebo: shuffle index 0, with the reference model pool.",
    "P02": "Full-pipeline placebo: shuffle index 1, with the reference model pool.",
    "P03": "Full-pipeline placebo: shuffle index 2, with the reference model pool.",
    "P04": "Full-pipeline placebo: shuffle index 3, with the reference model pool.",
    "P05": "Full-pipeline placebo: shuffle index 4, with the reference model pool.",
    "P03_INITIAL": "Initial measurement attempt for Placebo 3, retained to document the operationalization failure before repair.",
}
APPENDIX_NOTES = (
    "Every consolidated candidate is included, including candidates that did not validate. "
    "Effects are percentage-point differences in the prevalence of the binary coded feature. "
    "For real runs, positive values indicate higher prevalence among women; for placebo runs, "
    "positive values indicate higher prevalence under the shuffled focal label, not actual gender. "
    "d1 and d2 are effects in the two locked measurement halves; Mean is their average. "
    "p is the saved replication-gated permutation p-value, using 5,000 permutations; a value of "
    "1.0000 can reflect failure of the same-sign gate. V denotes validated at 5% FDR; "
    "S denotes suggestive at 10% FDR only; U denotes the same-sign, nominal p < .05 tier outside "
    "both FDR tiers; N denotes none of those tiers. U is uncorrected and is not validated. "
    "Tier decisions are copied from the saved outputs and apply within each run's candidate bank. "
    "The catalogue retains exact feature definitions and classification questions. "
    "The real runs reuse the same 800 evaluation responses, with 400 per group and 200 per group "
    "in each half. Placebos reserve the same responses with halves stratified on shuffled labels."
)
PACKAGES = r"""% Add these packages to the manuscript preamble if not already loaded.
\usepackage{array}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{amssymb}
"""


def tex(value):
    value = str(value).replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2013", "--").replace("\u2014", "---").replace("\u00a0", " ")
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(c, c) for c in value)


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def proof(fragment, title, appendix=False):
    if not appendix:
        return (r"\documentclass[letterpaper,12pt]{article}" + "\n" +
                r"\begin{document}" + "\n" + r"\clearpage" + "\n" + fragment +
                "\n" + r"\end{document}" + "\n")
    return (r"\documentclass[11pt]{article}" + "\n" +
            r"\usepackage[letterpaper,margin=0.75in]{geometry}" + "\n" +
            r"\usepackage[T1]{fontenc}" + "\n" + (PACKAGES if appendix else "") +
            r"\setlength{\parindent}{0pt}" + "\n" +
            (r"\renewcommand{\thetable}{S\arabic{table}}" + "\n" if appendix else "") +
            r"\begin{document}" + "\n" + fragment + "\n" + r"\end{document}" + "\n")


def main_table(rows, counts):
    marks={"check":r"\DiscernCheck", "composite":r"\(\sim\)","proposed":r"\(\circ\)","absent":r"\(-\)"}
    # Kernel-only table: no tabularx/array column types or external symbol fonts.
    # Freeze dimensions before entering p columns, where linewidth becomes local.
    lines=["% Drop-in main table: no additional packages required.",
           "% Input in the document body, outside another table environment.",
           "% Uses a full-width table* automatically in two-column manuscripts.",
           r"\begingroup",
           r"\ifdim\columnwidth<\textwidth\def\DiscernFloat{table*}\else\def\DiscernFloat{table}\fi",
           r"\begin{\DiscernFloat}[!htbp]", r"\centering",
           r"\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont",
           r"\setlength{\parskip}{0pt}\setlength{\parindent}{0pt}",
           r"\caption{Thematic recurrence and candidate validation}", r"\label{tab:validation-theme-crosswalk}",
           r"\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont",
           r"\setlength{\tabcolsep}{3pt}\setlength{\arrayrulewidth}{0.4pt}", r"\renewcommand{\arraystretch}{1.08}",
           r"\edef\DiscernRunWidth{\the\dimexpr.078\linewidth\relax}",
           r"\edef\DiscernLabelWidth{\the\dimexpr\linewidth-\DiscernRunWidth*6-12\tabcolsep-\arrayrulewidth\relax}",
           r"\def\DiscernCell#1{\makebox[\DiscernRunWidth][c]{#1}}",
           r"\def\DiscernLabel#1{{\raggedright#1\par}}",
           r"\def\DiscernCheck{\ifdefined\checkmark\(\checkmark\)\else{\setlength{\unitlength}{1pt}\linethickness{0.65pt}\begin{picture}(8,8)\qbezier(0,3)(1,2)(2,1)\qbezier(2,1)(4,4)(6,7)\end{picture}}\fi}",
           r"\begin{tabular}{@{}p{\DiscernLabelWidth}*{4}{p{\DiscernRunWidth}}|*{2}{p{\DiscernRunWidth}}@{}}",
           r"\hline", r" & \multicolumn{4}{c|}{Real contrast} & \multicolumn{2}{c}{Label placebos}" + r" \\",
           r"\cline{2-5}\cline{6-7}",
           r"\DiscernLabel{Substantive theme} & \DiscernCell{\shortstack{Main\\run}} & \DiscernCell{Repeat} & \DiscernCell{\shortstack{Default\\pool}} & \DiscernCell{\shortstack{OpenAI\\only}} & \DiscernCell{\shortstack{Placebo\\1}} & \DiscernCell{\shortstack{Placebo\\2}}" + r" \\", r"\hline"]
    for label, key in [("Candidates proposed","n_proposed"),("Candidates measured","n_measured"),("Candidates validated (5% FDR)","n_validated")]:
        row=next(r for r in counts if r["family_id"]==key)
        lines.append(r"\DiscernLabel{"+tex(label)+"} & "+" & ".join(r"\DiscernCell{\textbf{"+row[r]+"}}" for r in RUNS)+r" \\")
    lines.append(r"\hline")
    for row in rows:
        lines.append(r"\DiscernLabel{"+tex(row["theme"])+"} & "+" & ".join(r"\DiscernCell{"+marks[row[r]]+"}" for r in RUNS)+r" \\")
    lines += [r"\hline", r"\end{tabular}", r"\par\vspace{5pt}",
              r"\begin{minipage}{\linewidth}\def\baselinestretch{1}\fontsize{7.6}{9.2}\selectfont",
              r"\DiscernCheck\ Focused measure validates; \(\sim\) composite measure validates; \(\circ\) proposed only; \(-\) not proposed.",
              r"\par\vspace{3pt}\textit{Notes.} Women versus men within tall hierarchies. " + tex(NOTES),
              r"\end{minipage}", r"\end{\DiscernFloat}", r"\endgroup"]
    return "\n".join(lines)+"\n"


def summary_tex(data):
    lines=[r"\begin{table}[!htbp]\centering\small",
           r"\caption{Run designs and complete candidate counts}\label{tab:validation-run-designs}",
           r"\setlength{\tabcolsep}{4pt}",
           r"\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}Xrrrrr@{}}\toprule",
           r"Run & Proposed & Measured & V & S & U \\\midrule"]
    for run in data:
        s=run["selection"]
        lines.append(tex(run["label"])+" & "+" & ".join(str(n) for n in [len(run["bank"]),len(s["results"]),s["n_validated"],s["n_suggestive"],s["n_uncorrected"]])+r" \\")
    lines += [r"\bottomrule\end{tabularx}",r"\end{table}","\n"+tex(APPENDIX_NOTES)+"\n"]
    return "\n".join(lines)


def full_theme_tex(rows):
    marks={"check":r"\(\checkmark\)","composite":r"\(\sim\)","proposed":r"\(\circ\)","absent":r"\(-\)"}
    header=(r"Theme & \shortstack{Main\\run} & Repeat & \shortstack{Default\\pool} & \shortstack{OpenAI\\only} & \shortstack{Placebo\\1} & \shortstack{Placebo\\2}" + r" \\\hline")
    lines=[r"\clearpage\subsection*{Complete descriptive theme crosswalk}",
           r"\begingroup\small\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.2}",
           r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{.43\linewidth}*{4}{>{\centering\arraybackslash}p{.075\linewidth}}|*{2}{>{\centering\arraybackslash}p{.075\linewidth}}@{}}",
           r"\caption{All pooled descriptive themes, including those with no validation}\label{tab:validation-all-themes}\\",
           r"\hline",r" & \multicolumn{4}{c|}{Real contrast} & \multicolumn{2}{c}{Label placebos}"+r" \\",header,r"\endfirsthead",
           r"\multicolumn{7}{l}{\textit{Complete descriptive theme crosswalk (continued)}}\\\hline",header,r"\endhead",
           r"\hline\endfoot\hline\endlastfoot"]
    for r in rows: lines.append(tex(r["theme"])+" & "+" & ".join(marks[r[rid]] for rid in RUNS)+r" \\")
    lines += [r"\end{longtable}\endgroup",r"\footnotesize \(\checkmark\): focused measure validates; \(\sim\): composite measure validates; \(\circ\): proposed only; \(-\): not proposed. "+tex(FULL_THEME_NOTES)+r"\normalsize"]
    return "\n".join(lines)+"\n"


def run_tex(run):
    rid=run["run_id"];cfg=run["cfg"]
    model=", ".join(cfg["discovery_models"])
    rotation=", ".join(cfg["rotation_pool"])
    lines=[r"\clearpage",r"\subsection*{"+tex(run["label"]+" ("+rid+")")+"}",
           tex(DESIGNS[rid])+r"\par", r"\textit{Discovery models:} "+tex(model)+r".\par",
           r"\textit{Measurement pool:} "+tex(rotation)+r".\par",
           tex("15 discovery calls per half; 15 texts per active group per call; rotation measurement design. Consolidation model: "+cfg["consolidation_model"]+".")+r"\par",
           tex("Discovery seed: "+str(cfg["discovery_seed"])+"; reservation/split seeds: "+str(cfg["reservation_seed"])+"/"+str(cfg["split_seed"])+"; assignment seed: "+str(cfg["assignment_seed"])+".")+r"\par"]
    if rid.startswith("P"):
        lines.append(tex("Placebo seed: "+str(cfg["placebo_seed"])+"; shuffle index: "+str(cfg["run_index"])+". Effects concern shuffled labels, not actual women versus men.")+r"\par")
    if rid=="E_DEFAULTS":
        lines.append(tex("Measurement audit: 28 fallback judgments across two candidates, neither validated. DeepSeek alias resolved to deepseek-flash; actual model allocations are documented in the saved audit.")+r"\par")
    if run.get('measurement_note'):
        lines.append(tex(run['measurement_note'])+r"\par")
    lines += [r"\begingroup\small\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.13}",
              r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{.47\linewidth}rrrrc@{}}",
              r"\caption{Complete candidate results: "+tex(run["label"])+r"}\label{tab:validation-"+rid.lower().replace("_","-")+r"-results}\\",
              r"\toprule Feature & \(d_1\) & \(d_2\) & Mean & \(p\) & Tier \\\midrule\endfirsthead",
              r"\multicolumn{6}{l}{\textit{Complete candidate results: "+tex(run["label"])+r" (continued)}}\\",
              r"\toprule Feature & \(d_1\) & \(d_2\) & Mean & \(p\) & Tier \\\midrule\endhead",
              r"\midrule\multicolumn{6}{r}{\footnotesize Continued on next page}\\\endfoot",
              r"\bottomrule\endlastfoot"]
    for row in run["rows"]:
        name=tex(row["exhibit_id"]+". "+row["feature_name"])
        values=(["--"]*4 if row['tier']=='unmeasurable' else
                [f"{100*row[k]:+.2f}" for k in ["d1","d2","mean_effect"]]+[f"{row['perm_p']:.4f}"])
        lines.append(name+" & "+" & ".join(values+[TIER[row["tier"]]])+r" \\")
    lines += [r"\end{longtable}\endgroup",r"\par\footnotesize Effects are percentage points. V: 5\% FDR; S: 10\% FDR only; U: uncorrected; N: not validated. Rounded values do not determine tier assignments.\normalsize",
              r"\clearpage",r"\subsubsection*{Complete feature catalogue: "+tex(run["label"])+"}",
              r"\begingroup\small\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.12}",
              r"\begin{longtable}{@{}p{.06\linewidth}>{\raggedright\arraybackslash}p{.89\linewidth}@{}}",
              r"\caption{Feature definitions and classification questions: "+tex(run["label"])+r"}\label{tab:validation-"+rid.lower().replace("_","-")+r"-catalogue}\\",
              r"\toprule ID & Exact candidate text and discovery metadata \\\midrule\endfirsthead",
              r"\multicolumn{2}{l}{\textit{Feature catalogue: "+tex(run["label"])+r" (continued)}}\\",
              r"\toprule ID & Exact candidate text and discovery metadata \\\midrule\endhead",
              r"\midrule\multicolumn{2}{r}{\footnotesize Continued on next page}\\\endfoot",
              r"\bottomrule\endlastfoot"]
    for row in run["rows"]:
        text=(r"\textbf{"+tex(row["feature_name"])+r"}\par "
              +r"\textit{Definition:} "+tex(row["definition"])+r"\par "
              +r"\textit{Classification question:} "+tex(row["classification_question"])+r"\par "
              +r"\textit{Candidate ID:} {\ttfamily\footnotesize "+tex(row["candidate_id"])+r"}\par "
              +tex("Discovery direction: "+str(row["claimed_direction"])+"; source halves: "+", ".join(row["source_splits"] or [])+"; supporting hypotheses: "+str(row["n_supporting_hypotheses"])+"; direction conflict: "+str(row["direction_conflict"])+".")+r"\par "
              +tex("Same-sign measurement halves: "+str(row["same_sign"])+"; measured direction: "+str(row["measured_direction"])+"."))
        if row['tier']=='unmeasurable':
            text+=r"\par\textit{Measurement status:} "+tex(row['measurement_issue'])
        lines.append(tex(row["exhibit_id"])+" & "+text+r" \\[6pt]")
    lines.append(r"\end{longtable}\endgroup")
    return "\n".join(lines)+"\n"


def build(theme, original, out):
    theme,original,out=Path(theme),Path(original),Path(out)
    out.mkdir(parents=True,exist_ok=True)
    (out/"runs").mkdir(exist_ok=True)
    (out/"data").mkdir(exist_ok=True)
    main=list(csv.DictReader((theme/"theme_crosswalk.csv").open()))
    all_themes=list(csv.DictReader((theme/"appendix_all_themes.csv").open()))
    counts=list(csv.DictReader((original/"table_4_crosswalk.csv").open()))
    manifest=json.loads((original/"manifest.json").read_text())
    memberships={(r["run_id"],r["candidate_id"]):r for r in csv.DictReader((original/"feature_memberships_for_review.csv").open())}
    all_rows,data,sources=[],[],{}
    for index,rid in enumerate(RUNS):
        source=Path(next(r for r in manifest["runs"] if r["run_id"]==rid)["artifact_path"])
        cfg=json.loads((source/"00_config.json").read_text());cfg=cfg.get("config",cfg)
        bank=json.loads((source/"02_consolidated.json").read_text())["candidates"]
        selection=json.loads((source/"04_selected.json").read_text())
        assert {c["candidate_id"] for c in bank} == {c["candidate_id"] for c in selection["results"]}
        assert len(bank)==len(selection["results"])
        rows=[]
        for i,r in enumerate(selection["results"],1):
            old=memberships[(rid,r["candidate_id"])]
            assert old["tier"]==r["tier"] and abs(float(old["mean_effect"])-r["mean_effect"])<1e-12
            assert abs((r["d1"]+r["d2"])/2-r["mean_effect"])<1e-12
            assert abs(float(old["perm_p"])-r["perm_p"])<1e-12
            row={"run_id":rid,"exhibit_id":f"{chr(65+index)}{i:02}",**r}
            rows.append(row)
        rawdir=out/"data"/rid;rawdir.mkdir(exist_ok=True)
        for name in ["02_consolidated.json","04_selected.json"]:
            shutil.copy2(source/name,rawdir/name)
        model_fields=["condition","run_index","discovery_models","rotation_pool","discovery_prompt_variant","n_iterations","items_per_group","discovery_temperature","consolidation_model","n_per_group","measurement_design","permutations","fdr_q","fdr_q_exploratory","effect_floor","reservation_seed","split_seed","assignment_seed","placebo_seed","discovery_seed"]
        (rawdir/"run_settings.json").write_text(json.dumps({k:cfg[k] for k in model_fields},indent=2)+"\n")
        flattened=[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows]
        write_csv(out/"runs"/(rid+"_full_results.csv"),flattened)
        data.append({"run_id":rid,"label":LABELS[index],"cfg":cfg,"bank":bank,"selection":selection,"rows":rows})
        all_rows+=flattened
        sources[rid]={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in ["00_config.json","02_consolidated.json","04_selected.json"]}
    assert len(all_rows)==208
    write_csv(out/"all_runs_full_results.csv",all_rows)
    table=main_table(main,counts)
    (out/"table_4_theme_crosswalk.tex").write_text(table)
    (out/"table_4_preview.tex").write_text(proof(table,"Main table"))
    themes_fragment=full_theme_tex(all_themes)
    (out/"appendix_theme_crosswalk.tex").write_text(themes_fragment)
    start=r"\section*{Appendix: complete validation-run outputs}"+"\n"+summary_tex(data)+"\n"+themes_fragment
    pieces=[]
    for run in data:
        piece=run_tex(run);pieces.append(piece)
        (out/"runs"/(run["run_id"]+".tex")).write_text(piece)
    (out/"appendix_validation_runs.tex").write_text(start+"\n".join(pieces))
    (out/"appendix_validation_preview.tex").write_text(proof(start+"\n".join(pieces),"Full run appendix",True))
    (out/"validation_preamble.tex").write_text(PACKAGES)
    appendix_pdf(data,all_themes,out/"appendix_validation_runs.pdf")
    appendix_html(data,out/"appendix_validation_runs.html")
    (out/"manifest.json").write_text(json.dumps({"runs":RUNS,"total_candidates":len(all_rows),"candidate_counts":{r["run_id"]:len(r["rows"]) for r in data},"source_sha256":sources,"builder_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"checks":"Every consolidated candidate has one statistical result; all 208 preserved; tiers/effects/p-values match the prior exhibit; effects reconstruct from the two halves.","appendix_notes":APPENDIX_NOTES},indent=2)+"\n")
    (out/"README.txt").write_text("LaTeX validation exhibit package\n\n"
        "MAIN TABLE (updated 2026-10-27): no extra packages required. Upload table_4_theme_crosswalk.tex into the Overleaf FigsTables folder, then use:\n"
        "  \\clearpage\n  \\input{FigsTables/table_4_theme_crosswalk}\n\n"
        "The table sets its spacing locally, uses standard LaTeX table columns and drawn checkmarks, and spans both columns in a two-column manuscript. Input it outside another table environment. Font family and table numbering are inherited; table text size and line spacing are set locally to keep the exhibit compact.\n\n"
        "APPENDIX: add the packages in validation_preamble.tex to your preamble. After your existing appendix setup, use:\n"
        "  \\input{FigsTables/section4_validation/latex/appendix_validation_runs}\n\n"
        "Neither fragment resets appendix counters. The main table has a vertical rule between the four real runs and two placebos.\n"
        "table_4_preview.tex and appendix_validation_preview.tex are standalone, self-contained proofs for the built-in LaTeX editor. The appendix has the full 21-theme crosswalk, one complete statistical table and one exact feature catalogue per run, plus a run summary. All 208 final consolidated candidates are included. Discovery prompts are covered in the existing manuscript Appendix B.\n"
        "Each run's exact saved consolidated-bank and selection JSON is in data/. runs/ contains individual LaTeX fragments and full CSV results. all_runs_full_results.csv retains all saved result fields with stable exhibit IDs. No new statistical tests or model calls were made.\n"
        "The exported appendix PDF/HTML are reading copies generated from the same data. The LaTeX proof is the authority for manuscript layout and inherits the packages/fonts of its wrapper.\n\n"+APPENDIX_NOTES+"\n")
    print(json.dumps({"runs":len(data),"candidates":len(all_rows),"out":str(out)},indent=2))


def appendix_pdf(data,all_themes,path):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT,TA_CENTER
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle,PageBreak,KeepTogether,Flowable
    ink=colors.HexColor("#26332d")
    normal=ParagraphStyle("normal",fontName="Times-Roman",fontSize=9,leading=11.5,textColor=ink,spaceAfter=5)
    small=ParagraphStyle("small",parent=normal,fontSize=8,leading=10,spaceAfter=3)
    heading=ParagraphStyle("heading",parent=normal,fontName="Times-Bold",fontSize=15,leading=18,spaceAfter=12)
    sub=ParagraphStyle("sub",parent=heading,fontSize=12,leading=14,spaceAfter=8)
    number=ParagraphStyle("number",parent=small,alignment=TA_RIGHT)
    center=ParagraphStyle("center",parent=small,alignment=TA_CENTER)
    def p(s,style=normal):return Paragraph(escape(str(s)),style)
    def table(rows,widths):
        t=LongTable(rows,colWidths=widths,repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LINEABOVE",(0,0),(-1,0),.8,ink),("LINEBELOW",(0,0),(-1,0),.6,ink),("LINEBELOW",(0,-1),(-1,-1),.8,ink),("LINEBELOW",(0,1),(-1,-1),.25,colors.HexColor("#dce1dc")),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#f1f4ef")),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        return t
    story=[p("Appendix: complete validation-run outputs",heading),p("Women versus men within tall hierarchies"),p("All six completed runs; all 208 consolidated candidates. Statistical results are unchanged.")]
    summary=[[p(x,small) for x in ["Run","Proposed","Measured","V","S","U"]]]
    for r in data:
        s=r["selection"]
        summary.append([p(r["label"],small)]+[p(str(x),number) for x in [len(r["bank"]),len(s["results"]),s["n_validated"],s["n_suggestive"],s["n_uncorrected"]]])
    story += [table(summary,[222,62,62,57,57,57]),Spacer(1,12),p(APPENDIX_NOTES)]
    class Mark(Flowable):
        def __init__(self,value):
            Flowable.__init__(self);self.value=value;self.width=38.5;self.height=10
        def draw(self):
            c=self.canv;cx=self.width/2;cy=5;c.setStrokeColor(ink);c.setFillColor(ink);c.setLineWidth(.9)
            if self.value=="check":
                shape=c.beginPath();shape.moveTo(cx-3,cy);shape.lineTo(cx-1,cy-2.5);shape.lineTo(cx+4,cy+3);c.drawPath(shape)
            elif self.value=="composite":
                c.setFont("Times-Bold",12);c.drawCentredString(cx,cy-3,"~")
            elif self.value=="proposed":c.circle(cx,cy,2.3)
            else:c.line(cx-2.5,cy,cx+2.5,cy)
    theme_rows=[[p("Theme",small)]+[p(label,small) for label in LABELS]]
    for r in all_themes:theme_rows.append([p(r["theme"],small)]+[Mark(r[rid]) for rid in RUNS])
    theme_table=table(theme_rows,[239]+[46.5]*6)
    theme_table.setStyle(TableStyle([("LINEBEFORE",(5,0),(5,-1),.65,ink)]))
    story += [PageBreak(),p("Complete descriptive theme crosswalk",heading),theme_table,Spacer(1,9),p("Check: focused measure validates; tilde: composite measure validates; open circle: proposed only; dash: not proposed. "+FULL_THEME_NOTES,small)]
    for r in data:
        cfg=r["cfg"];rid=r["run_id"]
        story += [PageBreak(),p(r["label"]+" ("+rid+")",heading),p(DESIGNS[rid]),p("Discovery models: "+", ".join(cfg["discovery_models"])+".",small),p("Measurement pool: "+", ".join(cfg["rotation_pool"])+".",small),p("Discovery seed: "+str(cfg["discovery_seed"])+"; consolidation model: "+cfg["consolidation_model"]+". 15 calls per half, 15 texts per active group per call.",small)]
        if rid.startswith("P"):
            story.append(p("Placebo seed "+str(cfg["placebo_seed"])+", shuffle index "+str(cfg["run_index"])+". Signs refer to shuffled labels.",small))
        if rid=="E_DEFAULTS":story.append(p("Audit: 28 fallback judgments across two candidates, neither validated. DeepSeek alias resolved to deepseek-flash.",small))
        story += [p("Complete candidate results",sub)]
        stats=[[p(x,small) for x in ["Feature","d1 (pp)","d2 (pp)","Mean (pp)","p","Tier"]]]
        for row in r["rows"]:
            stats.append([p(row["exhibit_id"]+". "+row["feature_name"],small)]+[p(f"{100*row[k]:+.2f}",number) for k in ["d1","d2","mean_effect"]]+[p(f"{row['perm_p']:.4f}",number),p(TIER[row["tier"]],center)])
        story += [table(stats,[277,50,50,57,53,30]),Spacer(1,8),p("V: 5% FDR; S: 10% FDR only; U: uncorrected; N: not validated. Rounding does not determine tiers.",small),PageBreak(),p("Complete feature catalogue: "+r["label"],heading)]
        for row in r["rows"]:
            block=[p(row["exhibit_id"]+". "+row["feature_name"],sub),p("Definition: "+row["definition"]),p("Classification question: "+row["classification_question"]),p("Candidate ID: "+row["candidate_id"],small),p("Discovery direction: "+str(row["claimed_direction"])+"; source halves: "+", ".join(row["source_splits"] or [])+"; supporting hypotheses: "+str(row["n_supporting_hypotheses"])+"; direction conflict: "+str(row["direction_conflict"])+".",small),p("Same-sign measurement halves: "+str(row["same_sign"])+"; measured direction: "+str(row["measured_direction"])+".",small),Spacer(1,9)]
            story.append(KeepTogether(block))
    def footer(c,doc):
        c.setFont("Times-Roman",8);c.setFillColor(ink);c.drawString(38,25,"Full validation-run outputs | effects in percentage points");c.drawRightString(574,25,str(doc.page))
    SimpleDocTemplate(str(path),pagesize=(612,792),rightMargin=35,leftMargin=35,topMargin=37,bottomMargin=42,title="Complete validation-run outputs").build(story,onFirstPage=footer,onLaterPages=footer)


def appendix_html(data,path):
    sections=[]
    for r in data:
        rows=[]
        for x in r["rows"]:
            values=[f"{100*x[k]:+.2f}" for k in ["d1","d2","mean_effect"]]+[f"{x['perm_p']:.4f}",TIER[x["tier"]]]
            rows.append("<tr><td>"+escape(x["exhibit_id"]+". "+x["feature_name"])+"<details><summary>Definition and classification question</summary><p>"+escape(x["definition"])+"</p><p>"+escape(x["classification_question"])+"</p><p>Candidate ID: "+escape(x["candidate_id"])+"</p></details></td>"+"".join("<td>"+v+"</td>" for v in values)+"</tr>")
        sections.append("<section id='"+r["run_id"]+"'><h2>"+escape(r["label"]+" ("+r["run_id"]+")")+"</h2><p>"+escape(DESIGNS[r["run_id"]])+"</p><table><thead><tr><th>Feature</th><th>d1 (pp)</th><th>d2 (pp)</th><th>Mean (pp)</th><th>p</th><th>Tier</th></tr></thead><tbody>"+"".join(rows)+"</tbody></table></section>")
    path.write_text("<!doctype html><html><head><meta charset='utf-8'><title>Complete validation-run outputs</title><style>body{font:16px Georgia;color:#26332d;max-width:1100px;margin:36px auto;padding:20px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px;border-bottom:1px solid #ddd;vertical-align:top;text-align:right}th:first-child,td:first-child{text-align:left;width:54%}thead{background:#f1f4ef}section{margin-top:40px}summary{cursor:pointer;font:12px Arial;color:#64746b;margin-top:7px}details p{font-size:13px}nav a{margin-right:15px}p{line-height:1.5}</style></head><body><h1>Complete validation-run outputs</h1><p>"+escape(APPENDIX_NOTES)+"</p><nav>"+"".join("<a href='#"+r["run_id"]+"'>"+escape(r["label"])+"</a>" for r in data)+"</nav>"+"".join(sections)+"</body></html>")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme",required=True)
    parser.add_argument("--original",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    build(args.theme,args.original,args.out)
