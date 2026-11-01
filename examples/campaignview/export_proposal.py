"""Export Figure 2 and the complete CampaignView appendix from the saved run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def tex(value):
    escapes = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
               "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
               "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(escapes.get(c, c) for c in str(value))


def stats(row):
    return (f"$d_1={100*row['d1']:+.2f},\\ d_2={100*row['d2']:+.2f},\\ "
            f"\\bar d={100*row['mean_effect']:+.2f};\\ p={row['perm_p']:.4f}$")


def figure(selected, display):
    by_id = {r["candidate_id"]: r for r in selected["results"]}
    shown = [by_id[f["candidate_id"]] for f in display["features"]]
    if len(shown) != 8 or len({r["candidate_id"] for r in shown}) != 8 or not all(r["validated"] for r in shown):
        raise ValueError("Figure 2 must show eight distinct validated features")
    blocks = []
    for row in shown:
        party = "Republicans" if row["mean_effect"] > 0 else "Democrats"
        blocks.append(
            r"\noindent\textbf{" + tex(row["feature_name"]) + f"}} (more common among {party})" + r"\\[2pt]" + "\n"
            + r"{\fontsize{9}{10}\selectfont " + stats(row) + r"}\\[2pt]" + "\n"
            + r"\textit{Definition.} " + tex(row["definition"]) + r"\par" + "\n"
            + r"\textit{Question.} " + tex(row["classification_question"]) + r"\par")
    separator = "\n" + r"\vspace{5pt}\hrule height .25pt\vspace{5pt}" + "\n"
    return r"""\FloatBarrier\clearpage
\newgeometry{left=1.5cm,right=1.5cm,bottom=1.25cm,top=1.5cm}
\begin{figure}[p]
\centering
\caption{Selected pipeline outputs from CampaignView: Republican and Democratic candidate biographies.}
\label{fig:pipeline-outputs}
\setlength{\fboxsep}{5pt}
\setlength{\fboxrule}{.5pt}
\fbox{\begin{minipage}{\dimexpr\linewidth-2\fboxsep-2\fboxrule\relax}
\fontsize{9.5}{11}\selectfont
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
""" + separator.join(blocks) + r"""
\end{minipage}}
\caption*{\scriptsize \textit{Notes:} Eight of the 50 validated features are shown, selected to illustrate qualifications and self-presentation rather than to rank effect sizes. Names, definitions, and questions are reproduced verbatim. Effects are percentage-point differences (Republican minus Democratic biographies); $d_1$ and $d_2$ refer to the two held-out halves and $\bar d=(d_1+d_2)/2$. Measurement used 600 biographies (300 per party), model rotation, and 1,440 permutations. All shown features pass the Benjamini--Hochberg correction at $q=.05$ across 72 tested candidates and have nonzero same-sign half-effects. Reported $p$ values are unadjusted permutation p-values.}
\end{figure}

\FloatBarrier\clearpage\restoregeometry
"""


def appendix(selected):
    intro = r"""\FloatBarrier\clearpage
\section{Complete CampaignView Results}\label{app:campaignview-results}
This appendix reports all 72 candidate features from the CampaignView analysis in Section 3 of the proposal, including the eight selected examples in Figure 2. The data are campaign-website biographies of Republican and Democratic candidates for the U.S. House of Representatives in 2018--2022 \citep{Porter2025NatSciDat_Campaignview}. To avoid overlap, records sharing an FEC candidate ID, BIOGUIDE ID, normalized full name, or normalized whole biography were linked before splitting; one earliest-year biography was retained per linked group, and mixed-party groups were excluded. This yielded 3,961 biographies: 2,049 Republican and 1,912 Democratic. The pipeline generated 193 proposed hypotheses using 3,361 discovery biographies; 600 additional biographies (300 per party) were reserved for measurement. Recorded identities and normalized texts do not overlap across discovery or either measurement half. Matching rules, inclusion records, and an offline overlap check are included in the code package.

Of the 72 candidates, 50 passed the primary 5\% false discovery rate threshold, one additional feature passed only the exploratory 10\% threshold, and 21 passed neither threshold. Feature names, definitions, and classification questions are reproduced verbatim below. Where a question uses A/B notation, A and B refer to the Republican and Democratic sides of the contrast, respectively.

Effects are percentage-point differences in feature prevalence: Republican minus Democratic biographies. Positive values indicate greater prevalence among Republicans, and negative values indicate greater prevalence among Democrats. The two held-out half-sample effects are $d_1$ and $d_2$; their mean is $\bar d=(d_1+d_2)/2$. Reported p-values are unadjusted permutation p-values from 1,440 permutations. Both selection thresholds also require nonzero, same-sign effects in the two halves; a candidate that fails this requirement receives $p=1$. Values are rounded for display; selection uses full precision.
"""
    sections = []
    specs = [("confirmed", "Validated features", "Validated CampaignView features", "validated"),
             ("suggestive", "Additional features at the exploratory threshold",
              "Additional CampaignView features at the exploratory threshold", "exploratory"),
             ("not_validated", "Features that passed neither threshold",
              "CampaignView features that passed neither threshold", "not-validated")]
    covered = []
    for tier, title, caption, label in specs:
        lines = [r"\subsection{" + title + "}",
                 r"\begingroup\def\baselinestretch{1}\fontsize{10}{12}\selectfont",
                 r"\setlength{\tabcolsep}{0pt}\renewcommand{\arraystretch}{1}",
                 r"\begin{longtable}{@{}>{\raggedright\arraybackslash}p{\linewidth}@{}}",
                 r"\caption{" + caption + r"}\label{tab:campaignview-" + label + r"}\\",
                 r"\hline\endfirsthead",
                 r"\multicolumn{1}{@{}l@{}}{\textit{" + caption + r" (continued)}}\\\hline\endhead",
                 r"\hline\multicolumn{1}{r}{\footnotesize Continued on next page}\\\endfoot\hline\endlastfoot"]
        for i, row in enumerate(selected["results"], 1):
            if row["tier"] != tier:
                continue
            covered.append(row["candidate_id"])
            lines.extend([r"\textbf{" + f"{i}. " + tex(row["feature_name"]) + r"}\par",
                          r"\textit{Definition.} " + tex(row["definition"]) + r"\par",
                          r"\textit{Question.} " + tex(row["classification_question"]) + r"\par",
                          stats(row) + r" \\[7pt]\hline"])
        lines.append(r"\end{longtable}\endgroup")
        sections.append("\n".join(lines))
    if set(covered) != {r["candidate_id"] for r in selected["results"]} or len(covered) != 72:
        raise ValueError("The appendix must cover all 72 candidates exactly once")
    return intro + "\n\n" + "\n\n\\clearpage\n".join(sections) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    selected = json.loads((HERE / "saved_unique/real_r1/04_selected.json").read_text(encoding="utf-8"))
    display = json.loads((HERE / "display_features.unique.json").read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "campaignview_figure.tex").write_text(figure(selected, display), encoding="utf-8")
    (args.out_dir / "campaignview_appendix.tex").write_text(appendix(selected), encoding="utf-8")
    print("Exported eight display features and all 72 appendix features from the saved results.")


if __name__ == "__main__":
    main()
