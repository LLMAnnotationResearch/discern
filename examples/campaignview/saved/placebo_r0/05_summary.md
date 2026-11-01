# discern run: placebo_r0  (placebo)

- prompt_version: discern-1
- measurement: rotate, n=600 (300/group), permutations=1540, FDR=0.05
- discovery: 182 hypotheses -> 77 candidates -> **0 validated** (FDR 0.05) + **0 suggestive** (exploratory FDR 0.1) + **3 uncorrected directional** (p<0.05)

**Direction key:** + (focal_higher) = more prevalent among 'Republican House primary candidates'; - (focal_lower) = more prevalent among 'Democratic House primary candidates'.
d1/d2 = the two independent data-half effects (validation requires the same sign in both). A positive pp value = the feature is more prevalent among 'Republican House primary candidates'; negative = more prevalent among 'Democratic House primary candidates'.

## Validated features (FDR 0.05)


## Suggestive features (exploratory — FDR 0.1, not 0.05)

Real-but-marginal effects that clear the looser threshold. Treat as leads to confirm, not findings — the primary table above is the headline. Optionally sanity-check this tier with a placebo run.


## Uncorrected directional tendencies (exploratory — unadjusted p < 0.05)

These features have the same effect direction in both held-out halves and an unadjusted permutation p-value below 0.05, but do not pass either FDR tier. They are not multiplicity-controlled: some are expected by chance when many candidates are tested. Treat them as leads for future confirmation, not findings.

### Personal Interests Inclusion  (+12 pp — more common among Republican House primary candidates, p=0.006)
*The biography includes references to personal hobbies or family activities.*
Q: Does the biography include references to personal hobbies or family activities?
d1=+14pp  d2=+10pp  id=c_8fe4e87fb4cb253b

### Tone of Narrative (Populist vs. Formal)  (-8 pp — more common among Democratic House primary candidates, p=0.018)
*The narrative adopts a populist tone or a formal/authoritative tone.*
Q: Does the biography adopt a populist tone (vs. a formal/authoritative tone)?
d1=-11pp  d2=-4pp  id=c_3c7f03abd9bfa818

### Grassroots vs. Credentials Emphasis  (-7 pp — more common among Democratic House primary candidates, p=0.030)
*The narrative presents the candidate as grassroots/community-oriented or emphasizes credentials/formal education.*
Q: Does the biography present the candidate as grassroots/community-oriented (vs. emphasizing credentials/formal education)?
d1=-9pp  d2=-5pp  id=c_4aa647a808549f1c

