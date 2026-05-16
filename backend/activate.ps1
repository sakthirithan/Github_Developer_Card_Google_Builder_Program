param()
$venv = Join-Path $PSScriptRoot '.venv'
if (-not (Test-Path $venv)) {
    Write-Host "Creating virtual environment at $venv"
    python -m venv $venv
}
# Allow activation within this PowerShell process
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force | Out-Null
$activate = Join-Path $venv 'Scripts\Activate.ps1'
if (Test-Path $activate) {
    Write-Host "Activating virtual environment..."
    . $activate
} else {
    Write-Error "Activate.ps1 not found at $activate"
}
