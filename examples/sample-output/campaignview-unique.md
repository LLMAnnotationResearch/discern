# CampaignView output: one biography per candidate

The complete saved real-run summary follows verbatim. The [walkthrough](../campaignview/README.md) explains the preparation and offline checks; the [placebo summary](../campaignview/saved_unique/placebo_r0/05_summary.md) and [complete feature table](../campaignview/features.unique.real.csv) are also supplied.

---

# discern run: real_r1  (real)

- prompt_version: discern-1
- measurement: rotate, n=600 (300/group), permutations=1440, FDR=0.05
- discovery: 193 hypotheses -> 72 candidates -> **50 validated** (FDR 0.05) + **1 suggestive** (exploratory FDR 0.1) + **0 uncorrected directional** (p<0.05)

**Direction key:** + (focal_higher) = more prevalent among 'Republican House primary candidates'; - (focal_lower) = more prevalent among 'Democratic House primary candidates'.
d1/d2 = the two independent data-half effects (validation requires the same sign in both). A positive pp value = the feature is more prevalent among 'Republican House primary candidates'; negative = more prevalent among 'Democratic House primary candidates'.

## Validated features (FDR 0.05)

### Emphasis on Conservative or Traditional Values  (+74 pp — more common among Republican House primary candidates, p=0.001)
*The biography expresses a commitment to conservative, traditional, or libertarian values (e.g., limited government, individual responsibility, constitutional rights).*
Q: Does the biography express a commitment to conservative, traditional, or libertarian values (e.g., limited government, individual responsibility, constitutional rights)?
d1=+73pp  d2=+75pp  id=c_43560849237d4065

### Narrative of Advocating for Expanded Social Programs and Government Accountability  (-60 pp — more common among Democratic House primary candidates, p=0.001)
*The biography frames the candidate as advocating for expanded social programs, government accountability, and addressing inequality.*
Q: Does the biography frame the candidate as advocating for expanded social programs and government accountability?
d1=-60pp  d2=-59pp  id=c_cfc5525c8a84a36a

### Emphasis on Conservative vs. Progressive Political Values  (+57 pp — more common among Republican House primary candidates, p=0.001)
*The biography predominantly emphasizes conservative political values (e.g., limited government, patriotism, law-and-order, opposition to government expansion) or progressive values (e.g., social justice, inclusivity, government intervention in social and economic issues).*
Q: Does the biography predominantly emphasize conservative political values over progressive values?
d1=+57pp  d2=+57pp  id=c_0fce3e131147ebd6

### Emphasis on Progressive Policy Positions  (-55 pp — more common among Democratic House primary candidates, p=0.001)
*The biography emphasizes progressive policy positions such as healthcare access, environmental protection, civil rights expansion, and social equity.*
Q: Does the biography emphasize progressive policy positions such as healthcare access, environmental protection, or civil rights expansion?
d1=-53pp  d2=-56pp  id=c_9a3cbb6a2266dad3

### Emphasis on Individual Responsibility and Private Sector Solutions  (+54 pp — more common among Republican House primary candidates, p=0.001)
*The biography emphasizes individual responsibility and private sector solutions to problems, rather than collective or government-led solutions.*
Q: Does the biography emphasize individual responsibility and private sector solutions to problems?
d1=+54pp  d2=+55pp  id=c_df9181796149e0c5

### Emphasis on Social Equity, Diversity, and Inclusion  (-53 pp — more common among Democratic House primary candidates, p=0.001)
*The biography emphasizes social equity, diversity, and inclusion as core values.*
Q: Does the biography emphasize social equity, diversity, and inclusion as core values?
d1=-53pp  d2=-53pp  id=c_0c327d19089082ac

### Emphasis on Advocacy for Marginalized Communities and Structural Reform  (-52 pp — more common among Democratic House primary candidates, p=0.001)
*The biography highlights advocacy for marginalized communities, social justice, or structural reforms such as healthcare or criminal justice reform.*
Q: Does the biography highlight advocacy for marginalized communities or structural reforms?
d1=-54pp  d2=-51pp  id=c_342dd7059c8aba6b

