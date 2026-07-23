# Sample output — Organization Science vs. Strategic Management Journal

A real `discern` run distinguishing the abstracts of two management journals,
**Organization Science** (OrgSci) and the **Strategic Management Journal** (SMJ).
Abstracts were pulled from [OpenAlex](https://openalex.org) (open scholarly
metadata); the raw abstract text is **not** included here — this page shows only
`discern`'s output.

- **Input:** ~650 published abstracts (326 SMJ, ~320 OrgSci), one text column, one binary group label.
- **Discovery:** 326 blinded hypotheses → 49 candidates.
- **Measurement:** every candidate scored on a held-out sample of 300 abstracts (150/group), 2000-permutation null.
- **Result:** **26 features validated** at FDR 0.05 (+ 3 suggestive at FDR 0.1), grouped into 6 navigation themes.

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
- discovery: 326 hypotheses -> 49 candidates -> **26 validated** (FDR 0.05) + **3 suggestive** (exploratory FDR 0.1)

**Direction key:** + (focal_higher) = more prevalent among 'Organization Science'; - (focal_lower) = more prevalent among 'Strategic Management Journal'.
d1/d2 = the two independent data-half effects (validation requires the same sign in both). A positive pp value = the feature is more prevalent among 'Organization Science'; negative = more prevalent among 'Strategic Management Journal'.

## Validated features (FDR 0.05)

### Outcome Level: Employee vs. Firm  (+39 pp — more common among Organization Science, p=0.000)
*Whether the abstract examines employee-related outcomes (e.g., performance, learning, energy) versus firm-level outcomes (e.g., performance, innovation, survival).*
Q: Does the abstract examine employee-related outcomes rather than firm-level outcomes?
d1=+48pp  d2=+29pp  id=c_1ab271eeccc43e07

### Emphasis on Emotional, Psychological, and Interpersonal Dynamics  (+34 pp — more common among Organization Science, p=0.000)
*Whether the abstract emphasizes emotional, psychological, or interpersonal dynamics within organizations, as opposed to structural, strategic, or economic aspects.*
Q: Does the abstract emphasize emotional, psychological, or interpersonal dynamics within organizations?
d1=+44pp  d2=+24pp  id=c_aba1f933eb4b20d6

### Methodological Approach: Qualitative/Experimental/Mixed vs. Quantitative/Archival  (+32 pp — more common among Organization Science, p=0.000)
*Whether the abstract employs qualitative, experimental, or mixed methods (e.g., interviews, ethnography, fieldwork, experiments) versus quantitative, archival, or formal modeling approaches.*
Q: Does the abstract indicate the use of qualitative, experimental, or mixed methods (e.g., interviews, ethnography, fieldwork, experiments) rather than quantitative, archival, or formal modeling approaches?
d1=+31pp  d2=+33pp  id=c_a9bf763073879137

### Disciplinary Grounding: Social Science vs. Strategy/Economics  (+31 pp — more common among Organization Science, p=0.000)
*Whether the abstract engages with literatures on social psychology, organizational behavior, and identity theory, versus strategic management, resource-based view, and competitive strategy.*
Q: Does the abstract engage with literatures on social psychology, organizational behavior, or identity theory?
d1=+35pp  d2=+28pp  id=c_9600858375c87807

### Subjective/Interpretive vs. Structural/Objective Determinants  (+31 pp — more common among Organization Science, p=0.000)
*Whether the abstract examines how perceptions, cognition, and subjective interpretations shape organizational outcomes, versus how objective structural conditions or incentives shape firm behavior.*
Q: Does the abstract examine how perceptions, cognition, or subjective interpretations shape organizational outcomes?
d1=+32pp  d2=+29pp  id=c_096d96cefb5c769c

### Level of Analysis: Micro/Individual vs. Macro/Organizational  (+29 pp — more common among Organization Science, p=0.000)
*Whether the abstract focuses on micro-level phenomena (individuals, teams, internal organizational processes) versus macro-level phenomena (firms, industries, markets, external environments).*
Q: Does the abstract primarily focus on micro-level or individual-level phenomena such as individuals, teams, or internal organizational processes rather than macro-level or organizational/firm-level phenomena?
d1=+36pp  d2=+23pp  id=c_5d98d1431a972544

