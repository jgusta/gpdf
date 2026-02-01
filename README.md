# gpdf

gpdf is a command line program that steps through pdf files and searches for the indicated text. It's like grep but for pdfs.

Features

- Uses simple pcre regex for matching text
- Prints out filename, location in file (approximate % of document if page numbers cant be determined) and a front and back context window
- Outputs to stdout by default
- Can also create a simple html index for the results with Title, page number, context filename and a link to file.
- can also collect pages with a match of the text into a separate pdf with a clickable TOC that lists the findings and also has a link to the original file by each page.

## Install

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Build standalone (macOS/Linux)

```
./build.sh
```

The CLI executable will be at `dist/gpdf`. On macOS, the GUI app bundle will be at `dist/gpdf_app.app`.
Build on each OS you want a native binary for.

## Build standalone (Windows)

```
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

This produces `dist\\gpdf.exe` and `dist\\gpdf_app.exe`.

## Homebrew (local formula)

Update `Formula/gpdf.rb` with the tag version and SHA256 for your release assets, then:

```
brew install --build-from-source Formula/gpdf.rb
```

## Desktop app (report mode)

```
python3 gpdf_app.py
```

This opens a simple GUI that runs `gpdf` in report mode for a chosen directory.
On macOS, the app uses native dialogs via AppleScript (no Tkinter required).
On Linux, `python3` must include Tkinter support.

## Usage

```
./gpdf.py -h -m "pattern" *.pdf
./gpdf.py "pattern" *.pdf --html-path results.html --merge-path results.pdf
./gpdf.py -h -m "pattern" --output-dir out --copy-pdfs
./gpdf.py --report --name "My Search" "pattern" *.pdf
```

Notes:
- Matching is case-insensitive.
- If no paths are provided, gpdf scans PDFs in the current directory.
- For glob patterns, rely on your shell to expand them.
- When HTML or merged outputs are requested, results go to `_gpdf_results` by default (override with `--output-dir`).
- `--report` creates a `gpdf_report/` bundle with `html/`, `source/`, and `summaries/`.
