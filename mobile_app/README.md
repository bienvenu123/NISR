# Rwanda Inclusion Android app

An offline-first Android companion to the EICV7 district dashboard. It includes national weighted indicators, a tappable district map, a searchable district ranking, district profiles and approximate confidence intervals.

## Build the APK on Windows

The project uses the Android SDK installed with Android Studio. In PowerShell, from the NISR project folder, run:

```powershell
.\mobile_app\build_android.ps1
```

The signed debug APK is written to `deliverables/rwanda_inclusion_android.apk`. Copy it to an Android phone and open the APK to install. Android may ask you to allow installation from the file manager you use.

The build script requires Android SDK platform 36.1, Build Tools 36.1.0, and the Android Studio Java runtime. Set `ANDROID_SDK_ROOT` if your SDK is installed somewhere other than `%LOCALAPPDATA%\Android\Sdk`.

## Data and privacy

The app bundles `district_estimates.csv` and the public district boundary GeoJSON. These are district-level aggregates and boundaries; raw household microdata is not included. The app requests no internet permission and its core screens work offline.

After regenerating the analysis CSV, refresh the bundled copy and rebuild:

```powershell
Copy-Item .\outputs\eicv7_district_double_exclusion.csv .\mobile_app\app\src\main\assets\district_estimates.csv -Force
.\mobile_app\build_android.ps1
```

The APK is debug-signed for installation and review. A Play Store release requires a production signing key and release packaging.