### Focus on Micro-level Team and Collaboration Dynamics  (+29 pp — more common among Organization Science, p=0.000)
*Whether the abstract studies micro-level team processes, collaboration, or interpersonal relationships within organizations.*
Q: Does the abstract study micro-level team processes, collaboration, or interpersonal relationships within organizations?
d1=+37pp  d2=+21pp  id=c_1662eb62d865c193

### Focus on Social/Psychological Mechanisms vs. Structural/Economic Mechanisms  (+29 pp — more common among Organization Science, p=0.000)
*Whether the abstract explains outcomes primarily through social or psychological mechanisms (e.g., perception, cognition, emotion) rather than structural, economic, or material mechanisms.*
Q: Does the abstract explain outcomes primarily through social or psychological mechanisms rather than structural or economic mechanisms?
d1=+32pp  d2=+25pp  id=c_6e80100f379f3ba5

### Domain Focus: Labor/Employment/Entrepreneurship vs. Innovation/IP/Product Markets  (+29 pp — more common among Organization Science, p=0.000)
*Whether the abstract studies phenomena related to labor, employment, entrepreneurship, or talent, versus innovation, technology, intellectual property, or product markets.*
Q: Does the abstract study phenomena related to labor, employment, entrepreneurship, or talent?
d1=+32pp  d2=+25pp  id=c_096366d8bde0c50b

### Organizational Practices vs. Strategic Positioning  (+27 pp — more common among Organization Science, p=0.000)
*Whether the abstract focuses on organizational practices and their effects (e.g., incentives, monitoring, contract framing) versus firm strategies and positioning (e.g., optimal distinctiveness, framing, label appropriation).*
Q: Does the abstract focus on organizational practices and their effects rather than firm strategies and positioning?
d1=+29pp  d2=+24pp  id=c_46db4d1787403753

### Focus on Internal Organizational Processes vs. External/Market/Regulatory Contexts  (+23 pp — more common among Organization Science, p=0.000)
*Whether the abstract focuses on internal organizational processes, behaviors, and dynamics versus external market, regulatory, or institutional environments.*
Q: Does the abstract focus primarily on internal organizational processes or dynamics rather than external market, regulatory, or institutional contexts?
d1=+24pp  d2=+23pp  id=c_9ed5c7aaca2fc370

### Interdisciplinary vs. Discipline-Specific Frameworks  (+21 pp — more common among Organization Science, p=0.000)
*Whether the abstract utilizes interdisciplinary frameworks (drawing from multiple fields) versus frameworks primarily from business and management disciplines.*
Q: Does the abstract utilize interdisciplinary frameworks drawing from multiple fields?
d1=+25pp  d2=+17pp  id=c_2f75180b106a1962

### Emphasis on Social Influence, Communication, and Signaling  (+21 pp — more common among Organization Science, p=0.000)
*Whether the abstract studies social influence, communication processes, or signaling within or between organizations.*
Q: Does the abstract study social influence, communication processes, or signaling within or between organizations?
d1=+24pp  d2=+17pp  id=c_9235f5d625902389

### Emphasis on Agency, Identity, and Authenticity  (+21 pp — more common among Organization Science, p=0.000)
*Whether the abstract emphasizes individual agency, identity expression, or authenticity in organizational contexts.*
Q: Does the abstract emphasize individual agency, identity expression, or authenticity?
d1=+25pp  d2=+16pp  id=c_e197818626629393

### Normative/Ethical vs. Efficiency/Performance Focus  (+19 pp — more common among Organization Science, p=0.000)
*Whether the abstract emphasizes normative, ethical, fairness, or justice concerns (e.g., inclusion, equity, social responsibility) as opposed to efficiency, performance, or value creation.*
Q: Does the abstract emphasize normative, ethical, fairness, or justice concerns over efficiency or performance?
d1=+24pp  d2=+15pp  id=c_2b33ca8825a4fe6e

### Stakeholder Beneficiary Focus: Internal/Social vs. Market/Financial  (+17 pp — more common among Organization Science, p=0.000)
*Whether the abstract addresses how organizations can improve outcomes for internal stakeholders (e.g., fairness, inclusion, social outcomes) versus how firms can gain competitive advantage or improve financial performance.*
Q: Does the abstract address how organizations can improve outcomes for internal stakeholders such as fairness, inclusion, or social outcomes?
d1=+20pp  d2=+15pp  id=c_f7b41546ea2efff0

