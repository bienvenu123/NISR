# Rwanda Double Exclusion Project

**Double Exclusion in Rwanda: Mapping Where Poor Households Are Missed by Both Social Protection and Financial Services**

NISR 2026 Big Data Hackathon, Track 2: Financial Inclusion & Poverty Reduction. Team "Devs".

## Submission summary

- **Track:** 2 - Financial Inclusion & Poverty Reduction
- **Live app:** https://rwanda-double-exclusion.streamlit.app/
- **GitHub repository:** https://github.com/bienvenu123/NISR
- **Demo video (under 3 minutes):** [demo/nisr_demo.mp4](demo/nisr_demo.mp4)
- **Android app (compact version of the dashboard):** `deliverables/rwanda_inclusion_android.apk`
- **Eligibility documents (both team members):** [student_cards/](student_cards/)
- **Data source:** NISR EICV7 2023-24, https://microdata.statistics.gov.rw/index.php/catalog

## The problem

Some of Rwanda's poorest households get no help from social protection programmes and also have no access to financial services such as savings, loans or mobile money. We call this **double exclusion**. Using NISR data, this project finds the districts where it happens most, so that government and partners can direct support to the people who need it most.

This supports the national priorities of NST2 and Vision 2050 (poverty reduction and financial inclusion).

## Key findings (EICV7 2023-24)

| Indicator | Value |
|---|---|
| Population in poverty | 27.4% |
| Poor households reached by VUP | 15.9% |
| Poor households with a bank or mobile-money account | 82.0% |
| Poor households with neither VUP nor an account | 17.5% (about 134,614 households) |

- Highest double-exclusion rates among poor households: Ngoma (29.6%), Kamonyi (29.0%), Nyanza (28.1%).
- Largest numbers of affected households: Kamonyi, Nyagatare and Nyanza (more than 10,000 each).
- For most poor households the biggest gap is social protection, not bank access: 66.6% have an account but no VUP, 17.5% have neither, 15.4% have both.
- District poverty estimates match NISR's published district rates (differences under 0.05 percentage points).

## What the dashboard shows and how to use it

The Streamlit dashboard has three pages:

