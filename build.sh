#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv-build
source .venv-build/bin/activate
pip install -r requirements.txt -r requirements-build.txt

pyinstaller --onefile --name gpdf gpdf.py

echo "Built: dist/gpdf"