### Attention to Bias, Stereotypes, and Differential Group Effects  (+14 pp — more common among Organization Science, p=0.002)
*Whether the abstract examines bias, stereotypes, or differential effects of organizational practices on different demographic or social groups.*
Q: Does the abstract examine bias, stereotypes, or differential effects of organizational practices on different demographic or social groups?
d1=+19pp  d2=+9pp  id=c_6428b770e94ff3d9

### Study Scope and Scale: Single-site/In-depth vs. Large-scale/Multi-firm  (+15 pp — more common among Organization Science, p=0.004)
*Whether the abstract uses single-site, in-depth case studies or field studies of specific organizations or communities, versus large-scale datasets spanning multiple firms or industries.*
Q: Does the abstract use single-site, in-depth case studies or field studies of specific organizations or communities?
d1=+15pp  d2=+16pp  id=c_296737d9249661a2

### Emphasis on Innovation, Entrepreneurship, and Emergent Contexts  (-17 pp — more common among Strategic Management Journal, p=0.006)
*Whether the abstract focuses on innovation, entrepreneurship, startups, or emergent organizational forms and contexts.*
Q: Does the abstract focus on innovation, entrepreneurship, startups, or emergent organizational forms and contexts?
d1=-17pp  d2=-16pp  id=c_2074b5cb5a1c65fa

### Emphasis on Unintended Consequences and Spillover Effects  (+16 pp — more common among Organization Science, p=0.006)
*Whether the abstract examines unintended consequences or spillover effects of individual traits, beliefs, or behaviors on others.*
Q: Does the abstract examine unintended consequences or spillover effects of individual traits, beliefs, or behaviors on others?
d1=+19pp  d2=+13pp  id=c_6a3d634c296d413c

### Development/Identity Formation vs. Competitive Response  (+11 pp — more common among Organization Science, p=0.007)
*Whether the abstract examines how organizational practices enable individuals to develop new identities or capabilities, versus how firms respond to threats or opportunities in their competitive environment.*
Q: Does the abstract examine how organizational practices enable individuals to develop new identities or capabilities?
d1=+16pp  d2=+5pp  id=c_8cab35df83478374

### Societal/Ethical Relevance  (+15 pp — more common among Organization Science, p=0.011)
*Whether the abstract addresses societal or ethical issues such as social justice, diversity, inclusion, or social impact.*
Q: Does the abstract address societal or ethical issues such as social justice, diversity, inclusion, or social impact?
d1=+16pp  d2=+13pp  id=c_bf00ae6744fb89cb

### Innovation and Technology vs. Institutional and Social Dynamics  (+15 pp — more common among Organization Science, p=0.012)
*Whether the abstract emphasizes institutional contingencies, community inclusion, and boundary work in organizations, versus innovation processes, technology uniqueness, and acquisition strategies tied to technological assets.*
Q: Does the abstract emphasize institutional contingencies, community inclusion, or boundary work in organizations rather than innovation processes or technology uniqueness?
d1=+27pp  d2=+4pp  id=c_a29b4436d0f3cd32

### Focus on Marginalized/Underrepresented vs. Established Actors  (+11 pp — more common among Organization Science, p=0.015)
*Whether the abstract addresses challenges faced by marginalized, disadvantaged, or underrepresented populations, versus established firms or industries.*
Q: Does the abstract address challenges faced by marginalized, disadvantaged, or underrepresented populations?
d1=+15pp  d2=+8pp  id=c_8fb5d070cf679b56

### Exogenous vs. Endogenous Focus  (-11 pp — more common among Strategic Management Journal, p=0.020)
*Whether the abstract studies the effects of external shocks or regulatory changes versus endogenous processes like framing or category work.*
Q: Does the abstract study the effects of external shocks or regulatory changes rather than endogenous processes?
d1=-13pp  d2=-9pp  id=c_772fa9f9ccdd2346

### Theoretical vs. Practical/Empirical Emphasis  (+13 pp — more common among Organization Science, p=0.026)
*Whether the abstract emphasizes theoretical development, frameworks, or implications versus empirical findings, practical applications, or managerial implications.*
Q: Does the abstract emphasize theoretical development, frameworks, or implications over empirical findings or practical applications?
d1=+16pp  d2=+11pp  id=c_b826e9db4b5e340b


## Suggestive features (exploratory — FDR 0.1, not 0.05)

Real-but-marginal effects that clear the looser threshold. Treat as leads to confirm, not findings — the primary table above is the headline. Calibrate the exploratory tier with a placebo run.