### Emphasis on Collective Solutions and Government's Role  (-52 pp — more common among Democratic House primary candidates, p=0.001)
*The biography emphasizes collective solutions and the government's role in addressing problems.*
Q: Does the biography emphasize collective solutions and the government's role in addressing problems?
d1=-52pp  d2=-53pp  id=c_d01857967e65c0c9

### Emphasis on Systemic or Structural Issues  (-47 pp — more common among Democratic House primary candidates, p=0.001)
*The biography frames problems as systemic or structural (e.g., inequality, discrimination) and emphasizes the need for systemic change.*
Q: Does the biography frame problems as systemic or structural (e.g., inequality, discrimination) and emphasize the need for systemic change?
d1=-49pp  d2=-45pp  id=c_55f2c5c7b7c7b175

### Emphasis on Secular Community Engagement and Social Justice  (-47 pp — more common among Democratic House primary candidates, p=0.001)
*The biography emphasizes secular community engagement and social justice activism, with little or no mention of religion.*
Q: Does the biography emphasize secular community engagement and social justice activism, with little or no mention of religion?
d1=-53pp  d2=-41pp  id=c_07b2b5f4644d6ddf

### Emphasis on Policy Priorities: Social Equity, Healthcare, Education, Environment  (-45 pp — more common among Democratic House primary candidates, p=0.001)
*The biography highlights policy priorities such as social equity, healthcare access, education, or environmental protection.*
Q: Does the biography highlight policy priorities such as social equity, healthcare access, education, or environmental protection?
d1=-43pp  d2=-47pp  id=c_81f3b7650404f703

### Emphasis on Critique of Government Regulation or Overreach  (+40 pp — more common among Republican House primary candidates, p=0.001)
*The biography includes critique or opposition to government regulation, big government, or perceived government overreach.*
Q: Does the biography include critique or opposition to government regulation, big government, or perceived government overreach?
d1=+42pp  d2=+39pp  id=c_6c4158dd334bc8e1

### Emphasis on Individual Achievement vs. Community Engagement  (+39 pp — more common among Republican House primary candidates, p=0.001)
*The biography focuses on individual achievements (business success, military service, personal accomplishments) rather than community organizing, collective action, or advocacy.*
Q: Does the biography focus more on individual achievements than on community engagement or collective action?
d1=+38pp  d2=+41pp  id=c_ca6de4e54d99e711

### Emphasis on Specific Conservative Policy Positions  (+35 pp — more common among Republican House primary candidates, p=0.001)
*The biography identifies strongly with conservative policy positions such as Second Amendment rights, opposition to Obamacare, tax reduction, pro-life stances, and opposition to government mandates.*
Q: Does the biography identify strongly with specific conservative policy positions?
d1=+31pp  d2=+38pp  id=c_60a775e3a7e51319

### Emphasis on Business or Military Credentials over Academic Credentials  (+34 pp — more common among Republican House primary candidates, p=0.001)
*The biography highlights business or military credentials as more important than academic credentials.*
Q: Does the biography highlight business or military credentials as more important than academic credentials?
d1=+30pp  d2=+37pp  id=c_ff1b9a420ea67f08

### Emphasis on Collective Action or Community Relationships  (-30 pp — more common among Democratic House primary candidates, p=0.001)
*The biography emphasizes collective action, collaboration, or strong community relationships as central to the candidate's approach.*
Q: Does the biography emphasize collective action, collaboration, or strong community relationships as central to the candidate's approach?
d1=-33pp  d2=-27pp  id=c_b06095d2a670989e

### Emphasis on Critique of Progressive or Democratic Policies  (+30 pp — more common among Republican House primary candidates, p=0.001)
*The biography critiques progressive or Democratic policies specifically.*
Q: Does the biography critique progressive or Democratic policies specifically?
d1=+29pp  d2=+31pp  id=c_d1754fcbe23c630e

### Emphasis on Listening to Community Members and Centering Their Voices  (-27 pp — more common among Democratic House primary candidates, p=0.001)
*The biography emphasizes listening to community members and centering their voices in problem-solving.*
Q: Does the biography emphasize listening to community members and centering their voices in problem-solving?
d1=-25pp  d2=-29pp  id=c_dd3c30fc72656ef4

