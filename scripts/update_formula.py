#!/usr/bin/env python3
import argparse
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


def _latest_release(tag: str | None) -> dict:
    if tag:
        return _get_json(f"https://api.github.com/repos/{REPO}/releases/tags/{tag}")
    releases = _get_json(f"https://api.github.com/repos/{REPO}/releases")
    if not releases:
        raise SystemExit("No releases found")
    return releases[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="release tag (e.g. v0.1.1)")
    args = parser.parse_args()

    release = _latest_release(args.tag)
    tag = release.get("tag_name", "")
    if not tag.startswith("v"):
        raise SystemExit(f"Unexpected tag: {tag}")
    version = tag[1:]

    shas = {}
    for key, name in ASSETS.items():
        assets = release.get("assets", [])
        url = ""
        for asset in assets:
            if asset.get("name") == name:
                url = asset.get("browser_download_url", "")
                break
        if not url:
            raise SystemExit(f"Asset not found in release {tag}: {name}")
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
