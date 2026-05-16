PowerShell activation helper

Usage (PowerShell):

1. Open PowerShell in the `backend` folder.
2. Run the helper to create and activate the venv:

```powershell
.\activate.ps1
```

This script will:

- create a `.venv` if it doesn't exist (`python -m venv .venv`)
- set the process execution policy to allow activation
- dot-source the `Activate.ps1` so your shell becomes activated

Manual alternative commands:

```powershell
# create venv if needed
python -m venv .venv
# allow script execution for this session
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
# activate
. .\.venv\Scripts\Activate.ps1
```

Note: In PowerShell you should use `Activate.ps1` (not the `activate` batch file used by CMD).
