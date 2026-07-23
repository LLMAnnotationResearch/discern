# Sample output — Quarterly Journal of Economics vs. Journal of Political Economy

A real `discern` run distinguishing the abstracts of two economics journals,
the **Quarterly Journal of Economics** (QJE) and the **Journal of Political Economy** (JPE).
Abstracts were pulled from [OpenAlex](https://openalex.org) (open scholarly
metadata); the raw abstract text is **not** included here — this page shows only
`discern`'s output.

- **Input:** 734 published abstracts (314 QJE, 420 JPE), one text column, one binary group label.
- **Discovery:** 276 blinded hypotheses → 35 candidates.
- **Measurement:** every candidate scored on a held-out sample of 300 abstracts (150/group), 2000-permutation null.
- **Result:** **21 features validated** at FDR 0.05 (+ 1 suggestive at FDR 0.1), grouped into 5 navigation themes.

Discovery never saw the measurement sample. The gate requires same-sign replication
across two independent data halves, a permutation null, and Benjamini–Hochberg FDR
correction — so what survives is a genuine, held-out contrast, not a plausible-sounding guess.

The two sections below are exactly what the tool writes: first the **feature summary**
(every validated feature with its effect size and direction), then the **themes**
(a temperature-0 presentation layer that only groups the features — it changes no statistic).

---

# v2 run: real_r0  (real)

- prompt_version: discern-1
- measurement: rotate, n=300 (150/group), permutations=2000, FDR=0.05
- discovery: 276 hypotheses -> 35 candidates -> **21 validated** (FDR 0.05) + **1 suggestive** (exploratory FDR 0.1)

**Direction key:** + (focal_higher) = more prevalent among 'Quarterly Journal of Economics'; - (focal_lower) = more prevalent among 'Journal of Political Economy'.
d1/d2 = the two independent data-half effects (validation requires the same sign in both). A positive pp value = the feature is more prevalent among 'Quarterly Journal of Economics'; negative = more prevalent among 'Journal of Political Economy'.

## Validated features (FDR 0.05)

### Integration of Multiple Data Sources or Methods  (+35 pp — more common among Quarterly Journal of Economics, p=0.000)
*The abstract describes the integration of multiple data sources or mixed methods (e.g., combining administrative data, surveys, and experiments).*
Q: Does the abstract describe the integration of multiple data sources or mixed methods?
d1=+40pp  d2=+29pp  id=c_b209267b4355e738

### Novel Data Collection  (+33 pp — more common among Quarterly Journal of Economics, p=0.000)
*Whether the abstract uses newly collected or novel administrative data sources.*
Q: Does the abstract use newly collected or novel administrative data sources?
d1=+35pp  d2=+31pp  id=c_f571915c274dee1f

### Use of Quasi-Experimental or Experimental Methods  (+30 pp — more common among Quarterly Journal of Economics, p=0.000)
*Whether the abstract describes the use of quasi-experimental or experimental methods for causal identification (e.g., randomized controlled trials, natural experiments, regression discontinuity, instrumental variables).*
Q: Does the abstract describe the use of quasi-experimental or experimental methods for causal identification?
d1=+40pp  d2=+20pp  id=c_cfb77e12107b1c2b

### Explicit Mention of Data Sources  (+27 pp — more common among Quarterly Journal of Economics, p=0.000)
*The abstract explicitly mentions the use of specific data sources (e.g., administrative records, tax data, patent data, firm-level data).*
Q: Does the abstract explicitly mention the use of specific data sources?
d1=+33pp  d2=+20pp  id=c_dcc1d11cc4587428

### Empirical vs Theoretical Orientation  (+27 pp — more common among Quarterly Journal of Economics, p=0.000)
*Whether the abstract primarily describes empirical research (e.g., causal inference, field experiments, quasi-experimental methods, data analysis) or theoretical modeling (e.g., mechanism design, game theory, formal models).*
Q: Does the abstract primarily describe empirical research (as opposed to theoretical modeling)?
d1=+28pp  d2=+25pp  id=c_3e491db437dde4e3

