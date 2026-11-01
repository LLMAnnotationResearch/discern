# discern run: placebo_r0  (placebo)

- prompt_version: discern-1
- measurement: rotate, n=600 (300/group), permutations=1060, FDR=0.05
- discovery: 180 hypotheses -> 53 candidates -> **0 validated** (FDR 0.05) + **0 suggestive** (exploratory FDR 0.1) + **4 uncorrected directional** (p<0.05)

**Direction key:** + (focal_higher) = more prevalent among 'Republican House primary candidates'; - (focal_lower) = more prevalent among 'Democratic House primary candidates'.
d1/d2 = the two independent data-half effects (validation requires the same sign in both). A positive pp value = the feature is more prevalent among 'Republican House primary candidates'; negative = more prevalent among 'Democratic House primary candidates'.

## Validated features (FDR 0.05)


## Suggestive features (exploratory — FDR 0.1, not 0.05)

Real-but-marginal effects that clear the looser threshold. Treat as leads to confirm, not findings — the primary table above is the headline. Optionally sanity-check this tier with a placebo run.


## Uncorrected directional tendencies (exploratory — unadjusted p < 0.05)

These features have the same effect direction in both held-out halves and an unadjusted permutation p-value below 0.05, but do not pass either FDR tier. They are not multiplicity-controlled: some are expected by chance when many candidates are tested. Treat them as leads for future confirmation, not findings.

### Elite Educational Credentials  (+10 pp — more common among Republican House primary candidates, p=0.008)
*The biography mentions graduate degrees from prestigious institutions.*
Q: Does the biography mention graduate degrees from prestigious institutions?
d1=+15pp  d2=+5pp  id=c_c06e8722134699ab

### Vulnerable Populations Focus  (-10 pp — more common among Democratic House primary candidates, p=0.019)
*The biography emphasizes working directly with vulnerable or underserved populations.*
Q: Does the biography emphasize working directly with vulnerable or underserved populations?
d1=-11pp  d2=-9pp  id=c_5ec5bb13ad20a8a9

### Diversity of Professional Backgrounds  (-9 pp — more common among Democratic House primary candidates, p=0.020)
*The biography describes diverse professional experiences across multiple sectors, rather than deep expertise in a single domain.*
Q: Does the biography describe diverse professional experiences across multiple sectors, rather than deep expertise in a single domain?
d1=-11pp  d2=-7pp  id=c_77d351197dd53fe4

### Grassroots vs. Establishment Path  (-8 pp — more common among Democratic House primary candidates, p=0.047)
*The biography describes the path to candidacy as emerging from grassroots community organizing or direct service work, rather than established professional or political networks.*
Q: Does the biography describe the path to candidacy as emerging from grassroots community organizing or direct service work, rather than established professional or political networks?
d1=-9pp  d2=-7pp  id=c_f16edd16d80cd030

