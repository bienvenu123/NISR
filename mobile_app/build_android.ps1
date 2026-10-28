$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$appRoot = Join-Path $PSScriptRoot 'app\src\main'
$buildStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$buildRoot = Join-Path $projectRoot ".work\android-build\$buildStamp"
$sdkRoot = if ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { Join-Path $env:LOCALAPPDATA 'Android\Sdk' }
$buildTools = Join-Path $sdkRoot 'build-tools\36.1.0'
$androidJar = Join-Path $sdkRoot 'platforms\android-36.1\android.jar'
$jbr = Join-Path $env:ProgramFiles 'Android\Android Studio\jbr\bin'
$env:JAVA_HOME = Split-Path -Parent $jbr
$env:PATH = "$jbr;$env:PATH"
$java = Join-Path $jbr 'java.exe'
$javac = Join-Path $jbr 'javac.exe'
$keytool = Join-Path $jbr 'keytool.exe'
$workDir = Join-Path $projectRoot '.work\android'
$finalApk = Join-Path $projectRoot 'deliverables\rwanda_inclusion_android.apk'

foreach ($required in @(
    (Join-Path $buildTools 'aapt2.exe'), (Join-Path $buildTools 'd8.bat'),
    (Join-Path $buildTools 'zipalign.exe'), (Join-Path $buildTools 'apksigner.bat'),
    $androidJar, $java, $javac, $keytool,
    (Join-Path $appRoot 'assets\district_estimates.csv'),
    (Join-Path $appRoot 'assets\district_boundaries.geojson')
)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required Android build file not found: $required" }
}

New-Item -ItemType Directory -Force $buildRoot, $workDir, (Split-Path -Parent $finalApk) | Out-Null
$compiledResources = Join-Path $buildRoot 'compiled-resources.zip'
$resourcesApk = Join-Path $buildRoot 'resources.apk'
$generated = Join-Path $buildRoot 'generated'
$classes = Join-Path $buildRoot 'classes'
$dex = Join-Path $buildRoot 'dex'
$unsigned = Join-Path $buildRoot 'unsigned.apk'
$aligned = Join-Path $buildRoot 'aligned.apk'
$keystore = Join-Path $workDir 'android-debug.keystore'

New-Item -ItemType Directory -Force $buildRoot, $generated, $classes, $dex | Out-Null
$localAndroidJar = Join-Path $buildRoot 'android.jar'
Copy-Item -LiteralPath $androidJar -Destination $localAndroidJar

& (Join-Path $buildTools 'aapt2.exe') compile --dir (Join-Path $appRoot 'res') -o $compiledResources
if ($LASTEXITCODE -ne 0) { throw 'Android resource compilation failed.' }

& (Join-Path $buildTools 'aapt2.exe') link `
    -o $resourcesApk `
    -I $localAndroidJar `
    --manifest (Join-Path $appRoot 'AndroidManifest.xml') `
    --java $generated `
    -A (Join-Path $appRoot 'assets') `
    --min-sdk-version 23 `
    --target-sdk-version 35 `
    --version-code 2 `
    --version-name '1.1' `
    --debug-mode `
    $compiledResources
if ($LASTEXITCODE -ne 0) { throw 'Android resource linking failed.' }

$source = Join-Path $appRoot 'java\rw\nisr\doubleexclusion\MainActivity.java'
$rJava = Join-Path $generated 'rw\nisr\doubleexclusion\R.java'
& $javac --release 17 -classpath $localAndroidJar -d $classes $rJava $source
if ($LASTEXITCODE -ne 0) { throw 'Java compilation failed.' }

$classesJar = Join-Path $buildRoot 'classes.jar'
Push-Location $classes
try {
    & (Join-Path $jbr 'jar.exe') cf $classesJar .
    if ($LASTEXITCODE -ne 0) { throw 'Packaging compiled Java classes failed.' }
} finally { Pop-Location }

& (Join-Path $buildTools 'd8.bat') --min-api 23 --lib $localAndroidJar --output $dex $classesJar
if ($LASTEXITCODE -ne 0) { throw 'DEX conversion failed.' }

Copy-Item -LiteralPath $resourcesApk -Destination $unsigned -Force
Push-Location $dex
try {
    & (Join-Path $jbr 'jar.exe') uf $unsigned 'classes.dex'
    if ($LASTEXITCODE -ne 0) { throw 'Adding compiled app code to APK failed.' }
} finally { Pop-Location }

& (Join-Path $buildTools 'zipalign.exe') -f -p 4 $unsigned $aligned
if ($LASTEXITCODE -ne 0) { throw 'APK alignment failed.' }

if (-not (Test-Path -LiteralPath $keystore)) {
    & $keytool -genkeypair -v -keystore $keystore -storepass android -alias androiddebugkey `
        -keypass android -keyalg RSA -keysize 2048 -validity 10000 `
        -dname 'CN=Android Debug,O=Android,C=US'
    if ($LASTEXITCODE -ne 0) { throw 'Creating a local debug signing key failed.' }
}

& (Join-Path $buildTools 'apksigner.bat') sign --ks $keystore --ks-key-alias androiddebugkey `
    --ks-pass pass:android --key-pass pass:android --v4-signing-enabled false --out $finalApk $aligned
if ($LASTEXITCODE -ne 0) { throw 'APK signing failed.' }

& (Join-Path $buildTools 'apksigner.bat') verify --verbose $finalApk
if ($LASTEXITCODE -ne 0) { throw 'APK signature verification failed.' }
Write-Host "Built Android app: $finalApk"
