"""Separate the placebo tier counts from the real-run substantive crosswalk.

Requires completed artifacts for all five placebos. It never substitutes pending
runs or suppresses a survivor. Appendix D includes every candidate in all runs.
"""
import argparse
from collections import Counter
import csv
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_validation_latex import tex
from build_appendix_d import CHECK

REAL = ["ARCHIVE", "R01", "E_DEFAULTS", "E_OPENAI"]
PLACEBOS = ["P01", "P02", "P03", "P04", "P05"]
ORDER = REAL + PLACEBOS
LABELS = {"ARCHIVE": "Main run", "R01": "Same-pool repeat", "E_DEFAULTS": "Default pool", "E_OPENAI": "OpenAI only", **{rid: f"Placebo {i}" for i, rid in enumerate(PLACEBOS, 1)}}
PLACEBO_NOTE = ("Observed contrast: women versus men in tall hierarchies. Placebos rerun the full pipeline with shuffled labels "
                "(N = 800; 5,000 permutations). Tiers are exclusive; uncorrected requires same-sign effects and p < .05. "
                "See Appendix D.")
STABILITY_NOTE = ("Women versus men in tall hierarchies. Rows align related questions post hoc; wording and scope vary. "
                  "Runs reuse 800 evaluation responses. Full questions: Appendix D.")
STABILITY_TITLE = "Thematic recurrence across real runs"
DISPLAY_LABELS = {
    "T01": "Slow procedures and approvals",
    "T02": "Rigidity and resistance to change",
    "T03": "Hierarchy and management layers",
    "T04": "Unnecessary management positions",
}
STABILITY_LEGEND = "Focused feature proposed; * also validated (5% FDR); ~ broader question only; - not proposed."


def recurrence_rows(rows, links):
    """Separate focused rediscovery, focused validation, and broader-only coverage.

    Composite components never inherit a star from their parent question. Each
    candidate may have only one focused link, so it cannot validate two rows.
    The displayed rows and underlying semantic links are held fixed.
    """
    focused=Counter((l['run_id'],l['candidate_id']) for l in links if l['link_type']=='focused')
    if any(n>1 for n in focused.values()):raise ValueError('A candidate cannot provide focused validation for multiple rows')
    result=[]
    for row in rows:
        updated={**row,'theme':DISPLAY_LABELS.get(row['theme_id'],row['theme'])}
        for rid in REAL:
            group=[l for l in links if l['theme_id']==row['theme_id'] and l['run_id']==rid]
            direct=[l for l in group if l['link_type']=='focused']
            updated[rid]=('validated' if any(l['tier']=='confirmed' for l in direct) else
                          'proposed' if direct else 'broader' if group else 'absent')
        result.append(updated)
    return result


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_tiers(results):
    """Independently check exclusive tiers against the saved, unrounded p-values."""
    ordered=sorted(results,key=lambda r:r['perm_p'])
    def accepted(q):
        passing=[i for i,r in enumerate(ordered,1) if r['perm_p']<=q*i/len(ordered)]
        return {r['candidate_id'] for r in ordered[:max(passing,default=0)]}
    primary,secondary=accepted(.05),accepted(.1)
    for r in results:
        cid=r['candidate_id']
        same=(r['d1']*r['d2']>0)
        expected=('confirmed' if cid in primary else 'suggestive' if cid in secondary else
                  'uncorrected' if same and r['perm_p']<.05 else 'not_validated')
        assert r['tier']==expected,(cid,r['tier'],expected)
        assert r['same_sign']==same,cid
        assert abs(r['mean_effect']-(r['d1']+r['d2'])/2)<1e-12,cid