## Remaining candidates (not validated) (49)
- Emphasis on Political Experience and Leadership Roles  (d1=-1 d2=-15 pp, p=0.053, same_sign=True)
- Emphasis on Anti-Corruption or Money-in-Politics Concerns  (d1=-8 d2=-4 pp, p=0.063, same_sign=True)
- Concrete Policy Solutions Tied to Personal Experience  (d1=-4 d2=-11 pp, p=0.065, same_sign=True)
- Emphasis on Personal Narrative, Emotional Appeal, or Storytelling  (d1=-8 d2=-5 pp, p=0.065, same_sign=True)
- Emphasis on Skepticism and Highlighting Systemic Issues  (d1=-8 d2=-5 pp, p=0.129, same_sign=True)
- Emphasis on Collaboration, Listening, and Common Ground  (d1=-8 d2=-4 pp, p=0.129, same_sign=True)
- Military Service Emphasis  (d1=-1 d2=-11 pp, p=0.139, same_sign=True)
- Anti-Government Regulation Rhetoric  (d1=-9 d2=-1 pp, p=0.140, same_sign=True)
- Emphasis on Diverse or Non-Traditional Backgrounds  (d1=-5 d2=-7 pp, p=0.141, same_sign=True)
- Emphasis on Personal Agency vs. Institutional Support  (d1=-9 d2=-3 pp, p=0.144, same_sign=True)
- Emphasis on Career Stability and Long-Term Professional Trajectories  (d1=+11 d2=+2 pp, p=0.149, same_sign=True)
- Founding vs. Managing Organizations  (d1=-7 d2=-4 pp, p=0.163, same_sign=True)
- Work Ethic and Personal Determination Emphasis  (d1=-5 d2=-2 pp, p=0.168, same_sign=True)
- Emphasis on Fighting Opponents or Defending Principles  (d1=-5 d2=-6 pp, p=0.173, same_sign=True)
- Emphasis on Personal Sacrifice, Caregiving, or Putting Others First  (d1=-7 d2=-3 pp, p=0.187, same_sign=True)
- Family/Personal Hardship Narrative  (d1=-7 d2=-3 pp, p=0.192, same_sign=True)
- Emphasis on Problem Diagnosis: Structural Reform vs. Efficient Management  (d1=-4 d2=-5 pp, p=0.192, same_sign=True)
- Quantified Business Metrics  (d1=+5 d2=+1 pp, p=0.218, same_sign=True)
- Union Involvement Emphasis  (d1=-3 d2=-2 pp, p=0.270, same_sign=True)
- Emphasis on Urban, Diverse, or Immigrant Community Background  (d1=-2 d2=-4 pp, p=0.385, same_sign=True)
- Nonprofit/Community Service/Activism Emphasis  (d1=-3 d2=-1 pp, p=0.385, same_sign=True)
- Progressive/Democratic Identity Explicitness  (d1=-1 d2=-3 pp, p=0.388, same_sign=True)
- Emphasis on Fiscal Conservatism, Business-Friendly Policies, or Support for Trump  (d1=+2 d2=+2 pp, p=0.424, same_sign=True)
- Emphasis on Formal Educational Credentials and Institutional Training  (d1=+1 d2=+1 pp, p=0.460, same_sign=True)
- Accessibility to Constituents  (d1=-2 d2=-2 pp, p=0.467, same_sign=True)
- Business/Entrepreneurial Background Emphasis  (d1=-2 d2=-2 pp, p=0.482, same_sign=True)
- Geographic Mobility  (d1=+13 d2=-1 pp, p=1.000, same_sign=False)
- Socioeconomic Background Emphasis  (d1=-14 d2=+4 pp, p=1.000, same_sign=False)
- Manual Labor/Trades Origin  (d1=-11 d2=+2 pp, p=1.000, same_sign=False)
- Outsider vs. Insider Positioning  (d1=-13 d2=+5 pp, p=1.000, same_sign=False)
- Immigrant/Refugee Experience Emphasis  (d1=+10 d2=-2 pp, p=1.000, same_sign=False)
- Pragmatism vs. Principle  (d1=+3 d2=-9 pp, p=1.000, same_sign=False)
- Religious Faith Prominence  (d1=+6 d2=-1 pp, p=1.000, same_sign=False)
- Policy vs. Character Emphasis  (d1=-5 d2=+0 pp, p=1.000, same_sign=False)
- Local Community Roots/Deep Ties  (d1=-7 d2=+1 pp, p=1.000, same_sign=False)
- National/Global Perspective  (d1=+7 d2=-2 pp, p=1.000, same_sign=False)
- Policy Expertise/Technical Credentials Emphasis  (d1=+0 d2=-4 pp, p=1.000, same_sign=False)
- Social Justice Advocacy  (d1=+0 d2=-4 pp, p=1.000, same_sign=False)
- Family-Centered Identity Emphasis  (d1=-5 d2=+1 pp, p=1.000, same_sign=False)
- Explicit Partisan or Ideological Identification  (d1=+5 d2=-2 pp, p=1.000, same_sign=False)
- Emphasis on Policy Specificity and Legislative Achievements  (d1=+7 d2=-10 pp, p=1.000, same_sign=False)
- Ideological/Constitutional Principle Emphasis  (d1=+3 d2=+0 pp, p=1.000, same_sign=False)
- Emphasis on Resume-Like, Formal, or Institutional Tone  (d1=+7 d2=-3 pp, p=1.000, same_sign=False)
- Emphasis on Self-Education and Independent Learning  (d1=-5 d2=+3 pp, p=1.000, same_sign=False)
- Emphasis on Optimism and Positive Community Engagement  (d1=+5 d2=-3 pp, p=1.000, same_sign=False)
- Reluctant Entry vs. Natural Progression to Politics  (d1=-1 d2=+0 pp, p=1.000, same_sign=False)
- Education Achieved Through Struggle  (d1=-2 d2=+1 pp, p=1.000, same_sign=False)
- Conservative/Republican Identity Explicitness  (d1=+0 d2=+1 pp, p=1.000, same_sign=False)
- Recognition and Endorsements Type  (d1=+5 d2=-5 pp, p=1.000, same_sign=False)