### Emphasis on Religious Faith or Affiliation  (+27 pp — more common among Republican House primary candidates, p=0.001)
*The biography explicitly mentions religious faith, religious affiliation, or involvement in faith-based activities as a key part of identity or motivation.*
Q: Does the biography explicitly mention religious faith or affiliation as a key part of identity or motivation?
d1=+34pp  d2=+20pp  id=c_e97cd0417bff17d7

### Emphasis on Traditional American Values and Patriotism  (+27 pp — more common among Republican House primary candidates, p=0.001)
*The biography emphasizes traditional American values, patriotism, and the 'American Dream.'*
Q: Does the biography emphasize traditional American values and patriotism?
d1=+32pp  d2=+22pp  id=c_41a3083988c5c195

### Emphasis on Direct Service to Vulnerable or Marginalized Populations  (-27 pp — more common among Democratic House primary candidates, p=0.001)
*The biography describes direct service, advocacy, or work with vulnerable or marginalized populations as a core part of the candidate's background.*
Q: Does the biography describe direct service, advocacy, or work with vulnerable or marginalized populations as a core part of the candidate's background?
d1=-24pp  d2=-29pp  id=c_097cd62f7563616a

### Emphasis on Activism, Education, or Social Justice as Primary Credential  (-26 pp — more common among Democratic House primary candidates, p=0.001)
*The biography highlights activism, education, or professional roles connected to social justice, public service, or community work as the primary credential.*
Q: Does the biography highlight activism, education, or social justice as the primary credential?
d1=-23pp  d2=-30pp  id=c_f74096daf3bc0eac

### Emphasis on Support for Conservative Political Figures or Movements  (+25 pp — more common among Republican House primary candidates, p=0.001)
*The biography includes explicit mention of support for conservative political figures or movements (e.g., Trump-era policies).*
Q: Does the biography include explicit mention of support for conservative political figures or movements (e.g., Trump-era policies)?
d1=+28pp  d2=+22pp  id=c_18f50b3fe4f9336a

### Emphasis on Critique of Systemic Issues  (-23 pp — more common among Democratic House primary candidates, p=0.001)
*The biography critiques systemic issues or policies in general, rather than focusing critique on a specific party or ideology.*
Q: Does the biography critique systemic issues or policies in general, rather than focusing critique on a specific party or ideology?
d1=-19pp  d2=-27pp  id=c_3fef54f15e32410f

### Emphasis on Business Ownership or Entrepreneurship  (+22 pp — more common among Republican House primary candidates, p=0.001)
*The biography highlights business ownership, entrepreneurship, or private sector leadership as a core or primary qualification.*
Q: Does the biography highlight business ownership, entrepreneurship, or private sector leadership as a core or primary qualification?
d1=+17pp  d2=+27pp  id=c_0312baade9584bf8

### Emphasis on Credentials: Business/Entrepreneurship vs. Advanced Degrees/Professional Expertise  (+22 pp — more common among Republican House primary candidates, p=0.001)
*The biography emphasizes business ownership and entrepreneurial experience as credentials, or emphasizes advanced degrees and professional expertise (e.g., MD, PhD, law, engineering).*
Q: Does the biography emphasize business ownership or entrepreneurial experience as a credential over advanced degrees or professional expertise?
d1=+18pp  d2=+26pp  id=c_3b4190e5f3e03304

### Emphasis on Direct Personal Experience with Policy Problems  (-20 pp — more common among Democratic House primary candidates, p=0.001)
*The biography emphasizes the candidate's direct personal experience with the problems they seek to address (e.g., healthcare, housing, gun violence).*
Q: Does the biography emphasize the candidate's direct personal experience with the problems they seek to address (e.g., healthcare, housing, gun violence)?
d1=-21pp  d2=-20pp  id=c_b0a19dcff3d2c124

### Emphasis on Social Metrics such as Community Engagement and Educational Outcomes  (-20 pp — more common among Democratic House primary candidates, p=0.001)
*The biography references social metrics such as community engagement or educational outcomes as evidence of effectiveness.*
Q: Does the biography reference social metrics such as community engagement or educational outcomes as evidence of effectiveness?
d1=-22pp  d2=-18pp  id=c_e9c17d5a2a6f2803