def write_csv(path, rows):
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def load_runs(original, extra, repair=None):
    prior=json.loads((original/"manifest.json").read_text())["runs"]
    sources={r["run_id"]:Path(r["artifact_path"]) for r in prior}
    for job in json.loads(extra.read_text())["planned_jobs"]:
        cfg=json.loads(Path(job["config_path"]).read_text())
        sources[job["run_id"]]=Path(cfg["output_dir"])/job["run_id"]
    if repair is not None:sources['P03']=Path(repair)
    runs=[]
    for index,rid in enumerate(ORDER):
        root=sources[rid]
        if not (root/"04_selected.json").exists():
            raise ValueError(f"{rid} is incomplete; refusing to publish pending placebo results")
        cfg=json.loads((root/"00_config.json").read_text());cfg=cfg.get("config",cfg)
        bank=json.loads((root/"02_consolidated.json").read_text())["candidates"]
        selected=json.loads((root/"04_selected.json").read_text())
        results=selected["results"]
        events=list(map(json.loads,(root/'events.jsonl').open()))
        skipped={e['candidate_id']:e for e in events if e['stage']=='measure' and e['kind']=='candidate_skipped'}
        missing={c['candidate_id'] for c in bank}-{r['candidate_id'] for r in results}
        assert missing==set(skipped),f'{rid}: every missing candidate must have an explicit measurement-failure record'
        assert len(missing)==selected.get('n_skipped_unmeasurable',0)
        assert len(bank)==len(results)+len(missing)
        tiers=Counter(r["tier"] for r in results)
        for key,tier in [("n_validated","confirmed"),("n_suggestive","suggestive"),("n_uncorrected","uncorrected")]:
            assert selected[key]==tiers[tier], (rid,key)
        assert sum(tiers.values())==len(results)
        assert selected["permutations"]==5000 and selected["fdr_q"]==.05 and selected["fdr_q_exploratory"]==.1
        assert cfg["n_per_group"]==400 and cfg["effect_floor"] is None
        check_tiers(results)
        if rid in PLACEBOS:
            assert cfg["condition"]=="placebo"
            assert cfg["run_index"]==PLACEBOS.index(rid)
            assert cfg["discovery_models"]==["gpt-4o-mini","claude-haiku","gpt-4.1-mini"]
        reported=[{**r,'measurement_status':'measured','measurement_issue':''} for r in results]
        for c in bank:
            if c['candidate_id'] not in missing:continue
            row=dict.fromkeys(results[0])
            row.update({k:v for k,v in c.items() if k in row})
            row.update(tier='unmeasurable',same_sign='not assessed',measured_direction='not assessed',
                       measurement_status='unmeasurable',measurement_issue=skipped[c['candidate_id']]['error'])
            reported.append(row)
        rows=[{"run_id":rid,"exhibit_id":f"{chr(65+index)}{i:02}",**r} for i,r in enumerate(reported,1)]
        failures=sum(e['stage']=='measure' and e['kind']=='failure' for e in events)
        fallbacks=sum(e['stage']=='measure' and e['kind']=='fallback' for e in events)
        measurement_note=(f'Measurement audit: {failures} failed model calls and {fallbacks} fallback judgments logged across all attempts; {len(missing)} unmeasurable candidates. '
                          'M denotes unmeasurable, not a failed statistical test. See the saved audit for final model allocations.') if rid.startswith('P') and (failures or missing) else ''
        runs.append({"run_id":rid,"label":LABELS[rid],"cfg":cfg,"root":root,"bank":bank,"selection":selected,"rows":rows,
                     "measurement_note":measurement_note,
                     "count":{"run_id":rid,"run":("Observed contrast" if rid=="ARCHIVE" else LABELS[rid]),"proposed":len(bank),"measured":len(results),"validated":tiers["confirmed"],"suggestive_only":tiers["suggestive"],"uncorrected_only":tiers["uncorrected"],"neither_tier":tiers["not_validated"],"unmeasurable":len(missing)}})
    # Same reserved texts, and five explicitly different shuffle indices.
    uid_lists=[json.loads((r["root"]/"00_partition.json").read_text())["measurement_uids"] for r in runs]
    assert all(u==uid_lists[0] for u in uid_lists)
    return runs


def tex_note(note):return tex(note).replace("p < .05",r"\(p<.05\)")


def require_complete_measurement(runs):
    incomplete=[r['run_id'] for r in runs if r['count']['proposed']!=r['count']['measured']]
    if incomplete:
        raise ValueError('Cannot finalize the main exhibits with unmeasured candidates: '+', '.join(incomplete)+'. Resolve operationalization or classification failures first; preserve initial attempts in the repair history.')


