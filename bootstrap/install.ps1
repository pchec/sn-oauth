# Bootstrap sn-oauth on Windows: ensure Python 3.8+, create a local
# virtualenv, install the package. Offers to install Python if missing.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Find-Python {
    foreach ($c in @("python", "python3", "py")) {
        $cmd = Get-Command $c -ErrorAction SilentlyContinue
        if ($cmd) {
            & $c -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { return $c }
        }
    }
    return $null
}

$py = Find-Python
if (-not $py) {
    Write-Host "Python 3.8+ was not found."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        $ans = Read-Host "Install Python now with winget? [y/N]"
        if ($ans -eq "y" -or $ans -eq "Y") {
            winget install -e --id Python.Python.3.12
        }
    } else {
        Write-Host "Please install Python 3.8+ from https://www.python.org/downloads/ and re-run this script."
        exit 1
    }
    $py = Find-Python
    if (-not $py) { Write-Host "Python still not found after install. Aborting."; exit 1 }
}

Write-Host "Using Python: $(& $py --version)"
& $py -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
& .\.venv\Scripts\python.exe -m pip install -e .
Write-Host ""
Write-Host "Installed. Next:"
Write-Host "  1) copy sn-oauth.example.json to sn-oauth.json  and fill in your instance + client_id"
Write-Host "  2) .\sn-oauth.cmd login"
