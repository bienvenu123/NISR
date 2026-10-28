# Rwanda Inclusion Android app

An offline-first Android companion to the EICV7 district dashboard. It includes national weighted indicators, a tappable district map, a searchable district ranking, district profiles and approximate confidence intervals.

## Build the APK on Windows

The project uses the Android SDK installed with Android Studio. In PowerShell, from the NISR project folder, run:

```powershell
.\mobile_app\build_android.ps1
```

The signed debug APK is written to `deliverables/rwanda_inclusion_android.apk`. Copy it to an Android phone and open the APK to install. Android may ask you to allow installation from the file manager you use.

The build script requires Android SDK platform 36.1, Build Tools 36.1.0, and the Android Studio Java runtime. Set `ANDROID_SDK_ROOT` if your SDK is installed somewhere other than `%LOCALAPPDATA%\Android\Sdk`.

## Live district data

The app keeps a bundled district CSV as an offline fallback, then checks the local data feed when it opens. Tap **Refresh** on the overview to fetch the current district CSV without rebuilding or reinstalling the APK. The feed reads `outputs/eicv7_district_double_exclusion.csv` on every request, so rerun the analysis first when you need to update the results.

District profiles include the EICV7-reported reasons for denied loans and VUP Direct Support enrollment, where the district sample supports an estimate. These apply only to the relevant respondents. They do not identify why a household lacks a bank/mobile account or determine VUP eligibility.

Start the feed from the project root and leave its terminal running:

```powershell
python .\scripts\serve_mobile_data.py
```

The emulator reaches the computer through Android's `10.0.2.2` host alias. If the feed is unavailable, the app continues to show its bundled offline snapshot and offers **Refresh** to retry. The app sends no household data; it only downloads the district-level aggregate CSV. The local feed binds to `127.0.0.1` and is intended for the emulator on this computer.

To rebuild the fallback snapshot after regenerating the analysis:

```powershell
Copy-Item .\outputs\eicv7_district_double_exclusion.csv .\mobile_app\app\src\main\assets\district_estimates.csv -Force
.\mobile_app\build_android.ps1
```

The built APK is still portable and works offline. To use live updates on a physical phone, the feed must be hosted on a reachable, secured HTTPS endpoint and the Android data URL and network security settings must be configured for that host.

The APK is debug-signed for installation and review. A Play Store release requires a production signing key and release packaging.