### Use of Large-Scale Administrative or Survey Data  (+26 pp — more common among Quarterly Journal of Economics, p=0.000)
*The abstract describes the use of large-scale administrative records, government data, or population-level survey datasets.*
Q: Does the abstract describe the use of large-scale administrative records, government data, or population-level survey datasets?
d1=+36pp  d2=+16pp  id=c_a0eaff84ae5b4cdf

### Geographic or Contextual Specificity  (+24 pp — more common among Quarterly Journal of Economics, p=0.000)
*Whether the abstract specifies a particular geographic, demographic, or institutional context (e.g., country, city, population group).*
Q: Does the abstract specify a particular geographic, demographic, or institutional context?
d1=+27pp  d2=+21pp  id=c_746ae787803fd9a3

### Focus on Social Inequality and Disparities  (+24 pp — more common among Quarterly Journal of Economics, p=0.000)
*Whether the abstract addresses issues of social inequality, discrimination, or disparities between demographic groups (e.g., race, gender, class, income), or outcomes for disadvantaged or vulnerable populations.*
Q: Does the abstract address issues of social inequality, discrimination, or disparities between demographic groups, or outcomes for disadvantaged or vulnerable populations?
d1=+25pp  d2=+23pp  id=c_1dfaf3c6d4798008

### Labor Market and Employment Focus  (+23 pp — more common among Quarterly Journal of Economics, p=0.000)
*Whether the abstract focuses on labor markets, employment, wage inequality, or related labor outcomes.*
Q: Does the abstract focus on labor markets, employment, wage inequality, or related labor outcomes?
d1=+19pp  d2=+27pp  id=c_8fd7852bfd1d9cb0

### Explicit Quantitative Reporting  (+21 pp — more common among Quarterly Journal of Economics, p=0.000)
*Whether the abstract reports quantitative effect sizes or numerical estimates.*
Q: Does the abstract report quantitative effect sizes or numerical estimates?
d1=+13pp  d2=+29pp  id=c_144327a0fbb5779f

### Emphasis on Social Justice, Equity, or Community Impacts  (+21 pp — more common among Quarterly Journal of Economics, p=0.000)
*The abstract discusses social justice, equity, or community-level impacts as a central theme.*
Q: Does the abstract discuss social justice, equity, or community-level impacts as a central theme?
d1=+25pp  d2=+17pp  id=c_9c3188e9256cbea6

### Use of Structural Estimation or Formal Modeling  (-21 pp — more common among Journal of Political Economy, p=0.000)
*Whether the abstract describes the use of structural estimation, formal theoretical modeling, or mathematical frameworks.*
Q: Does the abstract describe the use of structural estimation, formal theoretical modeling, or mathematical frameworks?
d1=-31pp  d2=-11pp  id=c_1f6ca71158b0b2d1

### Interdisciplinary Content  (+19 pp — more common among Quarterly Journal of Economics, p=0.000)
*Whether the abstract incorporates concepts or methods from disciplines outside economics (e.g., psychology, sociology, linguistics, genetics) or discusses behavioral economics insights.*
Q: Does the abstract incorporate concepts or methods from disciplines outside economics, or discuss behavioral economics insights?
d1=+23pp  d2=+16pp  id=c_772cac97e5bf10e7

### Integration of Multidisciplinary Concepts  (+25 pp — more common among Quarterly Journal of Economics, p=0.001)
*Whether the abstract integrates concepts from multiple disciplines (e.g., genetics, psychology, sociology, political science) within an economic framework.*
Q: Does the abstract integrate concepts from multiple disciplines within an economic framework?
d1=+23pp  d2=+28pp  id=c_76cc7ebb1c88dd32

### Efficiency, Optimization, and Equilibrium Focus  (-21 pp — more common among Journal of Political Economy, p=0.001)
*Whether the abstract focuses on efficiency, optimization, or equilibrium properties of markets or mechanisms.*
Q: Does the abstract focus on efficiency, optimization, or equilibrium properties of markets or mechanisms?
d1=-25pp  d2=-16pp  id=c_4732505f85d44dd4