### Emphasis on Credentials: Advanced Degrees/Professional Expertise  (-19 pp — more common among Democratic House primary candidates, p=0.001)
*The biography emphasizes advanced degrees and professional expertise (e.g., MD, PhD, law, engineering) as credentials.*
Q: Does the biography emphasize advanced degrees or professional expertise as a credential?
d1=-15pp  d2=-23pp  id=c_f2fb929a5c4e4853

### Emphasis on Education as Personal Transformation  (-18 pp — more common among Democratic House primary candidates, p=0.001)
*The biography presents education as a tool for personal transformation or overcoming obstacles, rather than as a standard credential.*
Q: Does the biography present education as a tool for personal transformation or overcoming obstacles, rather than as a standard credential?
d1=-17pp  d2=-19pp  id=c_31bab6e5ee509d1b

### Emphasis on Explicit Partisan Identification or Party Ideology Alignment  (+18 pp — more common among Republican House primary candidates, p=0.001)
*The biography explicitly identifies the candidate's political party affiliation or emphasizes alignment with the candidate's party ideology and leadership.*
Q: Does the biography explicitly identify the candidate's political party affiliation or emphasize alignment with the candidate's party ideology and leadership?
d1=+22pp  d2=+14pp  id=c_2b38421ec2bd48af

### Emphasis on Prestigious or Multiple Academic Credentials  (-17 pp — more common among Democratic House primary candidates, p=0.001)
*The biography highlights prestigious academic credentials, multiple degrees, or academic roles as a core part of the candidate's qualifications.*
Q: Does the biography highlight prestigious academic credentials, multiple degrees, or academic roles as a core part of the candidate's qualifications?
d1=-12pp  d2=-22pp  id=c_a23a8bd338b519bf

### Emphasis on Mentorship or Inspiration from Community Members  (-17 pp — more common among Democratic House primary candidates, p=0.001)
*The biography references mentorship, role models, or inspiration from community members or everyday people.*
Q: Does the biography reference mentorship, role models, or inspiration from community members or everyday people?
d1=-17pp  d2=-16pp  id=c_6e873358f2a07e7d

### Narrative of Fighting Government Overreach vs. Advocating for Expanded Social Programs  (+17 pp — more common among Republican House primary candidates, p=0.001)
*The biography frames the candidate as fighting against government overreach and bureaucracy, or as advocating for expanded social programs and government accountability.*
Q: Does the biography frame the candidate as fighting against government overreach and bureaucracy?
d1=+21pp  d2=+13pp  id=c_507585978107b3de

### Explicit Mention of Identity Categories  (-16 pp — more common among Democratic House primary candidates, p=0.001)
*The biography explicitly references the candidate's identity categories (e.g., race, gender, LGBTQ status, disability, immigrant background) as central to their story.*
Q: Does the biography explicitly reference the candidate's identity categories (e.g., race, gender, LGBTQ status, disability, immigrant background) as central to their story?
d1=-14pp  d2=-19pp  id=c_1a3b56206d15988e

### Emphasis on Personal Struggle or Adversity  (-16 pp — more common among Democratic House primary candidates, p=0.001)
*The biography emphasizes the candidate's personal struggles, hardships, or experiences of overcoming adversity, including stories related to social or systemic issues such as poverty, discrimination, or healthcare access.*
Q: Does the biography emphasize the candidate's personal struggles, hardships, or experiences of overcoming adversity, including stories related to social or systemic issues?
d1=-13pp  d2=-19pp  id=c_e729cf32031b31db

### Emphasis on Business, Military, or Local Government as Primary Credential  (+16 pp — more common among Republican House primary candidates, p=0.001)
*The biography highlights business, military, or local government experience as the candidate's primary credential.*
Q: Does the biography highlight business, military, or local government experience as the primary credential?
d1=+19pp  d2=+13pp  id=c_27cc306a517b3775

### Emphasis on Inspiration from Institutional Credentials or Elite Networks  (-16 pp — more common among Democratic House primary candidates, p=0.001)
*The biography references institutional credentials, elite education, or professional networks as sources of inspiration.*
Q: Does the biography reference institutional credentials, elite education, or professional networks as sources of inspiration?
d1=-13pp  d2=-18pp  id=c_726fc940097a3674

### Emphasis on Bipartisan Cooperation and Working Across Party Lines  (-13 pp — more common among Democratic House primary candidates, p=0.001)
*The biography highlights bipartisan cooperation or working across party lines.*
Q: Does the biography highlight bipartisan cooperation or working across party lines?
d1=-9pp  d2=-17pp  id=c_794542301324c224