def placebo_tex(counts):
    lines=["% Main-paper Table 1; standard LaTeX only. Input outside another table.",r"\begin{table}[!htbp]\centering",
           r"\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont",
           r"\caption{Full-pipeline placebo tests}\label{tab:placebo-validation}",
           r"\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.25}",
           r"\begin{tabular*}{\linewidth}{@{\extracolsep{\fill}}lccccc@{}}\hline",
           r"Run & Proposed & Measured & \shortstack{Validated\\(5\% FDR)} & \shortstack{Suggestive only\\(10\% FDR)} & \shortstack{Uncorrected\\only}"+r" \\\hline"]
    for i,row in enumerate(counts):
        lines.append(tex(row["run"])+" & "+" & ".join(str(row[k]) for k in ["proposed","measured","validated","suggestive_only","uncorrected_only"])+r" \\")
        if i==0:lines.append(r"\hline")
    lines += [r"\hline\end{tabular*}\par\vspace{4pt}",r"\noindent\begin{minipage}{\linewidth}\def\baselinestretch{1}\fontsize{8}{9.6}\selectfont",
              r"\textit{Notes.} "+tex_note(PLACEBO_NOTE),r"\end{minipage}\end{table}"]
    return "\n".join(lines)+"\n"


def crosswalk_tex(rows, counts, appendix=False):
    marks={"validated":r"\PaperStabilityCheck\raisebox{.4ex}{\fontsize{6}{6}\selectfont *}",
           "proposed":r"\PaperStabilityCheck","broader":r"\(\sim\)","absent":r"\(-\)"}
    check=CHECK.replace("DValidationCheck","PaperStabilityCheck")
    begin=[r"\begingroup",check.strip(),r"\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont",
           r"\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.15}",
           r"\edef\PaperStabilityRunWidth{\the\dimexpr.11\linewidth\relax}",
           r"\edef\PaperStabilityLabelWidth{\the\dimexpr\linewidth-\PaperStabilityRunWidth*4-\tabcolsep*8\relax}",
           r"\def\PaperStabilityCell#1{\makebox[\PaperStabilityRunWidth][c]{#1}}"]
    spec=r"{@{}p{\PaperStabilityLabelWidth}*{4}{p{\PaperStabilityRunWidth}}@{}}"
    header=(r"Substantive theme & \PaperStabilityCell{\shortstack{Main\\run}} & \PaperStabilityCell{\shortstack{Same-pool\\repeat}} & \PaperStabilityCell{\shortstack{Default\\pool}} & \PaperStabilityCell{\shortstack{OpenAI\\only}}"+r" \\\hline")
    title="All descriptive themes across real runs" if appendix else STABILITY_TITLE
    label="tab:validation-all-themes" if appendix else "tab:stability-crosswalk"
    lines=[]
    if not appendix:lines += ["% Main-paper Table 2; standard LaTeX only.",r"\begin{table}[!htbp]\centering",r"\caption{"+title+r"}\label{"+label+"}"]
    lines+=begin
    if appendix:
        lines += [r"\begin{longtable}"+spec,r"\caption{"+title+r"}\label{"+label+r"}\\",r"\hline",header,r"\endfirsthead",r"\multicolumn{5}{l}{\textit{All descriptive themes (continued)}}\\\hline",header,r"\endhead",r"\hline\endfoot\hline\endlastfoot"]
    else:lines += [r"\begin{tabular}"+spec,r"\hline",header]
    if not appendix:
        for name,key in [("Candidates proposed","proposed"),("Candidates measured","measured"),("Candidates validated (5% FDR)","validated")]:
            lines.append(r"{\raggedright "+tex(name)+r"\par} & "+" & ".join(r"\PaperStabilityCell{\textbf{"+str(counts[rid][key])+"}}" for rid in REAL)+r" \\")
        lines.append(r"\hline")
    for row in rows:
        lines.append(r"{\raggedright "+tex(row["theme"])+r"\par} & "+" & ".join(r"\PaperStabilityCell{"+marks[row[rid]]+"}" for rid in REAL)+r" \\")
    lines += [r"\hline\end{longtable}" if appendix else r"\hline\end{tabular}",r"\par\vspace{4pt}",
              r"\noindent\begin{minipage}{\linewidth}\def\baselinestretch{1}\fontsize{8}{9.6}\selectfont",
              r"\PaperStabilityCheck\ focused feature proposed; * also validated (5\% FDR); \(\sim\) broader question only; \(-\) not proposed.",
              r"\par\textit{Notes.} "+tex(STABILITY_NOTE),r"\end{minipage}\endgroup"]
    if not appendix:lines.append(r"\end{table}")
    return "\n".join(lines)+"\n"


