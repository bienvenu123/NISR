# Rwanda Inclusion Android app

An offline-first Android companion to the EICV7 district dashboard. It includes national weighted indicators, a tappable district map, a searchable district ranking, district profiles and approximate confidence intervals.

## Build the APK on Windows

The project uses the Android SDK installed with Android Studio. In PowerShell, from the NISR project folder, run:

```powershell
.\mobile_app\build_android.ps1
```

The signed debug APK is written to `deliverables/rwanda_inclusion_android.apk`. Copy it to an Android phone and open the APK to install. Android may ask you to allow installation from the file manager you use.

The build script requires Android SDK platform 36.1, Build Tools 36.1.0, and the Android Studio Java runtime. Set `ANDROID_SDK_ROOT` if your SDK is installed somewhere other than `%LOCALAPPDATA%\Android\Sdk`.

## Install from the live dashboard

After the dashboard update is deployed, open [rwanda-double-exclusion.streamlit.app](https://rwanda-double-exclusion.streamlit.app) on an Android phone and use **Download Android app (APK)** in the sidebar. Open the downloaded APK to install it. Android may ask you to allow installs from your browser. This is a debug-signed sideload APK for project use; it is not listed in Google Play.

## Live district data

The app keeps a bundled district CSV as an offline fallback and checks the public GitHub raw file when it opens. Tap **Refresh** on the overview to fetch the latest committed version without rebuilding or reinstalling the APK. The feed is `outputs/eicv7_district_double_exclusion.csv` on the `main` branch, so updates become available after the regenerated district summary is pushed to GitHub. This requires the repository to be public; the CSV contains district aggregates only.

District profiles include the EICV7-reported reasons for denied loans and VUP Direct Support enrollment, where the district sample supports an estimate. These apply only to the relevant respondents. They do not identify why a household lacks a bank/mobile account or determine VUP eligibility.

The former local feed remains available for emulator development if needed:

```powershell
python .\scripts\serve_mobile_data.py
```

The app sends no household data; it only downloads the district-level aggregate CSV. The local development feed binds to `127.0.0.1` and is intended for the emulator on this computer. If the GitHub feed is unavailable, the app continues to show its bundled offline snapshot and offers **Refresh** to retry.

To rebuild the fallback snapshot after regenerating the analysis:

```powershell
Copy-Item .\outputs\eicv7_district_double_exclusion.csv .\mobile_app\app\src\main\assets\district_estimates.csv -Force
.\mobile_app\build_android.ps1
```

The built APK is portable, works offline, and can refresh from GitHub on a physical phone with internet access.

The APK is debug-signed for installation and review. A Play Store release requires a production signing key and release packaging.
