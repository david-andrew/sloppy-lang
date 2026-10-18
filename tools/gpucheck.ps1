# Check Sloppy on this Windows machine's GPU, unattended, and write one report
# (build\gpucheck\report.txt): the machine and its GPU driver, the render tests drawn through
# Vulkan on this GPU, random compute programs compared between the CPU and this GPU, and the
# example games' frame times. The Windows counterpart of tools/gpucheck.sh, for a rented machine
# reached over ssh (no desktop: the screenshot runs use SLOPPY_HEADLESS=1, no window).
# usage (from the test set's root, with bin\sloppy.exe in it):
#   powershell -ExecutionPolicy Bypass -File tools\gpucheck.ps1 [-Python C:\path\python.exe]
param([string]$Python = "")
$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)
$root = (Get-Location).Path
$out = Join-Path $root "build\gpucheck"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$rep = Join-Path $out "report.txt"
"" | Set-Content -Encoding utf8 $rep

# (as UTF-8: Windows PowerShell's Tee-Object writes UTF-16)
function Section($name) { "`n== $name" | Out-Host; "`n== $name" | Out-File -Encoding utf8 -Append $rep }
function Note($text) { $text | Out-Host; $text | Out-File -Encoding utf8 -Append $rep }

# a Python: the one given, one on the PATH, or the embeddable one from python.org (no installer)
if ($Python -eq "") {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch "WindowsApps") { $Python = $cmd.Source }
}
if ($Python -eq "") {
    $pydir = Join-Path $out "python"
    if (-not (Test-Path (Join-Path $pydir "python.exe"))) {
        $zip = Join-Path $out "python.zip"
        Invoke-WebRequest -UseBasicParsing "https://www.python.org/ftp/python/3.13.7/python-3.13.7-embed-amd64.zip" -OutFile $zip
        Expand-Archive -Force $zip $pydir
    }
    $Python = Join-Path $pydir "python.exe"
}

$env:SLOPPY_LIB = Join-Path $root "lib"
$env:SLOPPY_HEADLESS = "1"
$sloppy = Join-Path $root "bin\sloppy.exe"

Section "machine"
Note (Get-Date).ToUniversalTime().ToString("u")
Note ((Get-CimInstance Win32_OperatingSystem).Caption + " " + (Get-CimInstance Win32_OperatingSystem).Version)
Note ((Get-CimInstance Win32_Processor | Select-Object -First 1).Name)
Get-CimInstance Win32_VideoController | ForEach-Object { Note ("GPU: " + $_.Name + ", driver " + $_.DriverVersion + " (" + $_.DriverDate + ")") }
Note ("sloppy: " + (& $sloppy version 2>&1))

Section "Vulkan device"
$probe = Join-Path $out "probe.jo"
"draw = (): clear()" | Set-Content $probe
$env:SLOPPY_VULKAN = "1"; $env:SLOPPY_VK_VALIDATE = "1"; $env:SLOPPY_SCREENSHOT = (Join-Path $out "probe.png"); $env:SLOPPY_FRAMES = "3"
Note ((& $sloppy run $probe 2>&1) -join "`n")
Remove-Item Env:SLOPPY_VK_VALIDATE, Env:SLOPPY_SCREENSHOT, Env:SLOPPY_FRAMES, Env:SLOPPY_VULKAN

Section "render tests (Vulkan on this GPU, against the references)"
Note ((& $Python tools\rendertest.py --vulkan-only 2>&1) -join "`n")

Section "compute: random programs, CPU against this GPU"
$env:SLOPPY_FUZZ_COMPILER = $sloppy
Note ((& $Python tools\gpufuzz.py 200 --seed 1 --no-lavapipe 2>&1 | Select-Object -Last 15) -join "`n")

Section "shaders: random fragment shaders, software renderer against Vulkan"
Note ((& $Python tools\gpufuzz.py 100 --seed 1 --shaders --no-lavapipe 2>&1 | Select-Object -Last 15) -join "`n")

Section "games: 600 frames each through Vulkan (SLOPPY_STATS)"
foreach ($g in @("examples\rebound\rebound.jo", "examples\breakwater\breakwater.jo", "examples\dunes\dunes.jo")) {
    $exe = Join-Path $out ([IO.Path]::GetFileNameWithoutExtension($g) + ".exe")
    $b = & $sloppy build --release $g -o $exe 2>&1
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $exe)) { Note ("$g : the build failed: " + (($b | Select-Object -Last 5) -join " | ")); continue }
    $env:SLOPPY_VULKAN = "1"; $env:SLOPPY_STATS = "1"; $env:SLOPPY_FRAMES = "600"; $env:SLOPPY_SCREENSHOT = ($exe + ".png")
    $t = Measure-Command { $res = & $exe 2>&1 }
    $ok = (Test-Path ($exe + ".png")) -and $LASTEXITCODE -eq 0
    Note ("$g : " + [math]::Round($t.TotalSeconds, 2) + " s for 600 frames (exit $LASTEXITCODE, picture saved: $ok); " + (($res | Select-Object -Last 3) -join " | "))
    Remove-Item Env:SLOPPY_VULKAN, Env:SLOPPY_STATS, Env:SLOPPY_FRAMES, Env:SLOPPY_SCREENSHOT
}
Section "done"