### Emphasis on Real-World, Contemporary, or Applied Contexts  (+15 pp — more common among Quarterly Journal of Economics, p=0.003)
*The abstract focuses on current or recent real-world economic problems, social challenges, or applied contexts, as opposed to abstract, historical, or theoretical settings.*
Q: Does the abstract focus on current or recent real-world economic problems, social challenges, or applied contexts, as opposed to abstract, historical, or theoretical settings?
d1=+13pp  d2=+16pp  id=c_120be8c96b2f5b96

### Explicit Mention of Market Design or Mechanism Design  (-11 pp — more common among Journal of Political Economy, p=0.005)
*Whether the abstract explicitly mentions market design, mechanism design, or related strategic behavior.*
Q: Does the abstract explicitly mention market design, mechanism design, or related strategic behavior?
d1=-9pp  d2=-12pp  id=c_7ce8be91f0af1cb7

### Distributional vs Efficiency Focus  (+16 pp — more common among Quarterly Journal of Economics, p=0.007)
*Whether the abstract focuses on distributional outcomes, equity, or who benefits (as opposed to aggregate efficiency or welfare).*
Q: Does the abstract focus on distributional outcomes, equity, or who benefits (rather than aggregate efficiency or welfare)?
d1=+15pp  d2=+17pp  id=c_586d8c5296b33638

### Demographic or Socioeconomic Factors  (+15 pp — more common among Quarterly Journal of Economics, p=0.008)
*Whether the abstract discusses demographic or socioeconomic factors (e.g., age, gender, race, education, income) as determinants of outcomes.*
Q: Does the abstract discuss demographic or socioeconomic factors as determinants of outcomes?
d1=+17pp  d2=+13pp  id=c_3ab606934c91768d

### Historical or Long-Term Perspective  (+13 pp — more common among Quarterly Journal of Economics, p=0.016)
*Whether the abstract analyzes historical events, long-term trends, or data spanning decades or centuries.*
Q: Does the abstract analyze historical events, long-term trends, or data spanning decades or centuries?
d1=+20pp  d2=+7pp  id=c_944e176487150775

### Evaluation of Heterogeneous Effects  (+13 pp — more common among Quarterly Journal of Economics, p=0.025)
*Whether the abstract examines heterogeneity in treatment effects across individuals, groups, or organizations.*
Q: Does the abstract examine heterogeneity in treatment effects across individuals, groups, or organizations?
d1=+25pp  d2=+1pp  id=c_ac45ca524ec543d0


## Suggestive features (exploratory — FDR 0.1, not 0.05)

Real-but-marginal effects that clear the looser threshold. Treat as leads to confirm, not findings — the primary table above is the headline. Optionally sanity-check this tier with a placebo run.

### Focus on Causal Mechanisms and Downstream Effects  (+9 pp — more common among Quarterly Journal of Economics, p=0.034)
*The abstract examines how changes in one dimension causally affect multiple downstream outcomes, or investigates causal chains beyond immediate effects.*
Q: Does the abstract examine how changes in one dimension causally affect multiple downstream outcomes, or investigate causal chains beyond immediate effects?
d1=+15pp  d2=+3pp  id=c_3e3b94a47db5c826

## Not validated (13)
- Generalizability and Abstraction  (d1=-8 d2=-12 pp, p=0.075, same_sign=True)
- Institutional or Organizational Context Emphasis  (d1=+11 d2=+4 pp, p=0.229, same_sign=True)
- Behavioral or Psychological Mechanisms  (d1=+7 d2=+3 pp, p=0.255, same_sign=True)
- Public Sector, Social Programs, or Policy Outcomes  (d1=+3 d2=+9 pp, p=0.263, same_sign=True)
- Emphasis on Practical Applications or Improvements  (d1=+7 d2=+1 pp, p=0.271, same_sign=True)
- Focus on Real-World Implementation or Practical Challenges  (d1=+3 d2=+1 pp, p=0.429, same_sign=True)
- Quantitative vs Qualitative Methods  (d1=+1 d2=+1 pp, p=0.490, same_sign=True)
- Study of Unintended Consequences or Adaptation  (d1=+17 d2=+0 pp, p=1.000, same_sign=False)
- Market Mechanisms and Firm Behavior Focus  (d1=-16 d2=+4 pp, p=1.000, same_sign=False)
- Policy Evaluation and Relevance  (d1=+11 d2=-3 pp, p=1.000, same_sign=False)
- Private Sector, Market, or Firm Outcomes  (d1=-15 d2=+8 pp, p=1.000, same_sign=False)
- Technical Language Complexity  (d1=+1 d2=-3 pp, p=1.000, same_sign=False)
- Macro vs Micro/Individual-Level Focus  (d1=-4 d2=+5 pp, p=1.000, same_sign=False)