def standalone(body, appendix=False, table_index=1):
    head=r"\documentclass[letterpaper,12pt]{article}"+"\n"
    if appendix:head+=r"\usepackage{longtable}"+"\n"+r"\usepackage{chngcntr}"+"\n"
    head+=r"\begin{document}"+"\n"
    if not appendix and table_index>1:head+=r"\setcounter{table}{"+str(table_index-1)+"}\n"
    if appendix:head+=r"\appendix\counterwithin{table}{section}\renewcommand{\thetable}{\thesection\arabic{table}}\setcounter{section}{3}"+"\n"
    return head+body+"\n"+r"\end{document}"+"\n"


def build(original,theme,extra,out,repair=None):
    original,theme,extra,out=Path(original),Path(theme),Path(extra),Path(out)
    runs=load_runs(original,extra,repair)
    require_complete_measurement(runs)
    out.mkdir(parents=True,exist_ok=True)
    figs=out/"FigsTables";apps=out/"appendices";previews=out/"working"/"previews"
    for p in [figs,apps,previews]:p.mkdir(parents=True,exist_ok=True)
    byid={r["run_id"]:r for r in runs}
    placebo_counts=[byid[rid]["count"] for rid in ["ARCHIVE"]+PLACEBOS]
    real_counts={rid:byid[rid]["count"] for rid in REAL}
    all_themes=list(csv.DictReader((theme/"appendix_all_themes.csv").open()))
    all_themes=[{k:r[k] for k in ["theme_id","theme"]+REAL} for r in all_themes]
    links=[r for r in csv.DictReader((theme/'appendix_candidate_links.csv').open()) if r['run_id'] in REAL]
    saved={(run['run_id'],r['candidate_id']):r for run in runs for r in run['rows']}
    for link in links:
        result=saved[link['run_id'],link['candidate_id']]
        assert link['tier']==result['tier']
        assert float(link['mean_effect'])==result['mean_effect'] and float(link['perm_p'])==result['perm_p']
    for row in all_themes:
        for rid in REAL:
            group=[l for l in links if l['theme_id']==row['theme_id'] and l['run_id']==rid]
            valid=[l for l in group if l['tier']=='confirmed']
            expected='check' if any(l['link_type']=='focused' for l in valid) else 'composite' if valid else 'proposed' if group else 'absent'
            assert row[rid]==expected,(row['theme_id'],rid,row[rid],expected)
    main_ids={r['theme_id'] for r in all_themes if any(r[rid] in {'check','composite'} for rid in REAL)}
    # Keep exactly the same 16 rows; only labels and symbol meanings change.
    assert len(main_ids)==16 and len(all_themes)==21
    source_labels={r['theme_id']:r['theme'] for r in all_themes}
    all_themes=recurrence_rows(all_themes,links)
    main_themes=[r for r in all_themes if r['theme_id'] in main_ids]
    write_csv(figs/"table_1_placebos.csv",placebo_counts)
    write_csv(figs/"table_2_stability_crosswalk.csv",main_themes)
    t1,t2=placebo_tex(placebo_counts),crosswalk_tex(main_themes,real_counts)
    (figs/"table_1_placebos.tex").write_text(t1)
    (figs/"table_2_stability_crosswalk.tex").write_text(t2)
    for index,(name,body) in enumerate([("table_1_placebos_preview.tex",t1),("table_2_stability_preview.tex",t2)],1):
        (previews/name).write_text(standalone(body,table_index=index))
    # One candidate-level audit directory, independent of the manuscript layout.
    full_csv=[]
    for run in runs:
        rid=run["run_id"];dest=apps/"data"/"validation_runs"/rid;dest.mkdir(parents=True,exist_ok=True)
        for name in ["02_consolidated.json","04_selected.json"]:shutil.copy2(run["root"]/name,dest/name)
        cfg={k:v for k,v in run["cfg"].items() if k not in {"dataset","output_dir","base_dir","providers"}}
        (dest/"run_settings.json").write_text(json.dumps(cfg,indent=2)+"\n")
        flat=[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in run["rows"]]
        full_csv+=flat;write_csv(dest/"full_results.csv",flat)
    write_csv(apps/"data"/"all_validation_results.csv",full_csv)
    write_csv(apps/"data"/"all_run_counts.csv",[r["count"] for r in runs])
    write_csv(apps/'data'/'table_2_theme_links.csv',links)
    write_csv(apps/'data'/'appendix_all_themes.csv',all_themes)
    (apps/'data'/'theme_display_labels.json').write_text(json.dumps({tid:{'source_label':source_labels[tid],'display_label':name} for tid,name in DISPLAY_LABELS.items()},indent=2)+'\n')
    cells=[]
    for row in all_themes:
        for rid in REAL:
            group=[l for l in links if l['theme_id']==row['theme_id'] and l['run_id']==rid]
            cells.append({'theme_id':row['theme_id'],'theme':row['theme'],'run_id':rid,'marker':row[rid],
                          'focused_proposed':sum(l['link_type']=='focused' for l in group),
                          'focused_validated':sum(l['link_type']=='focused' and l['tier']=='confirmed' for l in group),
                          'broader_proposed':sum(l['link_type']=='composite' for l in group),
                          'broader_validated':sum(l['link_type']=='composite' and l['tier']=='confirmed' for l in group)})
    write_csv(apps/'data'/'theme_cell_audit.csv',cells)
    for name in ['semantic_link_specification.json','appendix_candidate_links.csv']:
        if (theme/name).exists():shutil.copy2(theme/name,apps/'data'/name)
    # A compact appendix retains every numerical result; verbatim text lives in
    # the accompanying catalogue rather than nine repeated long catalogues.
    total=len(full_csv)
    from build_compact_appendix_d import build as compact_appendix
    compact_report=compact_appendix(apps/'data',apps/'appendix_D.tex',previews/'appendix_D_preview.tex')
    assert compact_report['candidates']==total
    pdf_tables(figs,placebo_counts,main_themes,real_counts)
    html_tables(figs,placebo_counts,main_themes,real_counts)
    manifest={"status":"completed_and_source_checked","runs":ORDER,"total_candidates":total,
              "tier_counts":{r["run_id"]:r["count"] for r in runs},"table_2_themes":len(main_themes),
              "placebo_recipe":"Reference model pool, unique shuffle indices 0-4; unchanged reservation and statistical settings.",
              "source_sha256":{r["run_id"]:{name:digest(r["root"]/name) for name in ["00_config.json","02_consolidated.json","04_selected.json"]} for r in runs},
              "frozen_theme_links_sha256":digest(theme/"semantic_link_specification.json"),"builder_sha256":digest(__file__),
              "crosswalk_display":{"validated":"focused feature proposed and validated at 5% FDR","proposed":"focused feature proposed","broader":"only represented by broader question","absent":"not proposed"},
              "display_labels":DISPLAY_LABELS,"same_main_theme_ids":sorted(main_ids),"appendix_layout":compact_report}
    manifest['source_artifact_paths']={r['run_id']:str(r['root']) for r in runs}
    (apps/"data"/"validation_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (figs/"README.txt").write_text("Main-paper outputs\n\nTable 1: table_1_placebos.tex / .pdf / .html / .csv\nTable 2: table_2_stability_crosswalk.tex / .pdf / .html / .csv\n\nInput Table 1 before Table 2; LaTeX numbers captions automatically. Neither table requires additional packages. Appendix D consolidates settings, the full crosswalk, and all 317 numerical results in three tables; it requires longtable. Exact questions and definitions are in appendices/data/validation_feature_catalogue.csv and its searchable HTML companion.\n")
    print(json.dumps({"total_candidates":total,"counts":manifest["tier_counts"],"out":str(out)},indent=2))


def pdf_tables(out,placebos,themes,counts):
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph
    ink=colors.HexColor("#26332d")
    text_style=ParagraphStyle("cell",fontName="Times-Roman",fontSize=9,leading=11,textColor=ink)
    note_style=ParagraphStyle("note",parent=text_style,fontSize=8,leading=10)
    def paragraph(c,text,x,y,w,style=text_style):
        p=Paragraph(escape(text),style);_,h=p.wrap(w,400);p.drawOn(c,x,y-h);return h
    def rule(c,y,x=40,w=532):c.setStrokeColor(ink);c.setLineWidth(.65);c.line(x,y,x+w,y)
    c=canvas.Canvas(str(out/"table_1_placebos.pdf"),pagesize=(612,792));c.setTitle("Table 1. Full-pipeline placebo tests")
    c.setFillColor(ink);c.setFont("Times-Bold",14);c.drawString(40,750,"Table 1. Full-pipeline placebo tests")
    c.setFont("Times-Roman",10);c.drawString(40,731,"Women versus men within tall hierarchies")
    widths=[132,70,70,83,87,90];centers=[];pos=40
    for w in widths:centers.append(pos+w/2);pos+=w
    y=702;rule(c,y)
    for i,words in enumerate([["Run"],["Proposed"],["Measured"],["Validated","(5% FDR)"],["Suggestive only","(10% FDR)"],["Uncorrected","only"]]):
        c.setFont("Times-Bold",9)
        for j,word in enumerate(words):
            if i==0:c.drawString(44,y-18-j*11,word)
            else:c.drawCentredString(centers[i],y-18-j*11,word)
    y-=40;rule(c,y)
    for i,r in enumerate(placebos):
        c.setFont("Times-Roman",10);c.drawString(44,y-20,r["run"])
        for j,k in enumerate(["proposed","measured","validated","suggestive_only","uncorrected_only"],1):c.drawCentredString(centers[j],y-20,str(r[k]))
        y-=31
        if i==0:rule(c,y)
    rule(c,y);paragraph(c,"Notes. "+PLACEBO_NOTE,40,y-12,532,note_style);c.save()
    c=canvas.Canvas(str(out/"table_2_stability_crosswalk.pdf"),pagesize=(612,792));c.setTitle("Table 2. "+STABILITY_TITLE)
    c.setFillColor(ink);c.setFont("Times-Bold",14);c.drawString(40,750,"Table 2. "+STABILITY_TITLE)
    c.setFont("Times-Roman",10);c.drawString(40,731,"Women versus men within tall hierarchies")
    label_width=296;cw=(532-label_width)/4
    y=705;rule(c,y)
    c.setFont("Times-Bold",9);c.drawString(44,y-25,"Substantive theme")
    for i,words in enumerate([["Main run"],["Same-pool","repeat"],["Default","pool"],["OpenAI only"]]):
        for j,w in enumerate(words):c.drawCentredString(40+label_width+(i+.5)*cw,y-18-j*11,w)
    y-=42;rule(c,y)
    for name,key in [("Candidates proposed","proposed"),("Candidates measured","measured"),("Candidates validated (5% FDR)","validated")]:
        c.setFont("Times-Roman",9);c.drawString(44,y-14,name)
        c.setFont("Times-Bold",10)
        for i,rid in enumerate(REAL):c.drawCentredString(40+label_width+(i+.5)*cw,y-14,str(counts[rid][key]))
        y-=22
    rule(c,y)
    def mark(value,cx,cy):
        c.setFillColor(ink);c.setStrokeColor(ink);c.setLineWidth(.9)
        if value in {"proposed","validated"}:
            p=c.beginPath();p.moveTo(cx-3,cy);p.lineTo(cx-1,cy-3);p.lineTo(cx+4,cy+3.5);c.drawPath(p)
            if value=='validated':c.setFont('Times-Bold',8);c.drawString(cx+5,cy+3,'*')
        elif value=="broader":c.setFont("Times-Bold",12);c.drawCentredString(cx,cy-3,"~")
        else:c.line(cx-2.5,cy,cx+2.5,cy)
    for r in themes:
        paragraph(c,r["theme"],44,y-6,label_width-10)
        for i,rid in enumerate(REAL):mark(r[rid],40+label_width+(i+.5)*cw,y-12)
        y-=24
        c.setStrokeColor(colors.HexColor("#dce1dc"));c.setLineWidth(.25);c.line(40,y,572,y)
    rule(c,y);y-=18
    for value,cx,label in [("proposed",44,"Focused feature proposed"),("validated",192,"Also validated (5% FDR)"),("broader",360,"Broader question only"),("absent",492,"Not proposed")]:
        mark(value,cx,y);c.setFont("Times-Roman",7);c.drawString(cx+(12 if value=='validated' else 7),y-2,label)
    h=paragraph(c,"Notes. "+STABILITY_NOTE,40,y-15,532,note_style)
    assert y-15-h>30
    c.save()


def html_tables(out,placebos,themes,counts):
    style="body{font:16px Georgia;color:#26332d;max-width:1050px;margin:40px auto;padding:20px}table{width:100%;border-collapse:collapse;border-top:2px solid #26332d;border-bottom:2px solid #26332d}th,td{padding:11px 8px;text-align:center;border-bottom:1px solid #dde2dc}th:first-child,td:first-child{text-align:left}thead{background:#f1f4ef}.notes{font-size:13px;line-height:1.5}.baseline{border-bottom:1px solid #26332d}"
    def page(title,body):return "<!doctype html><html><head><meta charset='utf-8'><title>"+title+"</title><style>"+style+"</style></head><body><h1>"+title+"</h1><p>Women versus men within tall hierarchies</p>"+body+"</body></html>"
    body="<table><thead><tr>"+"".join("<th>"+h+"</th>" for h in ["Run","Proposed","Measured","Validated<br>(5% FDR)","Suggestive only<br>(10% FDR)","Uncorrected only"])+"</tr></thead><tbody>"
    for i,r in enumerate(placebos):body+="<tr"+(" class='baseline'" if i==0 else "")+"><td>"+r["run"]+"</td>"+"".join("<td>"+str(r[k])+"</td>" for k in ["proposed","measured","validated","suggestive_only","uncorrected_only"])+"</tr>"
    body+="</tbody></table><p class='notes'>"+escape(PLACEBO_NOTE)+"</p>"
    (out/"table_1_placebos.html").write_text(page("Table 1. Full-pipeline placebo tests",body))
    body="<table><thead><tr><th>Substantive theme</th>"+"".join("<th>"+LABELS[r]+"</th>" for r in REAL)+"</tr></thead><tbody>"
    for label,key in [("Candidates proposed","proposed"),("Candidates measured","measured"),("Candidates validated (5% FDR)","validated")]:body+="<tr><td>"+label+"</td>"+"".join("<td><b>"+str(counts[r][key])+"</b></td>" for r in REAL)+"</tr>"
    marks={"validated":"✓<sup>*</sup>","proposed":"✓","broader":"~","absent":"-"}
    for r in themes:body+="<tr><td>"+escape(r["theme"])+"</td>"+"".join("<td>"+marks[r[rid]]+"</td>" for rid in REAL)+"</tr>"
    body+="</tbody></table><p class='notes'>✓ Focused feature proposed; * also validated (5% FDR); ~ broader question only; - not proposed.</p><p class='notes'>"+escape(STABILITY_NOTE)+"</p>"
    (out/"table_2_stability_crosswalk.html").write_text(page("Table 2. "+STABILITY_TITLE,body))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original",required=True);p.add_argument("--theme",required=True);p.add_argument("--extra-batch",required=True);p.add_argument("--out",required=True)
    p.add_argument('--repair',help='completed second-version P03 artifact directory')
    a=p.parse_args();build(a.original,a.theme,a.extra_batch,a.out,a.repair)
