#!/usr/bin/env python3
import hashlib
import json
import re
import urllib.request
from pathlib import Path


REPO = "jgusta/gpdf"
FORMULA_PATH = Path(__file__).resolve().parents[1] / "Formula" / "gpdf.rb"
ASSETS = {
    "mac": "gpdf-macos-latest",
    "linux": "gpdf-ubuntu-latest",
}


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "gpdf-formula-updater"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _sha256(url: str) -> str:
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    release = _get_json(f"https://api.github.com/repos/{REPO}/releases/latest")
    tag = release.get("tag_name", "")
    if not tag.startswith("v"):
        raise SystemExit(f"Unexpected tag: {tag}")
    version = tag[1:]

    base = f"https://github.com/{REPO}/releases/download/{tag}"
    shas = {}
    for key, name in ASSETS.items():
        url = f"{base}/{name}"
        shas[key] = _sha256(url)

    text = FORMULA_PATH.read_text(encoding="utf-8")
    text = re.sub(r'version\s+"[^"]+"', f'version "{version}"', text)
    text = re.sub(
        r'sha256\s+"[^"]+"',
        lambda m, _it=iter([shas["mac"], shas["linux"]]): f'sha256 "{next(_it)}"',
        text,
        count=2,
    )
    FORMULA_PATH.write_text(text, encoding="utf-8")
    print(f"Updated {FORMULA_PATH} to {version}")


if __name__ == "__main__":
    main()
