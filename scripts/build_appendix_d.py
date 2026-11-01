"""Make a single drop-in Appendix D consistent with the paper's Appendices A-C.

Only longtable is added to their existing package requirements. Statistical
results and stable feature IDs are copied from the previously exported run data.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_validation_latex import RUNS, LABELS, APPENDIX_NOTES, tex, run_tex, summary_tex
from build_theme_crosswalk import NOTES


INTRO = (
    "All 208 consolidated candidates from the six runs are reported below. Effects are "
    "percentage-point differences: women minus men for real runs, shuffled focal minus "
    "reference labels for placebos. The two half-sample effects and their average use "
    "800 evaluation responses, with 200 per active group in each half. Real runs reuse "
    "the same responses. All runs use 5,000 permutations. "
    "V denotes 5% FDR validation; S denotes 10% FDR only; U denotes the uncorrected, "
    "same-sign p < .05 tier outside both FDR tiers; N denotes none of these. "
    "A p-value of 1 can reflect failure of the same-sign gate. Feature-ID prefixes "
    "A--F identify the six runs in the order shown. Definitions and classification "
    "questions retain their original wording."
)

CHECK = r"""\providecommand{\DValidationCheck}{\ifdefined\checkmark\(\checkmark\)\else{\setlength{\unitlength}{1pt}\linethickness{0.65pt}\begin{picture}(8,8)\qbezier(0,3)(1,2)(2,1)\qbezier(2,1)(4,4)(6,7)\end{picture}}\fi}
"""


def portable(text):
    """Remove array/tabularx/booktabs/symbol-font dependencies from run tables."""
    text=text.replace(r">{\raggedright\arraybackslash}", "")
    text=text.replace(r"\begin{tabularx}{\linewidth}{@{}Xrrrrr@{}}",r"\begin{tabular}{@{}lrrrrr@{}}")
    text=text.replace(r"\end{tabularx}",r"\end{tabular}")
    for command in [r"\toprule",r"\midrule",r"\bottomrule"]:
        text=text.replace(command,r"\hline")
    text=text.replace(r"\begingroup\small",r"\begingroup\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont")
    text=text.replace(r"\centering\small",r"\centering\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont")
    text=text.replace(r"\subsection*{",r"\subsection{")
    text=text.replace(r"\subsubsection*{",r"\subsubsection{")
    return text


def themes_tex(rows):
    marks={"check":r"\DValidationCheck","composite":r"\(\sim\)","proposed":r"\(\circ\)","absent":r"\(-\)"}
    head=(r"Theme & \DValidationCell{\shortstack{Main\\run}} & \DValidationCell{Repeat} & \DValidationCell{\shortstack{Default\\pool}} & \DValidationCell{\shortstack{OpenAI\\only}} & \DValidationCell{\shortstack{Placebo\\1}} & \DValidationCell{\shortstack{Placebo\\2}}"+r" \\\hline")
    lines=[r"\clearpage\subsection{Complete descriptive theme crosswalk}",
           r"\begingroup\def\baselinestretch{1}\fontsize{9}{10.5}\selectfont",
           r"\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.1}",
           r"\edef\DValidationRunWidth{\the\dimexpr.075\linewidth\relax}",
           r"\edef\DValidationLabelWidth{\the\dimexpr.43\linewidth\relax}",
           r"\def\DValidationCell#1{\makebox[\DValidationRunWidth][c]{#1}}",
           r"\begin{longtable}{@{}p{\DValidationLabelWidth}*{4}{p{\DValidationRunWidth}}|*{2}{p{\DValidationRunWidth}}@{}}",
           r"\caption{All descriptive themes across real and placebo runs}\label{tab:validation-all-themes}\\",
           r"\hline",r" & \multicolumn{4}{c|}{Real contrast} & \multicolumn{2}{c}{Label placebos}"+r" \\",head,r"\endfirsthead",
           r"\multicolumn{7}{l}{\textit{Complete descriptive theme crosswalk (continued)}}\\\hline",head,r"\endhead",
           r"\hline\endfoot\hline\endlastfoot"]
    for row in rows:
        lines.append(r"{\raggedright "+tex(row["theme"])+r"\par} & "+" & ".join(r"\DValidationCell{"+marks[row[rid]]+"}" for rid in RUNS)+r" \\")
    lines += [r"\end{longtable}\endgroup",
              r"\par{\footnotesize \DValidationCheck\ focused measure validates; \(\sim\) composite measure validates; \(\circ\) proposed only; \(-\) not proposed. "+tex(NOTES)+"}\n"]
    return "\n".join(lines)+"\n"


def build(source,theme,out):
    source,theme,out=Path(source),Path(theme),Path(out)
    out.mkdir(parents=True,exist_ok=True)
    data=[]
    with (source/"all_runs_full_results.csv").open() as f:
        csv_rows=list(csv.DictReader(f))
    byid={(r["run_id"],r["candidate_id"]):r for r in csv_rows}
    for index,rid in enumerate(RUNS):
        root=source/"data"/rid
        bank=json.loads((root/"02_consolidated.json").read_text())["candidates"]
        selection=json.loads((root/"04_selected.json").read_text())
        cfg=json.loads((root/"run_settings.json").read_text())
        rows=[]
        for result in selection["results"]:
            previous=byid[(rid,result["candidate_id"])]
            assert previous["tier"]==result["tier"]
            for k in ["d1","d2","mean_effect","perm_p"]:assert float(previous[k])==result[k]
            rows.append({"run_id":rid,"exhibit_id":previous["exhibit_id"],**result})
        assert {r["candidate_id"] for r in rows}=={c["candidate_id"] for c in bank}
        data.append({"run_id":rid,"label":LABELS[index],"cfg":cfg,"selection":selection,"bank":bank,"rows":rows})
    assert sum(len(r["rows"]) for r in data)==len(csv_rows)==208
    with (theme/"appendix_all_themes.csv").open() as f: themes=list(csv.DictReader(f))
    assert len(themes)==21
    summary=summary_tex(data).replace(tex(APPENDIX_NOTES),tex(INTRO).replace("p < .05",r"\(p<.05\)"))
    intro=("% Appendix D. Add \\usepackage{longtable} in the manuscript preamble.\n"
           "% Input after Appendix C; inherits section/table numbering and font family.\n"
           "% No document class, appendix reset, external files, or figure assets.\n"
           r"\section{Validation and complete run outputs}"+"\n"+r"\label{app:validation}"+"\n\n"+CHECK+"\n")
    fragment=intro+portable(summary)+"\n"+themes_tex(themes)+"\n"+"\n".join(portable(run_tex(run)) for run in data)
    for token in [r"\begin{tabularx}",r"\arraybackslash",r"\checkmark",r"\toprule",r"\midrule",r"\bottomrule",r"\input",r"\includegraphics"]:
        assert token not in fragment, token
    assert len(re.findall(r"\{\\ttfamily\\footnotesize c\\_",fragment))==208
    assert len(re.findall(r"\\caption\{",fragment))==14
    (out/"appendix_D.tex").write_text(fragment)
    preview=(r"\documentclass[letterpaper,12pt]{article}"+"\n"+r"\usepackage{longtable}"+"\n"+
             r"\usepackage{chngcntr}"+"\n"+r"\begin{document}"+"\n"+r"\appendix"+"\n"+
             r"\counterwithin{table}{section}"+"\n"+r"\renewcommand{\thetable}{\thesection\arabic{table}}"+"\n"+
             r"\setcounter{section}{3}"+"\n"+fragment+"\n"+r"\end{document}"+"\n")
    (out/"appendix_D_preview.tex").write_text(preview)
    verification={"candidate_count":208,"theme_count":21,"table_count":14,
                  "additional_packages":["longtable"],"section_label":"app:validation",
                  "numbering":"inherits appendix section and table counters; D1-D14 when input after Appendix C",
                  "source_sha256":hashlib.sha256((source/"all_runs_full_results.csv").read_bytes()).hexdigest(),
                  "appendix_D_sha256":hashlib.sha256(fragment.encode()).hexdigest(),
                  "checks":"All numeric results and tiers match saved outputs; every final candidate retained; 14 table captions; no external file dependencies."}
    (out/"verification.json").write_text(json.dumps(verification,indent=2)+"\n")
    print(json.dumps(verification,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",required=True)
    parser.add_argument("--theme",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    build(args.source,args.theme,args.out)