### Emphasis on Role Conflict and Dual Roles  (+11 pp — more common among Organization Science, p=0.032)
*Whether the abstract studies situations involving role conflict or dual roles that create strategic pressures.*
Q: Does the abstract study situations involving role conflict or dual roles that create strategic pressures?
d1=+3pp  d2=+19pp  id=c_b4e260969b33fc90

### Political Dimensions in Entrepreneurship and Firms  (-6 pp — more common among Strategic Management Journal, p=0.054)
*Whether the abstract examines political activity as market actions and the effects of political opportunity structures on entrepreneurship, versus the role of political homophily and activism in entrepreneurial teams and firm strategies.*
Q: Does the abstract examine political activity as market actions or the effects of political opportunity structures on entrepreneurship rather than the role of political homophily and activism in entrepreneurial teams?
d1=-4pp  d2=-8pp  id=c_1097ee2ec0857ad7

### Firm Maturity and Industry Focus: Established Firms vs. Startups/Ecosystems  (-11 pp — more common among Strategic Management Journal, p=0.056)
*Whether the abstract investigates established firms, corporate governance, and regulatory outcomes, versus new ventures, startup ecosystems, and platform competition.*
Q: Does the abstract investigate established firms, corporate governance, or regulatory outcomes rather than new ventures, startup ecosystems, or platform competition?
d1=-17pp  d2=-5pp  id=c_24d74974d5b183d9

## Not validated (20)
- Focus on Social Identity, Diversity, and Inequality  (d1=+11 d2=+7 pp, p=0.076, same_sign=True)
- Context-Specificity vs. Universality  (d1=-7 d2=-13 pp, p=0.092, same_sign=True)
- Analytical Approach: Theoretical/Narrative vs. Empirical/Quantitative  (d1=+11 d2=+4 pp, p=0.092, same_sign=True)
- Theoretical vs. Applied Orientation  (d1=-13 d2=-7 pp, p=0.098, same_sign=True)
- Causal Identification vs. Theory Building  (d1=-13 d2=-3 pp, p=0.137, same_sign=True)
- Technology vs. Categories  (d1=+11 d2=+1 pp, p=0.152, same_sign=True)
- Prescriptive/Normative vs. Descriptive/Positive Framing  (d1=+4 d2=+9 pp, p=0.197, same_sign=True)
- Constraint vs. Discretion  (d1=-9 d2=-5 pp, p=0.200, same_sign=True)
- Theme of Conflict: Chaos/Paradox vs. Strategic Response  (d1=+4 d2=+4 pp, p=0.237, same_sign=True)
- Temporal Orientation: Longitudinal/Historical vs. Contemporary/Static  (d1=-11 d2=-3 pp, p=0.246, same_sign=True)
- Managerial Agency and Control  (d1=-5 d2=-1 pp, p=0.392, same_sign=True)
- Integration/Mutual Benefit vs. Competition/Zero-Sum Framing  (d1=+20 d2=-3 pp, p=1.000, same_sign=False)
- Focus on Social/Political Signaling vs. Governance Mechanisms  (d1=-16 d2=+4 pp, p=1.000, same_sign=False)
- Emphasis on Managerial Discretion and Subjectivity  (d1=-1 d2=+9 pp, p=1.000, same_sign=False)
- Valence of Phenomenon/Findings  (d1=-1 d2=+5 pp, p=1.000, same_sign=False)
- Emphasis on Heterogeneity, Contingency, and Moderation  (d1=-7 d2=+4 pp, p=1.000, same_sign=False)
- Emphasis on Learning, Knowledge, and Adaptation  (d1=+0 d2=+3 pp, p=1.000, same_sign=False)
- Complexity of Relationships/Theoretical Argument  (d1=+0 d2=+3 pp, p=1.000, same_sign=False)
- Attention to Temporal Dynamics and Processual Change  (d1=-1 d2=+4 pp, p=1.000, same_sign=False)
- Emphasis on System Critique and Failure to Achieve Intended Outcomes  (d1=+0 d2=+1 pp, p=1.000, same_sign=False)

---

# real_r0 — validated features grouped into themes

26 validated features -> 6 navigation themes (temperature-0 gpt-4.1). Themes are navigation labels only; grouping changes no statistic. Coverage: OK.

