# Rwanda Double Exclusion Project

EICV7 analysis for **Double Exclusion in Rwanda: Mapping Poor Households' Gaps in VUP Social Protection and Financial Access**.

## Data

The analysis reads these EICV7 cross-section files from `Microdata/Cross_Section/`:

- `CS_EICV7_poverty_file.dta`: household poverty, geography and household/population weights.
- `CS_S01_S5_S7_Household.dta`: survey strata (`strata_id`).
- `CS_S9D1_Direct_Support.dta`, `CS_S9D2_Classic_Public_Work.dta`, `CS_S9D3_Expanded_Public_Work.dta`, `CS_S9D4_NSDS.dta`, `CS_S9D5_Financial_Services.dta`: VUP program flags.
- `CS_S10C_Savings.dta`: financial account, mobile money and tontine measures.
- `CS_S10A1_A2_credits.dta`: loan application records and the respondent-stated reason a loan was denied.
- `CS_S9B_transfers_in.dta` is available but records household transfers/remittances in, not a verified government social-protection benefit; it is not included in VUP coverage.

The [official NISR microdata catalog](https://microdata.statistics.gov.rw/index.php/catalog/119) identifies EICV7 2023-2024; the [NISR poverty profile](https://statistics.gov.rw/sites/default/files/documents/2025-07/EICV7_Poverty%20Profile.pdf) says fieldwork ran from October 2023 to October 2024. Confirm metadata and data-use terms with NISR before publishing. Do not commit or share raw microdata.

District boundaries are stored in `data/rwanda_districts.geojson`. The file was downloaded from the [Rwanda national geodata district boundary service](https://geodata.rw/server/rest/services/basemap/District_Boundary/FeatureServer/0); the layer lists NISR and the Rwanda Land Authority as source/copyright. It joins through the `dist_code` property.

## Definitions

- **Poor / extreme poor:** `pov_jan == 100` / `epov_jan == 100` in the poverty file.
- **District poverty rate:** population-weighted headcount using `pop_wt`.
- **VUP covered:** a household has a positive participation flag in at least one of five VUP modules.
- **Financial access:** at least one household member has a bank or mobile-money account (`s10cq4 == 1`). Tontine participation is kept separate. A wider sensitivity measure uses `s10cq1 == 1`, whose label includes a financial institution, mobile money, or tontine.
- **Double exclusion:** a poor household has neither an observed VUP participation flag nor an observed bank/mobile-money account.
- **District burden:** sum of household weights for poor households classified as double-excluded. The exclusion rate among poor households is also reported.

The savings module has repeated person/account records, so the script collapses it to one household indicator before joining. VUP eligibility is not observed; these results describe non-coverage among poor households, not a program eligibility gap or causal impact.

The district output also includes reported loan-denial reasons among poor households with a denied loan recorded, and reported enrollment reasons among poor VUP Direct Support households. These are subgroup indicators, not explanations for lacking a bank/mobile account, and they do not establish VUP eligibility. Households can contribute to more than one loan-denial reason when multiple credit records are present; subgroup sample counts are included for context.

- Loan-denial responses use `s10aq1 == 1` and the recorded `s10aq2` category: insufficient income, insufficient collateral, debt-history problems, unclear loan purpose, or other reason. Each reason is collapsed to a household indicator before estimating its weighted share among poor households with a recorded denial reason.
- VUP Direct Support enrollment responses use `s9d1q2 == 1` and `s9d1q3`: household had no workers, someone cared for a person with severe disability, or respondent did not know. Estimates are weighted shares among poor households reporting Direct Support.

## Reproduce the district estimates

With Python, pandas and numpy installed:

```powershell
python scripts/analyze_eicv7.py
```

Optional paths:

```powershell
python scripts/analyze_eicv7.py --data-dir Microdata/Cross_Section --output-dir outputs
```

The script writes only district aggregates to `outputs/eicv7_district_double_exclusion.csv`; it does not write household-level derived records. Household coverage estimates use `weight`. District poverty uses `pop_wt` and is checked against the NISR Main Indicators Report to the published 0.1 percentage point. Standard errors use PSU clusters and `strata_id` with ratio linearization; the 95% intervals use a normal 1.96 multiplier. Review them against NISR's full survey design documentation before publication.

## Run the dashboard

Install the packages in `requirements.txt`, then launch the app from the project root:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run dashboard.py
```

The dashboard provides a district choropleth, selectable measures, district ranking and profile, burden chart, weighted national summaries, reliability notes, definitions and a CSV download. Streamlit 1.57 or newer is required.

## Deliverables

The current analysis outputs are in `outputs/eicv7_district_double_exclusion.csv`. The two-page policy brief, seven-slide presentation and installable Android APK are in `deliverables/`.

The Android app source, offline aggregate data assets and Windows build instructions are in `mobile_app/`. Build a fresh APK with `mobile_app/build_android.ps1`; see [the mobile app README](mobile_app/README.md) for installation steps. The app contains only district aggregates and public boundaries, not household-level microdata.

Rebuild the brief after changing its text or analysis values:

```powershell
python scripts/build_policy_brief.py
```

The presentation source is `scripts/build_presentation.mjs`. It uses the OpenAI Artifact Tool package and the presentation skill's validation tools. Set `RUNTIME_NODE_MODULES` to the directory containing `@oai/artifact-tool`, then run from the project root with Node.js. Each rebuild creates a timestamped validated PPTX in `deliverables/`; the current presentation is already included there.

`requirements.txt` includes the analysis, dashboard and brief dependencies. The raw `.dta` microdata stays in the local `Microdata/` folder and is excluded from version control; share only aggregate outputs unless NISR's data-use terms allow more.

## Interpretation and status

This is a descriptive first release. District poverty estimates reproduce NISR's published benchmark, but the VUP and financial-access measures remain proxies. Do not interpret non-coverage as exclusion from eligibility, or use district estimates to identify individual households. Districts with fewer than 50 sampled poor households are flagged and need cautious interpretation.
