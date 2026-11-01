# Sample output — CampaignView candidate biographies

A completed `discern` run comparing campaign-website biographies of Republican and Democratic
candidates for the U.S. House in 2018, 2020, and 2022.

- Input: 5,105 candidate-year biographies (2,600 Republican; 2,505 Democratic).
- Discovery: 204 proposed hypotheses consolidated into 65 candidate features.
- Measurement: 600 held-out biographies, 300 per party, split into two halves with 150 per party.
- Selection: 1,300 permutations; 47 validated features at 5% FDR and two additional suggestive
  features at 10% FDR. No features fall in the uncorrected-only tier.
- Placebo: the matching run with shuffled labels validated zero of 77 candidates at either FDR
  threshold. See the [complete placebo output](../campaignview/saved/placebo_r0/05_summary.md).

Positive differences mean greater prevalence among Republican biographies; negative differences
mean greater prevalence among Democratic biographies. Effects are percentage-point differences.
Party references remain in the texts, so many large differences recover explicit partisan identity.
The results describe biography texts and do not establish causal effects or classification accuracy.

The report below is the actual saved [real-run output](../campaignview/saved/real_r1/05_summary.md),
reproduced unchanged. It includes the validated and suggestive features and lists the remaining
candidates. Its display rounds effects and p-values; the [complete feature table](../campaignview/features.real.csv)
contains all 65 definitions and questions with full-precision statistics. Optional theme grouping
was disabled for this run.

The [walkthrough](../campaignview/README.md) provides the openly licensed data, full configurations,
all saved stages, and an offline verification command. No API keys are needed to read or verify
these saved results.

---

# discern run: real_r1  (real)

- prompt_version: discern-1
- measurement: rotate, n=600 (300/group), permutations=1300, FDR=0.05
- discovery: 204 hypotheses -> 65 candidates -> **47 validated** (FDR 0.05) + **2 suggestive** (exploratory FDR 0.1) + **0 uncorrected directional** (p<0.05)

**Direction key:** + (focal_higher) = more prevalent among 'Republican House primary candidates'; - (focal_lower) = more prevalent among 'Democratic House primary candidates'.
d1/d2 = the two independent data-half effects (validation requires the same sign in both). A positive pp value = the feature is more prevalent among 'Republican House primary candidates'; negative = more prevalent among 'Democratic House primary candidates'.

## Validated features (FDR 0.05)

### Emphasis on Progressive or Reformist Ideology and Values  (-77 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative explicitly references progressive, reformist, or social justice-oriented values, organizations, or causes.*
Q: Does the biography explicitly reference progressive, reformist, or social justice-oriented values, organizations, or causes?
d1=-77pp  d2=-78pp  id=c_95cc5980b5524e93

### Emphasis on Conservative Ideology and Values  (+69 pp — more common among Republican House primary candidates, p=0.001)
*The narrative explicitly references conservative political values, organizations, or policy positions (e.g., pro-life, pro-2nd Amendment, limited government).*
Q: Does the biography explicitly reference conservative political values, organizations, or policy positions (e.g., pro-life, pro-2nd Amendment, limited government)?
d1=+66pp  d2=+73pp  id=c_3bd81b5d88643982

### Emphasis on Social Justice, Diversity, and Community Advocacy  (-62 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes social justice, diversity, or advocacy for marginalized groups.*
Q: Does the biography emphasize social justice, diversity, or advocacy for marginalized groups?
d1=-63pp  d2=-61pp  id=c_75f04a5b10e787a4

### Explicit Conservative/Republican Political Identity  (+61 pp — more common among Republican House primary candidates, p=0.001)
*The narrative explicitly identifies the candidate as conservative, Republican, or aligned with Trump.*
Q: Does the biography explicitly identify the candidate as conservative, Republican, or aligned with Trump?
d1=+57pp  d2=+65pp  id=c_0bee4a5fcf1f4882

### Emphasis on Social Programs, Government Accountability, and Wealth Redistribution  (-59 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes social programs, government accountability, or wealth redistribution.*
Q: Does the biography emphasize social programs, government accountability, or wealth redistribution?
d1=-55pp  d2=-62pp  id=c_be06aa38949c4157

### Explicit Progressive/Democratic Political Identity  (-51 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative explicitly identifies the candidate as progressive, Democratic, or aligned with progressive policies.*
Q: Does the biography explicitly identify the candidate as progressive, Democratic, or aligned with progressive policies?
d1=-49pp  d2=-54pp  id=c_215afc972b2902ac

