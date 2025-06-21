# PowerShell script: Nuitka build for AlarmServer (UTF-8 encoding, no BOM)
# Please activate your virtual environment before running

# 0. Check for MSVC build environment
Write-Host "[MSVC] Checking for Microsoft Visual C++ Build Tools..."
$vswhere = [System.IO.Path]::Combine($Env:ProgramFiles, 'Microsoft Visual Studio', 'Installer', 'vswhere.exe')
if (!(Test-Path $vswhere)) {
    $vswhere = [System.IO.Path]::Combine(${Env:ProgramFiles(x86)}, 'Microsoft Visual Studio', 'Installer', 'vswhere.exe')
}
if (Test-Path $vswhere) {
    $msvc = & "$vswhere" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
    if ($msvc) {
        Write-Host "[MSVC] Visual Studio C++ Build Tools found at: $msvc"
    } else {
        Write-Host "[MSVC] ERROR: Visual Studio C++ Build Tools not found! Please install Visual Studio C++ Build Tools first."
        exit 1
    }
} else {
    Write-Host "[MSVC] ERROR: vswhere.exe not found! Please make sure Visual Studio Installer is installed."
    exit 1
}

# 1. Install Nuitka and dependencies if not present
Write-Host "[Nuitka] Checking and installing dependencies..."
pip install --upgrade nuitka wheel ordered-set zstandard

# 2. Set parameters
$mainScript = "main.py"
$outputDir = "build_nuitka"
$extraData = @()

# To include static resources (e.g. resources folder), add:
# $extraData += '--include-data-dir=resources=resources'

# 3. Build Nuitka command (as a single string for PowerShell's Invoke-Expression)
$nuitkaCmd = @(
    "python -m nuitka",
    "--standalone",
    "--onefile",
    "--enable-plugin=tk-inter",
    "--include-package=application",
    "--include-package=core",
    "--include-package=ui",
    "--include-module=application.http.ui_config_tab",
    "--include-module=application.kafka.ui_config_tab",
    "--include-module=application.rmq.ui_config_tab",
    "--msvc=latest",
    "--lto=no",
    "--output-dir=$outputDir"
)
$nuitkaCmd += $extraData
$nuitkaCmd += $mainScript

# Combine all arguments into a single command string
$cmdStr = $nuitkaCmd -join ' '

# 4. Run build using Invoke-Expression for correct command parsing
Write-Host "[Nuitka] Building..."
Invoke-Expression $cmdStr

Write-Host "[Nuitka] Build complete. Output in $outputDir."