## Remaining candidates (not validated) (74)
- Narrative Tone: Personal/Resilient vs. Urgent/Activist  (d1=+5 d2=+5 pp, p=0.174, same_sign=True)
- Diversity of Career Experiences  (d1=-6 d2=-3 pp, p=0.208, same_sign=True)
- Traditional/Working-Class Background Emphasis  (d1=-8 d2=-1 pp, p=0.221, same_sign=True)
- Emphasis on Business or Operational Leadership  (d1=+4 d2=+5 pp, p=0.264, same_sign=True)
- Career Politician Status  (d1=-3 d2=-6 pp, p=0.265, same_sign=True)
- Patriotism vs. Problem Focus  (d1=+7 d2=+2 pp, p=0.270, same_sign=True)
- Business vs. Public Service Emphasis  (d1=+3 d2=+5 pp, p=0.302, same_sign=True)
- Political Network Emphasis  (d1=-1 d2=-3 pp, p=0.306, same_sign=True)
- Emphasis on Constituent Relationships and Community Roots  (d1=-5 d2=-1 pp, p=0.308, same_sign=True)
- Narrative Length and Detail  (d1=+5 d2=+1 pp, p=0.314, same_sign=True)
- Intellectual vs. Practical Knowledge Emphasis  (d1=+3 d2=+4 pp, p=0.316, same_sign=True)
- Emphasis on Community Service and Advocacy  (d1=+4 d2=+3 pp, p=0.317, same_sign=True)
- Emphasis on Urban/Diverse vs. Rural/Traditional Background  (d1=-3 d2=-4 pp, p=0.317, same_sign=True)
- Political Establishment Positioning  (d1=-2 d2=-5 pp, p=0.337, same_sign=True)
- Emphasis on Fiscal Conservatism and Government Reduction  (d1=-3 d2=-3 pp, p=0.339, same_sign=True)
- Expertise vs. Relatability Positioning  (d1=+3 d2=+3 pp, p=0.350, same_sign=True)
- Partisan Lean / Ideological Orientation  (d1=+6 d2=+1 pp, p=0.366, same_sign=True)
- Scale of Service Orientation  (d1=+2 d2=+3 pp, p=0.380, same_sign=True)
- Emphasis on Economic Development and Job Creation  (d1=+3 d2=+1 pp, p=0.387, same_sign=True)
- Practitioner vs. Expert Framing  (d1=-1 d2=-1 pp, p=0.389, same_sign=True)
- Mention of Awards and Honors  (d1=-2 d2=-3 pp, p=0.391, same_sign=True)
- Patriotic and Political Framing  (d1=+3 d2=+1 pp, p=0.398, same_sign=True)
- Emphasis on Policy Expertise and Legislative Detail  (d1=+4 d2=+1 pp, p=0.405, same_sign=True)
- Emphasis on Local vs. Systemic/National Issues  (d1=-2 d2=-1 pp, p=0.422, same_sign=True)
- Disruption vs. Stability  (d1=-1 d2=-2 pp, p=0.438, same_sign=True)
- Local vs. National Focus  (d1=-3 d2=-1 pp, p=0.443, same_sign=True)
- Emphasis on Collaboration and Bipartisanship  (d1=-2 d2=-2 pp, p=0.454, same_sign=True)
- Individual vs. Collective Emphasis  (d1=+2 d2=+1 pp, p=0.483, same_sign=True)
- Emphasis on National Security and Defense  (d1=+11 d2=-3 pp, p=1.000, same_sign=False)
- Narrative Structure: Anecdotal and Descriptive vs. Formal and Structured  (d1=-8 d2=+1 pp, p=1.000, same_sign=False)
- Problem Scale and Class Positioning  (d1=+3 d2=-9 pp, p=1.000, same_sign=False)
- Emphasis on Board, Committee, or Institutional Leadership  (d1=+5 d2=+0 pp, p=1.000, same_sign=False)
- Emphasis on Military Service  (d1=+13 d2=-7 pp, p=1.000, same_sign=False)
- Accomplishment Framing  (d1=-7 d2=+2 pp, p=1.000, same_sign=False)
- Biographical Voice and Perspective  (d1=+5 d2=-11 pp, p=1.000, same_sign=False)
- Religious Content  (d1=+5 d2=+0 pp, p=1.000, same_sign=False)
- Emphasis on Family Background and Structure  (d1=-6 d2=+1 pp, p=1.000, same_sign=False)
- Ideological Consistency vs. Journey  (d1=+5 d2=-1 pp, p=1.000, same_sign=False)
- Emphasis on Professional or Legislative Experience  (d1=+1 d2=-5 pp, p=1.000, same_sign=False)
- Emphasis on Grassroots or Non-Political Background  (d1=+0 d2=-4 pp, p=1.000, same_sign=False)
- Emphasis on Values-Based or Ideological Messaging  (d1=-1 d2=+5 pp, p=1.000, same_sign=False)
- Emphasis on Scientific Expertise and Evidence-Based Policymaking  (d1=-1 d2=+5 pp, p=1.000, same_sign=False)
- Frustration with Status Quo  (d1=-4 d2=+0 pp, p=1.000, same_sign=False)
- Emphasis on Traditional Values, Family, and Faith  (d1=+6 d2=-3 pp, p=1.000, same_sign=False)
- Vulnerable Population Focus  (d1=+8 d2=-5 pp, p=1.000, same_sign=False)
- Corporate vs. Grassroots Funding  (d1=-3 d2=+0 pp, p=1.000, same_sign=False)
- Emphasis on Personal Adversity and Resilience  (d1=-4 d2=+1 pp, p=1.000, same_sign=False)
- Career Trajectory Pattern  (d1=+0 d2=+3 pp, p=1.000, same_sign=False)
- Personal vs. Professional Focus  (d1=-5 d2=+3 pp, p=1.000, same_sign=False)
- Traditional Values vs. Progressive Reform  (d1=+4 d2=-1 pp, p=1.000, same_sign=False)
- Emphasis on Academic Credentials and Elite Education  (d1=+4 d2=-2 pp, p=1.000, same_sign=False)
- Locality Emphasis  (d1=+3 d2=-1 pp, p=1.000, same_sign=False)
- Policy Priority Differences  (d1=+3 d2=-5 pp, p=1.000, same_sign=False)
- Emphasis on Social Justice, Diversity, and Inclusion  (d1=+2 d2=-4 pp, p=1.000, same_sign=False)
- Community Engagement vs. Professionalism  (d1=+0 d2=-2 pp, p=1.000, same_sign=False)
- Educational Detail  (d1=-1 d2=+2 pp, p=1.000, same_sign=False)
- Emphasis on Policy Solutions Grounded in Research  (d1=+1 d2=-3 pp, p=1.000, same_sign=False)
- Emphasis on Practical Experience or Work Ethic  (d1=+0 d2=-1 pp, p=1.000, same_sign=False)
- Emphasis on Demographic Representation  (d1=-7 d2=+5 pp, p=1.000, same_sign=False)
- Community and Family Values Emphasis  (d1=-2 d2=+1 pp, p=1.000, same_sign=False)
- Progressive vs. Conservative Values  (d1=+2 d2=-3 pp, p=1.000, same_sign=False)
- Institutional Reform vs. Anti-Establishment Positioning  (d1=-3 d2=+4 pp, p=1.000, same_sign=False)
- Election Integrity Focus  (d1=+0 d2=-1 pp, p=1.000, same_sign=False)
- Emphasis on Organizational Affiliations  (d1=+2 d2=-1 pp, p=1.000, same_sign=False)
- Professional Sector Focus  (d1=-3 d2=+3 pp, p=1.000, same_sign=False)
- Educational Credential Emphasis  (d1=+0 d2=-1 pp, p=1.000, same_sign=False)
- Specific Policy Proposals  (d1=+5 d2=-5 pp, p=1.000, same_sign=False)
- Policy Priority Focus  (d1=+4 d2=-3 pp, p=1.000, same_sign=False)
- Expressed Values  (d1=+1 d2=+0 pp, p=1.000, same_sign=False)
- Emphasis on Ideological Consistency and Opposition  (d1=+1 d2=-1 pp, p=1.000, same_sign=False)
- Emphasis on Published Work or Public Intellectual Contributions  (d1=-3 d2=+3 pp, p=1.000, same_sign=False)
- Political Outsider or Newcomer Status  (d1=+1 d2=-1 pp, p=1.000, same_sign=False)
- Narrative Framing of Candidacy Motivation  (d1=-1 d2=+1 pp, p=1.000, same_sign=False)
- Explicit Political Opposition  (d1=-3 d2=+3 pp, p=1.000, same_sign=False)