### Emphasis on Progressive Social Issues (e.g., Racial Justice, Immigration Reform, Environmental Concerns)  (-48 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes progressive social issues such as racial justice, immigration reform, or environmental concerns.*
Q: Does the biography emphasize progressive social issues such as racial justice, immigration reform, or environmental concerns?
d1=-45pp  d2=-51pp  id=c_3b72860a60ce5ba7

### Emphasis on Representation of Marginalized or Diverse Communities  (-46 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative highlights the candidate's identity as a member of, or advocate for, underrepresented, marginalized, or diverse communities.*
Q: Does the biography highlight the candidate's identity as a member of, or advocate for, underrepresented, marginalized, or diverse communities?
d1=-43pp  d2=-49pp  id=c_de354beb36cb550a

### Emphasis on Opposition to Socialism or Progressive Economic Policies  (+46 pp — more common among Republican House primary candidates, p=0.001)
*The narrative emphasizes opposition to socialism or progressive economic policies.*
Q: Does the biography emphasize opposition to socialism or progressive economic policies?
d1=+41pp  d2=+52pp  id=c_79d1e492a7de70aa

### Emphasis on Policy Domains: Social Issues vs. Economic/Conservative Issues  (-45 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes social issues (healthcare, education, environment, social justice) versus economic/conservative issues (taxes, deregulation, border security, constitutional rights).*
Q: Does the biography emphasize social issues (healthcare, education, environment, social justice) versus economic/conservative issues (taxes, deregulation, border security, constitutional rights)?
d1=-50pp  d2=-40pp  id=c_b0475f647dc27026

### Emphasis on Small Government, Deregulation, and Fiscal Conservatism  (+44 pp — more common among Republican House primary candidates, p=0.001)
*The narrative emphasizes limited government, deregulation, spending cuts, or fiscal conservatism.*
Q: Does the biography emphasize limited government, deregulation, spending cuts, or fiscal conservatism?
d1=+39pp  d2=+49pp  id=c_412c8829c1e1cf53

### Emphasis on Conservative Cultural Issues (e.g., Pro-life, Second Amendment, Opposition to Big Government)  (+44 pp — more common among Republican House primary candidates, p=0.001)
*The narrative emphasizes conservative cultural issues such as pro-life stance, Second Amendment rights, or opposition to big government.*
Q: Does the biography emphasize conservative cultural issues such as pro-life stance, Second Amendment rights, or opposition to big government?
d1=+38pp  d2=+49pp  id=c_ff84206170172803

### Emphasis on Collaborative Problem-Solving and Consensus-Building  (-40 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes collaborative problem-solving or consensus-building.*
Q: Does the biography emphasize collaborative problem-solving or consensus-building?
d1=-32pp  d2=-47pp  id=c_25ed92259f2f53bc

### Emphasis on Change/Reform vs. Restoration/Tradition  (-34 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative frames the candidate as an agent of change, reform, or systemic improvement versus as a defender of tradition or restoration of past values.*
Q: Does the biography frame the candidate as an agent of change, reform, or systemic improvement (B) versus as a defender of tradition or restoration of past values (A)?
d1=-34pp  d2=-34pp  id=c_b432f9347172563c

### Emphasis on Systemic Reform and Advocacy for Change  (-34 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative focuses on systemic reform, advocacy for change, or addressing systemic inequalities.*
Q: Does the biography focus on systemic reform, advocacy for change, or addressing systemic inequalities?
d1=-32pp  d2=-36pp  id=c_edc1685f9e794d85

### Emphasis on Traditional Family Values and Religious Faith  (+33 pp — more common among Republican House primary candidates, p=0.001)
*The narrative emphasizes traditional family structure, family values, or religious faith (especially Christian).*
Q: Does the biography emphasize traditional family structure, family values, or religious faith (especially Christian)?
d1=+29pp  d2=+38pp  id=c_d45bcf1d0f5fb48f

### Emphasis on Collective Action and Community Empowerment  (-30 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes collective action, community empowerment, or working together.*
Q: Does the biography emphasize collective action, community empowerment, or working together?
d1=-30pp  d2=-31pp  id=c_18f56da3e4b8cdfb

### Emphasis on Religious Faith or Motivation  (+29 pp — more common among Republican House primary candidates, p=0.001)
*The narrative references religious faith, church membership, or religious motivation for candidacy.*
Q: Does the biography reference religious faith, church membership, or religious motivation for candidacy?
d1=+29pp  d2=+29pp  id=c_e2a5bb40d2d09efd

### Emphasis on Religious Identity and Christian Faith  (+28 pp — more common among Republican House primary candidates, p=0.001)
*The narrative explicitly references religious identity or Christian faith as central to the candidate's values.*
Q: Does the biography explicitly reference religious identity or Christian faith as central to the candidate's values?
d1=+27pp  d2=+30pp  id=c_116d20b03beb6ef1