### Emphasis on Policy Achievements Related to Fiscal Responsibility and Government Reform  (+13 pp — more common among Republican House primary candidates, p=0.001)
*The biography highlights specific legislative or policy achievements related to fiscal responsibility, tax reduction, government reform, or opposition to government expansion.*
Q: Does the biography highlight policy achievements related to fiscal responsibility, tax reduction, or government reform?
d1=+14pp  d2=+11pp  id=c_dc2d25ec55b6d88d

### Emphasis on Public Service, Healthcare, Education, or Social Justice Background  (-11 pp — more common among Democratic House primary candidates, p=0.001)
*The biography highlights experience in public service, healthcare, education, activism, or social justice as a primary credential.*
Q: Does the biography highlight public service, healthcare, education, activism, or social justice as a primary credential?
d1=-7pp  d2=-15pp  id=c_f862bd10c3a02575

### Emphasis on Military or Law Enforcement Background  (+12 pp — more common among Republican House primary candidates, p=0.003)
*The biography highlights military service or law enforcement experience as a significant credential or identity.*
Q: Does the biography highlight military service or law enforcement experience as a significant credential or identity?
d1=+17pp  d2=+8pp  id=c_59600fb045ec3cbf

### Emphasis on Community Service or Grassroots Engagement  (-11 pp — more common among Democratic House primary candidates, p=0.003)
*The biography emphasizes community service, grassroots organizing, or engagement with local organizations as a core part of the candidate's background.*
Q: Does the biography emphasize community service, grassroots organizing, or engagement with local organizations as a core part of the candidate's background?
d1=-5pp  d2=-17pp  id=c_af8369eca7a18595

### Emphasis on Family Background of Hardship or Marginalization  (-13 pp — more common among Democratic House primary candidates, p=0.003)
*The biography describes the candidate's family background as involving hardship, poverty, working-class roots, or experiences of marginalization.*
Q: Does the biography describe the candidate's family background as involving hardship, poverty, working-class roots, or experiences of marginalization?
d1=-7pp  d2=-20pp  id=c_74a2cfc10517fbf8

### Emphasis on Individual Achievement and Self-Made Success  (+8 pp — more common among Republican House primary candidates, p=0.004)
*The biography emphasizes individual achievement, self-made success, or upward mobility through personal effort.*
Q: Does the biography emphasize individual achievement, self-made success, or upward mobility through personal effort?
d1=+9pp  d2=+7pp  id=c_7119fc41529d0c93

### Emphasis on Professional or Technical Expertise about Policy Problems  (-10 pp — more common among Democratic House primary candidates, p=0.010)
*The biography emphasizes the candidate's professional expertise or technical knowledge about the problems they seek to address.*
Q: Does the biography emphasize the candidate's professional expertise or technical knowledge about the problems they seek to address?
d1=-8pp  d2=-12pp  id=c_25dbc95c2f9ff235

### Emphasis on Simultaneous Work and Study  (-11 pp — more common among Democratic House primary candidates, p=0.015)
*The biography describes the candidate working while studying or managing multiple responsibilities simultaneously.*
Q: Does the biography describe the candidate working while studying or managing multiple responsibilities simultaneously?
d1=-4pp  d2=-17pp  id=c_38270cd6bb4f162b

### Emphasis on National or Global Experience  (+8 pp — more common among Republican House primary candidates, p=0.028)
*The biography emphasizes the candidate's national or global experience, accomplishments, or deployments over local community ties.*
Q: Does the biography emphasize the candidate's national or global experience, accomplishments, or deployments over local community ties?
d1=+7pp  d2=+9pp  id=c_aa9ae19af2ee1ca3

### Emphasis on Diverse, Non-Traditional, or Immigrant Family Background  (-8 pp — more common among Democratic House primary candidates, p=0.029)
*The biography highlights diverse, non-traditional, immigrant, or multicultural family backgrounds as part of the candidate's identity.*
Q: Does the biography highlight diverse, non-traditional, immigrant, or multicultural family backgrounds?
d1=-9pp  d2=-7pp  id=c_21bea577c710dc67