---

# real_r0 — validated features grouped into themes

21 validated features -> 5 navigation themes (temperature-0 gpt-4.1). Themes are navigation labels only; grouping changes no statistic. Coverage: OK.

**Direction key:** + (focal_higher) = more prevalent among 'Quarterly Journal of Economics'; - (focal_lower) = more prevalent among 'Journal of Political Economy'.

## Data Sources and Collection  (4 feats, all +, mean +30pp)
*Features describing the types, novelty, and explicit mention of data sources and data collection methods.*
- Integration of Multiple Data Sources or Methods  (+35pp — more common among Quarterly Journal of Economics, p=0.000)
- Novel Data Collection  (+33pp — more common among Quarterly Journal of Economics, p=0.000)
- Explicit Mention of Data Sources  (+27pp — more common among Quarterly Journal of Economics, p=0.000)
- Use of Large-Scale Administrative or Survey Data  (+26pp — more common among Quarterly Journal of Economics, p=0.000)

## Empirical and Methodological Approaches  (7 feats, MIXED, mean +6pp)
*Features describing the empirical or theoretical orientation and specific methodological approaches used in research.*
- Use of Quasi-Experimental or Experimental Methods  (+30pp — more common among Quarterly Journal of Economics, p=0.000)
- Empirical vs Theoretical Orientation  (+27pp — more common among Quarterly Journal of Economics, p=0.000)
- Explicit Quantitative Reporting  (+21pp — more common among Quarterly Journal of Economics, p=0.000)
- Use of Structural Estimation or Formal Modeling  (-21pp — more common among Journal of Political Economy, p=0.000)
- Efficiency, Optimization, and Equilibrium Focus  (-21pp — more common among Journal of Political Economy, p=0.001)
- Explicit Mention of Market Design or Mechanism Design  (-11pp — more common among Journal of Political Economy, p=0.005)
- Evaluation of Heterogeneous Effects  (+13pp — more common among Quarterly Journal of Economics, p=0.025)

## Interdisciplinary and Multidisciplinary Content  (2 feats, all +, mean +22pp)
*Features describing the integration or incorporation of concepts and methods from multiple disciplines.*
- Interdisciplinary Content  (+19pp — more common among Quarterly Journal of Economics, p=0.000)
- Integration of Multidisciplinary Concepts  (+25pp — more common among Quarterly Journal of Economics, p=0.001)

## Context and Scope  (3 feats, all +, mean +17pp)
*Features describing the geographic, demographic, institutional, historical, or applied context of the research.*
- Geographic or Contextual Specificity  (+24pp — more common among Quarterly Journal of Economics, p=0.000)
- Emphasis on Real-World, Contemporary, or Applied Contexts  (+15pp — more common among Quarterly Journal of Economics, p=0.003)
- Historical or Long-Term Perspective  (+13pp — more common among Quarterly Journal of Economics, p=0.016)

## Social and Distributional Focus  (5 feats, all +, mean +20pp)
*Features describing research focused on social inequality, justice, demographic factors, distributional outcomes, and labor market issues.*
- Focus on Social Inequality and Disparities  (+24pp — more common among Quarterly Journal of Economics, p=0.000)
- Labor Market and Employment Focus  (+23pp — more common among Quarterly Journal of Economics, p=0.000)
- Emphasis on Social Justice, Equity, or Community Impacts  (+21pp — more common among Quarterly Journal of Economics, p=0.000)
- Distributional vs Efficiency Focus  (+16pp — more common among Quarterly Journal of Economics, p=0.007)
- Demographic or Socioeconomic Factors  (+15pp — more common among Quarterly Journal of Economics, p=0.008)