### Emphasis on Economic Regulation and Worker Protections  (-26 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes economic regulation or worker protections.*
Q: Does the biography emphasize economic regulation or worker protections?
d1=-25pp  d2=-28pp  id=c_cde45b98dc7a5435

### Emphasis on Qualitative Impact and Community Change  (-26 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes qualitative impact (e.g., lives changed, communities empowered, justice advanced).*
Q: Does the biography emphasize qualitative impact (e.g., lives changed, communities empowered, justice advanced)?
d1=-24pp  d2=-29pp  id=c_4a0d4e9f66df412e

### Emphasis on Business, Military, or Law Enforcement as Leadership Experience  (+26 pp — more common among Republican House primary candidates, p=0.001)
*The narrative highlights business, military, or law enforcement experience as evidence of leadership.*
Q: Does the biography highlight business, military, or law enforcement experience as evidence of leadership?
d1=+25pp  d2=+27pp  id=c_1582365fdd31c4d0

### Hopeful, Unifying, or Emotive Rhetorical Style  (-25 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative uses hopeful, unifying, or emotive language focused on inclusion, change, or community.*
Q: Does the biography use hopeful, unifying, or emotive language focused on inclusion, change, or community?
d1=-25pp  d2=-25pp  id=c_6885bb6f6bb21ac7

### Emphasis on Business/Entrepreneurial Background  (+23 pp — more common among Republican House primary candidates, p=0.001)
*The narrative highlights business ownership, entrepreneurship, or professional achievements in the private sector as key qualifications.*
Q: Does the biography highlight business ownership, entrepreneurship, or professional achievements in the private sector as key qualifications?
d1=+26pp  d2=+21pp  id=c_267c0a14f702730b

### Emphasis on Religious Reference Frequency  (+23 pp — more common among Republican House primary candidates, p=0.001)
*The narrative frequently references religious beliefs, faith, or church involvement.*
Q: Does the biography frequently reference religious beliefs, faith, or church involvement?
d1=+21pp  d2=+25pp  id=c_fda7c7e4113632e6

### Emphasis on Worker Rights, Labor Protections, and Unions  (-23 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes worker rights, labor protections, or union involvement.*
Q: Does the biography emphasize worker rights, labor protections, or union involvement?
d1=-21pp  d2=-25pp  id=c_8d7f01acf79ccac8

### Emphasis on Professional Background in Law, Education, Healthcare, or Community Advocacy  (-23 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative highlights professional experience in law, education, healthcare, or community advocacy as a qualification.*
Q: Does the biography highlight professional experience in law, education, healthcare, or community advocacy as a qualification?
d1=-27pp  d2=-18pp  id=c_2b68cddbf5d7b1f6

### Emphasis on Community Service and Grassroots Organizing  (-22 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative highlights community service, grassroots organizing, or activism as central to the candidate's identity.*
Q: Does the biography highlight community service, grassroots organizing, or activism as central to the candidate's identity?
d1=-20pp  d2=-24pp  id=c_bc7ebf8dccc05179

### Emphasis on Diverse Family Structures and Secular/Inclusive Spirituality  (-20 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative emphasizes diverse family structures or secular/inclusive spiritual frameworks rather than traditional religious identity.*
Q: Does the biography emphasize diverse family structures or secular/inclusive spiritual frameworks rather than traditional religious identity?
d1=-19pp  d2=-21pp  id=c_559c872d7897328b

### Emphasis on Personal Adversity, Minority, or Immigrant Background  (-19 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative highlights personal adversity, minority identity, or immigrant background as central to the candidate's story.*
Q: Does the biography highlight personal adversity, minority identity, or immigrant background as central to the candidate's story?
d1=-16pp  d2=-21pp  id=c_d12dac381127b9b9

### Emphasis on Self-Made Achievement vs. Institutional Support  (+19 pp — more common among Republican House primary candidates, p=0.001)
*The narrative frames the candidate's achievements as self-made through personal effort versus achieved through institutional support, mentorship, or programs.*
Q: Does the biography frame the candidate's achievements as self-made through personal effort (A) versus achieved through institutional support, mentorship, or programs (B)?
d1=+17pp  d2=+20pp  id=c_4a59b837a526d341

### Emphasis on Policy Opposition (Critique of Opponents or Liberal Policies)  (+17 pp — more common among Republican House primary candidates, p=0.001)
*The narrative includes direct criticism of political opponents, liberal policies, or the political establishment.*
Q: Does the biography include direct criticism of political opponents, liberal policies, or the political establishment?
d1=+21pp  d2=+14pp  id=c_0a44a206f180df49