1. **Dashboard (overview):** national indicators, district map, district ranking, burden chart and district profile. Use the sidebar to change the map measure, choose a district, sort districts (highest or lowest first) and download the district CSV.
2. **Innovation Lab: Pathways and Targeting:** follows poor households step by step (VUP, then account), shows the four pathway states in every district, a priority index, and a **targeting simulator**. The user chooses how many poor households a programme can reach and an allocation rule, and the tool shows how the budget would be spread across districts. It also includes a map and spatial analysis (Moran's I).
3. **Innovation Lab: Insights and Comparison:** compares a district with the national profile and with a similar "better twin" district (radar chart), compares direct and stabilised rates, and checks poverty estimates against NISR's published district rates.

Districts with fewer than 50 sampled poor households are flagged as less reliable. The tool is a decision-support tool for district planning. It is not for individual eligibility decisions.

## Android app

A compact Android app shows the same district figures on a phone (national picture, district explorer and map). The APK is in `deliverables/`; the source, offline data and build instructions are in `mobile_app/` (see [mobile_app/README.md](mobile_app/README.md)). The web dashboard remains the main application.

## Data

**Source:** NISR EICV7 2023-24 (Integrated Household Living Conditions Survey), available at https://microdata.statistics.gov.rw/index.php/catalog (see also the [catalog entry](https://microdata.statistics.gov.rw/index.php/catalog/119)).

**Raw household microdata is NOT included in this repository** because of NISR data-use terms. Only district-level aggregates and public boundaries are included:

- `outputs/eicv7_district_double_exclusion.csv`: district estimates produced by our script.
- `data/rwanda_districts.geojson`: public district boundaries (source: NISR and Rwanda Land Authority, via the [Rwanda national geodata service](https://geodata.rw/server/rest/services/basemap/District_Boundary/FeatureServer/0)). It joins through the `dist_code` property.

### EICV7 files read by the analysis

The analysis reads these cross-section files from `Microdata/Cross_Section/` (kept locally, not committed):

- `CS_EICV7_poverty_file.dta`: household poverty, geography and household/population weights.
- `CS_S01_S5_S7_Household.dta`: survey strata (`strata_id`).
- `CS_S9D1_Direct_Support.dta`, `CS_S9D2_Classic_Public_Work.dta`, `CS_S9D3_Expanded_Public_Work.dta`, `CS_S9D4_NSDS.dta`, `CS_S9D5_Financial_Services.dta`: VUP programme flags.
- `CS_S10C_Savings.dta`: financial account, mobile money and tontine measures.
- `CS_S10A1_A2_credits.dta`: loan application records and the stated reason a loan was denied.
- `CS_S9B_transfers_in.dta` records household transfers and remittances, not a verified government benefit, so it is not included in VUP coverage.

## Definitions

- **VUP:** Vision 2020 Umurenge Programme, Rwanda's main social protection programme.
- **Poor / extreme poor:** `pov_jan == 100` / `epov_jan == 100` in the poverty file.
- **District poverty rate:** population-weighted headcount using `pop_wt`.
- **VUP covered:** a household has a positive participation flag in at least one of five VUP modules.
- **Financial access:** at least one household member has a bank or mobile-money account (`s10cq4 == 1`). Tontine participation is kept separate. A wider sensitivity measure uses `s10cq1 == 1`.
- **Double exclusion:** a poor household has neither an observed VUP participation flag nor an observed bank/mobile-money account.
- **District burden:** sum of household weights for poor households classified as double-excluded. The exclusion rate among poor households is also reported.

The savings module has repeated person/account records, so the script collapses it to one household indicator before joining. VUP eligibility is not observed: the results describe non-coverage among poor households, not an eligibility gap or causal impact.

The district output also includes reported loan-denial reasons (`s10aq1 == 1`, `s10aq2`) among poor households with a recorded denial, and reported enrolment reasons (`s9d1q2 == 1`, `s9d1q3`) among poor VUP Direct Support households. These are subgroup indicators, not explanations for lacking an account, and they do not establish VUP eligibility.

## Method notes

- Household coverage estimates use the household weight (`weight`). District poverty uses `pop_wt` and reproduces the NISR Main Indicators Report to the published 0.1 percentage point.
- Standard errors use PSU clusters and `strata_id` with ratio linearisation; 95% intervals use a normal 1.96 multiplier.
- Reliability flags: 16 districts reliable, 14 to be interpreted with caution (fewer than 50 sampled poor households).
- Spatial clustering is low (Moran's I = 0.07), so district-level targeting matters more than regional targeting.

## Run it on your machine

Requires Python 3.11 or newer.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

The dashboard needs only the files in this repository (no raw microdata). Streamlit 1.57 or newer is required.

### Reproduce the district estimates (needs the raw EICV7 files)

```powershell
python scripts/analyze_eicv7.py
```

Optional paths:

```powershell
python scripts/analyze_eicv7.py --data-dir Microdata/Cross_Section --output-dir outputs
```

The script writes only district aggregates to `outputs/eicv7_district_double_exclusion.csv`. It does not write household-level records.

## Repository structure

```
README.md                  this file
dashboard.py               Streamlit entry point (overview page)
pages/                     Innovation Lab pages
lab/                       Innovation Lab analysis code
scripts/                   analysis, policy brief and presentation scripts
data/                      public district boundaries (GeoJSON)
outputs/                   district aggregate estimates (CSV)
demo/                      demo video (under 3 minutes)
deliverables/              policy brief, presentation, Android APK
mobile_app/                Android app source and build instructions
student_cards/             eligibility documents for both team members
tests/                     automated tests
requirements.txt           Python dependencies
```

## Deployment

The dashboard is deployed on Streamlit Community Cloud: repository `bienvenu123/NISR`, branch `main`, main file `dashboard.py`. The app contains district-level aggregates and public boundaries only. Free-tier apps sleep after a period without visitors; open the link and wait a few seconds for it to wake up.

## Deliverables

- Two-page policy brief, seven-slide presentation and Android APK in `deliverables/`.
- Rebuild the brief with `python scripts/build_policy_brief.py`.
- The presentation source is `scripts/build_presentation.mjs`.

## Limitations

This is a descriptive first release. District poverty estimates reproduce NISR's published benchmark, but the VUP and financial-access measures are proxies. Do not interpret non-coverage as exclusion from eligibility, and do not use district estimates to identify individual households. Districts with fewer than 50 sampled poor households need cautious interpretation.

## Declaration of AI use

AI tools were used to help write code and documentation. Every number shown in the dashboard is computed from the EICV7 data by our scripts, and the team reviewed the results.

## Declaration of originality

This submission is our own work and all sources of reference are acknowledged.

## Team

- Bienvenu UWAYEZU ([@bienvenu123](https://github.com/bienvenu123))
- Prince Joe / Joseph ([@Jocos12](https://github.com/Jocos12))

## Intellectual property

As required by the hackathon rules, participants assign the intellectual property rights in the submitted work to the National Institute of Statistics of Rwanda (NISR).