### Emphasis on Critique of Specific Political Figures or Movements  (-6 pp — more common among Democratic House primary candidates, p=0.030)
*The biography includes explicit mention of opposition to specific political figures or movements (e.g., Trump, calls for impeachment).*
Q: Does the biography include explicit mention of opposition to specific political figures or movements (e.g., Trump, calls for impeachment)?
d1=-4pp  d2=-8pp  id=c_1a91de167cec450e


## Suggestive features (exploratory — FDR 0.1, not 0.05)

Real-but-marginal effects that clear the looser threshold. Treat as leads to confirm, not findings — the primary table above is the headline. Optionally sanity-check this tier with a placebo run.

### Emphasis on Policy Expertise or Specific Policy Positions  (-7 pp — more common among Democratic House primary candidates, p=0.067)
*The biography highlights the candidate's policy expertise, specific policy positions, or technical knowledge as a core qualification.*
Q: Does the biography highlight the candidate's policy expertise, specific policy positions, or technical knowledge as a core qualification?
d1=-5pp  d2=-9pp  id=c_437250f5be2cb860


## Uncorrected directional tendencies (exploratory — unadjusted p < 0.05)

These features have the same effect direction in both held-out halves and an unadjusted permutation p-value below 0.05, but do not pass either FDR tier. They are not multiplicity-controlled: some are expected by chance when many candidates are tested. Treat them as leads for future confirmation, not findings.

## Remaining candidates (not validated) (21)
- Emphasis on Political Insider or Established Professional Status  (d1=-7 d2=-7 pp, p=0.085, same_sign=True)
- Emphasis on Emotional, Personal, or First-Person Storytelling  (d1=-3 d2=-7 pp, p=0.131, same_sign=True)
- Emphasis on Incumbency and Established Government Service  (d1=-5 d2=-7 pp, p=0.144, same_sign=True)
- Formal, Traditional, and Achievement-Focused Tone  (d1=+6 d2=+4 pp, p=0.189, same_sign=True)
- Emphasis on Awards, Honors, or Formal Recognition  (d1=-9 d2=-1 pp, p=0.194, same_sign=True)
- Emphasis on Challenger or First-Time Candidate Status  (d1=-4 d2=-6 pp, p=0.205, same_sign=True)
- Emphasis on Policy Priorities: Economic Growth, Security, Deregulation  (d1=+5 d2=+5 pp, p=0.209, same_sign=True)
- Emphasis on Personal Experiences with Economic Success or Overcoming Obstacles  (d1=-3 d2=-5 pp, p=0.244, same_sign=True)
- Emphasis on Financial Metrics and Fundraising Success  (d1=+5 d2=+1 pp, p=0.268, same_sign=True)
- Emphasis on Traditional Family Structure and Heritage  (d1=+1 d2=+5 pp, p=0.271, same_sign=True)
- Emphasis on Sequential Education and Career Phases  (d1=+7 d2=+1 pp, p=0.298, same_sign=True)
- Emphasis on Political Outsider or Newcomer Status  (d1=-1 d2=-7 pp, p=0.314, same_sign=True)
- Emphasis on Abstract Principles and Duty-Based Language  (d1=-1 d2=-3 pp, p=0.314, same_sign=True)
- Emphasis on Family Background of Professional or Military Success  (d1=+4 d2=+3 pp, p=0.343, same_sign=True)
- Emphasis on Professional Credentials or Achievements  (d1=-2 d2=-3 pp, p=0.362, same_sign=True)
- Emphasis on Leadership, Management, or Command Experience  (d1=+0 d2=+9 pp, p=1.000, same_sign=False)
- Emphasis on Emotional Language and Personal Pronouns  (d1=+0 d2=-6 pp, p=1.000, same_sign=False)
- Emphasis on Structured, Fact-Driven, or Formal Narrative  (d1=-1 d2=+4 pp, p=1.000, same_sign=False)
- Emphasis on Overcoming Adversity in Professional Context  (d1=+1 d2=-4 pp, p=1.000, same_sign=False)
- Emphasis on Local Community Rootedness  (d1=+3 d2=-5 pp, p=1.000, same_sign=False)
- Emphasis on Solving Problems Through Expertise and Decisive Action  (d1=+4 d2=-5 pp, p=1.000, same_sign=False)