### Emphasis on Non-Traditional or Practical Education Paths  (+17 pp — more common among Republican House primary candidates, p=0.001)
*The narrative emphasizes non-traditional education paths or practical business/military education.*
Q: Does the biography emphasize non-traditional education paths or practical business/military education?
d1=+24pp  d2=+10pp  id=c_c1db7a1e0fb4b498

### Emphasis on Combative vs. Collaborative Rhetoric  (+15 pp — more common among Republican House primary candidates, p=0.001)
*The narrative uses language emphasizing fighting, strength, and confrontation versus building, serving, and collaboration.*
Q: Does the biography use language emphasizing fighting, strength, and confrontation (A) versus building, serving, and collaboration (B)?
d1=+19pp  d2=+11pp  id=c_d68aa35bb39b8c70

### Emphasis on Military Service  (+14 pp — more common among Republican House primary candidates, p=0.001)
*The narrative highlights the candidate's military service or veteran status as a central qualification or identity.*
Q: Does the biography highlight the candidate's military service or veteran status as a central qualification or identity?
d1=+16pp  d2=+12pp  id=c_6383065b4677e9c6

### Emphasis on Insider Status or Established Political Career  (-14 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative presents the candidate as an experienced insider with a long political or public service career.*
Q: Does the biography present the candidate as an experienced insider with a long political or public service career?
d1=-13pp  d2=-15pp  id=c_b31897130f3a7692

### Emphasis on Longstanding Civic Engagement and Community Organizing  (-14 pp — more common among Democratic House primary candidates, p=0.001)
*The narrative presents a long history of civic engagement, community organizing, or public service.*
Q: Does the biography present a long history of civic engagement, community organizing, or public service?
d1=-11pp  d2=-17pp  id=c_cf55f57473ee6c5d

### Emphasis on Second Amendment Rights and Gun Ownership  (+13 pp — more common among Republican House primary candidates, p=0.001)
*The narrative emphasizes Second Amendment rights or gun ownership.*
Q: Does the biography emphasize Second Amendment rights or gun ownership?
d1=+10pp  d2=+16pp  id=c_f83055f2caaddd08

### Emphasis on Immigration Enforcement and Border Security  (+12 pp — more common among Republican House primary candidates, p=0.001)
*The narrative emphasizes immigration enforcement or border security as a policy priority.*
Q: Does the biography emphasize immigration enforcement or border security as a policy priority?
d1=+12pp  d2=+12pp  id=c_cbc9bebf4ada4fb7

### Emphasis on Abortion Policy Framing  (+9 pp — more common among Republican House primary candidates, p=0.001)
*The narrative describes abortion policy using language of protecting life/defending the unborn versus reproductive rights and choice.*
Q: Does the biography describe abortion policy using language of protecting life/defending the unborn (A) versus reproductive rights and choice (B)?
d1=+5pp  d2=+13pp  id=c_b40876b77f4d777c

### Emphasis on Policy Specificity and Legislative Accomplishments  (-12 pp — more common among Democratic House primary candidates, p=0.002)
*The narrative provides detailed policy proposals or references specific legislative accomplishments.*
Q: Does the biography provide detailed policy proposals or reference specific legislative accomplishments?
d1=-8pp  d2=-16pp  id=c_ebca7ca854cb14bf

### Emphasis on Trump Alignment  (+10 pp — more common among Republican House primary candidates, p=0.002)
*The narrative explicitly references President Trump, Trump-era policies, or uses Trump-aligned language.*
Q: Does the biography explicitly reference President Trump, Trump-era policies, or use Trump-aligned language?
d1=+10pp  d2=+10pp  id=c_cc98700584a302e1

### Emphasis on Overcoming Adversity or Economic Hardship  (-13 pp — more common among Democratic House primary candidates, p=0.002)
*The narrative includes stories of overcoming adversity, economic hardship, or personal struggle as a formative experience.*
Q: Does the biography include stories of overcoming adversity, economic hardship, or personal struggle as a formative experience?
d1=-7pp  d2=-19pp  id=c_dd779ec902b82826

### Emphasis on Recent Entry vs. Career Progression  (-10 pp — more common among Democratic House primary candidates, p=0.011)
*The narrative presents the candidacy as a recent decision or calling versus as the result of long-term career progression.*
Q: Does the biography present the candidacy as a recent decision or calling (A) versus as the result of long-term career progression (B)?
d1=-8pp  d2=-13pp  id=c_b4f71000790cf779

