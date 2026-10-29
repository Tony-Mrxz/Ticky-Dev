# build_installer.ps1
#
# One command: compile Ticky, stage the offline speech model, produce the
# per-user setup exe.
#
#   .\build_installer.ps1                  # full installer, model bundled
#   .\build_installer.ps1 -SkipModel       # quick build without the 141 MB model
#   .\build_installer.ps1 -SkipApp         # recompile setup only, reuse dist\Ticky
#   .\build_installer.ps1 -SkipSmoke       # do not launch the bundle to test it
#
# Requires the .venv (PySide6 + faster-whisper + PyInstaller) and Inno Setup 6.

[CmdletBinding()]
param(
    [string]$Python = "",
    [string]$Iscc = "",
    [switch]$SkipApp,
    [switch]$SkipModel,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

# --- toolchain ---------------------------------------------------------------

if (-not $Python) {
    # The local project virtualenv first; CI has dependencies on the PATH python.
    foreach ($candidate in @(".venv\Scripts\Python.exe", ".venv\bin\python")) {
        $candidate = Join-Path $PSScriptRoot $candidate
        if (Test-Path -LiteralPath $candidate) { $Python = $candidate; break }
    }
    if (-not $Python) {
        $onPath = Get-Command python -ErrorAction SilentlyContinue
        if ($onPath) { $Python = $onPath.Source }
    }
}
if (-not $Python -or -not (Test-Path -LiteralPath $Python)) {
    throw "Python not found. Build from the project virtualenv; the system interpreter does not have faster-whisper installed."
}

if (-not $Iscc) {
    foreach ($candidate in @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    )) {
        if (Test-Path -LiteralPath $candidate) { $Iscc = $candidate; break }
    }
    if (-not $Iscc) {
        throw "Inno Setup compiler not found. Install it with: winget install JRSoftware.InnoSetup"
    }
}

# utils/version.py is the single source of truth: Ticky.spec stamps the exe
# metadata from it, and the update check compares releases against it.
$versionSource = Get-Content -LiteralPath "utils\version.py" -Raw
$version = [regex]::Match($versionSource, "APP_VERSION\s*=\s*['""]([^'""]+)['""]").Groups[1].Value
if (-not $version) { throw "Could not read APP_VERSION from utils\version.py" }
Write-Host "Ticky $version" -ForegroundColor Green

# --- offline speech model ----------------------------------------------------

$modelStage = Join-Path $PSScriptRoot "models\whisper"
$modelId = "models--Systran--faster-whisper-base.en"
$modelTarget = Join-Path $modelStage $modelId
$hfCache = Join-Path $env:USERPROFILE ".cache\huggingface\hub\$modelId"

if ($SkipModel) {
    Step "Skipping the bundled speech model"
    if (Test-Path -LiteralPath $modelStage) { Remove-Item -LiteralPath $modelStage -Recurse -Force }
} else {
    Step "Staging the Whisper base.en model for offline dictation"
    if (-not (Test-Path -LiteralPath (Join-Path $modelTarget "snapshots"))) {
        if (Test-Path -LiteralPath $hfCache) {
            New-Item -ItemType Directory -Force -Path $modelStage | Out-Null
            Copy-Item -LiteralPath $hfCache -Destination $modelTarget -Recurse -Force
        } else {
            Write-Host "  not in the local HF cache - downloading" -ForegroundColor Yellow
            & $Python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-base.en', cache_dir='models/whisper')"
            if ($LASTEXITCODE -ne 0) { throw "Model download failed" }
        }
    }
    # A snapshot dir can hold links; the bundle needs real bytes next to the exe.
    $modelBin = Get-ChildItem -Path (Join-Path $modelTarget "snapshots") -Recurse -Filter "model.bin" |
                Select-Object -First 1
    if (-not $modelBin -or $modelBin.Length -lt 100MB) {
        throw "Bundled model looks incomplete at $modelTarget (no model.bin over 100 MB)."
    }
    Write-Host ("  {0:N0} MB ready" -f ($modelBin.Length / 1MB))
}

# --- application bundle ------------------------------------------------------

if ($SkipApp) {
    Step "Reusing the existing bundle in dist\Ticky"
} else {
    Step "Building the onedir bundle with PyInstaller"
    & $Python -m PyInstaller --clean --noconfirm Ticky.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
}

$bundle = Join-Path $PSScriptRoot "dist\Ticky"
$exe = Join-Path $bundle "Ticky.exe"
if (-not (Test-Path -LiteralPath $exe)) { throw "Expected $exe after the build" }

if (-not (Test-Path -LiteralPath (Join-Path $bundle "_internal"))) {
    throw "dist\Ticky has no _internal folder - that is not the onedir bundle the installer expects. Delete dist\ and rebuild."
}
foreach ($required in @("_internal\base_library.zip", "_internal\PySide6")) {
    if (-not (Test-Path -LiteralPath (Join-Path $bundle $required))) {
        throw "Bundle is missing $required - the spec file needs attention."
    }
}

if (-not $SkipModel) {
    $bundledModel = Get-ChildItem -Path (Join-Path $bundle "_internal\models\whisper") -Recurse -Filter "model.bin" -ErrorAction SilentlyContinue
    if (-not $bundledModel) { throw "The speech model did not reach _internal\models\whisper - check Ticky.spec." }
    Write-Host ("  bundled model: {0:N0} MB" -f (($bundledModel | Measure-Object Length -Sum).Sum / 1MB))
}

# --- smoke test --------------------------------------------------------------

$alreadyRunning = Get-Process -Name "Ticky" -ErrorAction SilentlyContinue
if ($SkipApp -or $SkipSmoke -or $alreadyRunning) {
    if ($alreadyRunning -and -not $SkipSmoke) {
        Write-Host "  a Ticky process is already running; the single-instance guard would stop a second one from starting, so the smoke test is skipped" -ForegroundColor Yellow
    } else {
        Step "Skipping the bundle smoke test"
    }
} else {
    Step "Starting the bundle to prove it launches"
    $proc = Start-Process -FilePath $exe -PassThru
    Start-Sleep -Seconds 8
    if ($proc.HasExited) {
        throw "Ticky.exe exited with code $($proc.ExitCode). Either an import failed (set console=True in Ticky.spec to see it) or another Ticky - including a 'python main.py' dev run - holds the single-instance lock."
    }
    Stop-Process -Id $proc.Id -Force
    Write-Host "  launched and stopped cleanly"
}

# --- setup exe ---------------------------------------------------------------

Step "Compiling the installer"
& $Iscc "/DAppVersion=$version" "/DBundleDir=$bundle" "installer\Ticky.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed" }

$setup = Join-Path $PSScriptRoot "installer\output\Ticky-Setup-$version.exe"
if (-not (Test-Path -LiteralPath $setup)) { throw "ISCC reported success but $setup is missing" }

$item = Get-Item -LiteralPath $setup
Write-Host ("`nInstaller: {0}`nSize: {1:N1} MB" -f $item.FullName, ($item.Length / 1MB)) -ForegroundColor Green
Write-Host "Silent test install:  `"$($item.Name)`" /VERYSILENT /TASKS=`"desktopicon`""