**Direction key:** + (focal_higher) = more prevalent among 'Organization Science'; - (focal_lower) = more prevalent among 'Strategic Management Journal'.

## Level and Scope of Analysis  (5 feats, MIXED, mean +19pp)
*Features describing the level (individual, team, firm, industry) and scope (internal vs. external, single-site vs. multi-firm) of analysis in abstracts.*
- Outcome Level: Employee vs. Firm  (+39pp — more common among Organization Science, p=0.000)
- Level of Analysis: Micro/Individual vs. Macro/Organizational  (+29pp — more common among Organization Science, p=0.000)
- Focus on Internal Organizational Processes vs. External/Market/Regulatory Contexts  (+23pp — more common among Organization Science, p=0.000)
- Study Scope and Scale: Single-site/In-depth vs. Large-scale/Multi-firm  (+15pp — more common among Organization Science, p=0.004)
- Exogenous vs. Endogenous Focus  (-11pp — more common among Strategic Management Journal, p=0.020)

## Subject Matter Focus  (4 feats, MIXED, mean +10pp)
*Features describing the substantive focus or domain of the research (e.g., labor, innovation, marginalized groups).*
- Domain Focus: Labor/Employment/Entrepreneurship vs. Innovation/IP/Product Markets  (+29pp — more common among Organization Science, p=0.000)
- Emphasis on Innovation, Entrepreneurship, and Emergent Contexts  (-17pp — more common among Strategic Management Journal, p=0.006)
- Innovation and Technology vs. Institutional and Social Dynamics  (+15pp — more common among Organization Science, p=0.012)
- Focus on Marginalized/Underrepresented vs. Established Actors  (+11pp — more common among Organization Science, p=0.015)

## Methodological and Theoretical Approach  (4 feats, all +, mean +24pp)
*Features describing the methodological, disciplinary, or theoretical orientation of the research.*
- Methodological Approach: Qualitative/Experimental/Mixed vs. Quantitative/Archival  (+32pp — more common among Organization Science, p=0.000)
- Disciplinary Grounding: Social Science vs. Strategy/Economics  (+31pp — more common among Organization Science, p=0.000)
- Interdisciplinary vs. Discipline-Specific Frameworks  (+21pp — more common among Organization Science, p=0.000)
- Theoretical vs. Practical/Empirical Emphasis  (+13pp — more common among Organization Science, p=0.026)

## Mechanisms and Determinants  (7 feats, all +, mean +23pp)
*Features describing the types of mechanisms or determinants (social, psychological, structural, economic) emphasized in the research.*
- Emphasis on Emotional, Psychological, and Interpersonal Dynamics  (+34pp — more common among Organization Science, p=0.000)
- Subjective/Interpretive vs. Structural/Objective Determinants  (+31pp — more common among Organization Science, p=0.000)
- Focus on Social/Psychological Mechanisms vs. Structural/Economic Mechanisms  (+29pp — more common among Organization Science, p=0.000)
- Emphasis on Social Influence, Communication, and Signaling  (+21pp — more common among Organization Science, p=0.000)
- Emphasis on Agency, Identity, and Authenticity  (+21pp — more common among Organization Science, p=0.000)
- Emphasis on Unintended Consequences and Spillover Effects  (+16pp — more common among Organization Science, p=0.006)
- Development/Identity Formation vs. Competitive Response  (+11pp — more common among Organization Science, p=0.007)

## Organizational Practices and Processes  (2 feats, all +, mean +28pp)
*Features describing the focus on organizational practices, internal processes, and team or collaboration dynamics.*
- Focus on Micro-level Team and Collaboration Dynamics  (+29pp — more common among Organization Science, p=0.000)
- Organizational Practices vs. Strategic Positioning  (+27pp — more common among Organization Science, p=0.000)

## Normative and Ethical Focus  (4 feats, all +, mean +16pp)
*Features describing the emphasis on normative, ethical, fairness, justice, or societal concerns in the research.*
- Normative/Ethical vs. Efficiency/Performance Focus  (+19pp — more common among Organization Science, p=0.000)
- Stakeholder Beneficiary Focus: Internal/Social vs. Market/Financial  (+17pp — more common among Organization Science, p=0.000)
- Attention to Bias, Stereotypes, and Differential Group Effects  (+14pp — more common among Organization Science, p=0.002)
- Societal/Ethical Relevance  (+15pp — more common among Organization Science, p=0.011)