### Emphasis on Educational Achievement from Prestigious Institutions  (-10 pp — more common among Democratic House primary candidates, p=0.012)
*The narrative highlights educational achievement from prestigious institutions or advanced degrees.*
Q: Does the biography highlight educational achievement from prestigious institutions or advanced degrees?
d1=-15pp  d2=-5pp  id=c_22762f6641bcf40e

### Emphasis on Traditional Family Structure and Values  (+9 pp — more common among Republican House primary candidates, p=0.021)
*The narrative highlights traditional family structures (marriage, children, grandchildren) and/or explicitly references family values.*
Q: Does the biography highlight traditional family structures (marriage, children, grandchildren) and/or explicitly reference family values?
d1=+9pp  d2=+9pp  id=c_ccad4f5588714713

### Emphasis on Hands-On/Technical Work vs. Administrative/Policy Work  (+9 pp — more common among Republican House primary candidates, p=0.029)
*The narrative describes direct, hands-on, technical, or operational work versus administrative, analytical, or policy work.*
Q: Does the biography describe direct, hands-on, technical, or operational work (A) versus administrative, analytical, or policy work (B)?
d1=+12pp  d2=+7pp  id=c_c37d00f1b203e35b


## Suggestive features (exploratory — FDR 0.1, not 0.05)

Real-but-marginal effects that clear the looser threshold. Treat as leads to confirm, not findings — the primary table above is the headline. Optionally sanity-check this tier with a placebo run.

### Emphasis on Immigration Policy Framing  (+6 pp — more common among Republican House primary candidates, p=0.071)
*The narrative frames immigration policy around border security and legal processes versus humanitarian concerns and immigrant contributions.*
Q: Does the biography frame immigration policy around border security and legal processes (A) versus humanitarian concerns and immigrant contributions (B)?
d1=+8pp  d2=+3pp  id=c_e9bc39ae824f0c74

### Emphasis on Immigration Reform, Immigrant Rights, or Multiculturalism  (-6 pp — more common among Democratic House primary candidates, p=0.074)
*The narrative emphasizes immigration reform, immigrant rights, or multicultural experiences.*
Q: Does the biography emphasize immigration reform, immigrant rights, or multicultural experiences?
d1=-4pp  d2=-9pp  id=c_7a2fc0483a3710e1


## Uncorrected directional tendencies (exploratory — unadjusted p < 0.05)

These features have the same effect direction in both held-out halves and an unadjusted permutation p-value below 0.05, but do not pass either FDR tier. They are not multiplicity-controlled: some are expected by chance when many candidates are tested. Treat them as leads for future confirmation, not findings.

## Remaining candidates (not validated) (16)
- Emphasis on Outsider Status or Anti-Establishment Positioning  (d1=+7 d2=+7 pp, p=0.078, same_sign=True)
- Emphasis on Populist vs. Pluralist Representation  (d1=-3 d2=-8 pp, p=0.079, same_sign=True)
- Emphasis on Quantifiable Accomplishments  (d1=-3 d2=-10 pp, p=0.085, same_sign=True)
- Emphasis on Policy Position Specificity  (d1=+1 d2=+13 pp, p=0.098, same_sign=True)
- Emphasis on Law Enforcement Background  (d1=+6 d2=+1 pp, p=0.102, same_sign=True)
- Emphasis on Media Presence vs. Government Service  (d1=+3 d2=+7 pp, p=0.156, same_sign=True)
- Emphasis on Personal Courage and Willingness to Make Unpopular Decisions  (d1=+4 d2=+7 pp, p=0.172, same_sign=True)
- Emphasis on Educational Achievement  (d1=-5 d2=-3 pp, p=0.281, same_sign=True)
- Emphasis on Personal Narrative vs. Professional Qualifications  (d1=-7 d2=-1 pp, p=0.285, same_sign=True)
- Emphasis on Educational Institution Prestige  (d1=-5 d2=-3 pp, p=0.311, same_sign=True)
- Emphasis on Formal, Credential-Focused Narrative  (d1=-1 d2=+9 pp, p=1.000, same_sign=False)
- Emphasis on Insider Experience vs. Outsider/Reformer Positioning  (d1=+5 d2=-11 pp, p=1.000, same_sign=False)
- Emphasis on Personal Stories and Emotional Appeal  (d1=+3 d2=+0 pp, p=1.000, same_sign=False)
- Emphasis on Advocacy for Veterans and Military Families  (d1=+5 d2=-1 pp, p=1.000, same_sign=False)
- Emphasis on Recent Political Engagement Motivated by Current Events  (d1=-5 d2=+3 pp, p=1.000, same_sign=False)
- Emphasis on Individual Accomplishment and Leadership  (d1=-1 d2=+1 pp, p=1.000, same_sign=False)