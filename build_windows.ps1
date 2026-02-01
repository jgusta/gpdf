$ErrorActionPreference = "Stop"

python -m venv .venv-build
. .\.venv-build\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-build.txt

pyinstaller --onefile --name gpdf gpdf.py
pyinstaller --onefile --windowed --name gpdf_app gpdf_app.py

Write-Host "Built: dist\gpdf.exe"
Write-Host "Built: dist\gpdf_app.exe"
