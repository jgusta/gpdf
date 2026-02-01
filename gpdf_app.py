#!/usr/bin/env python3
import os
import platform
import re
import subprocess
import sys


def _run_report(pattern: str, target_dir: str, name: str) -> int:
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "gpdf.py"),
        "--report",
        "--name",
        name,
        pattern,
        target_dir,
    ]
    return subprocess.call(cmd, cwd=target_dir)


def _osascript(script: str) -> str:
    return subprocess.check_output(["osascript", "-e", script], text=True).strip()


def _mac_dialog(label: str, default: str = "") -> str:
    script = (
        'display dialog "' + label.replace('"', '\\"') + '" '
        'default answer "' + default.replace('"', '\\"') + '" '
        'buttons {"Cancel","OK"} default button "OK"'
    )
    output = _osascript(script)
    match = re.search(r"text returned:(.*)$", output)
    return match.group(1) if match else ""


def _mac_choose_dir() -> str:
    script = 'POSIX path of (choose folder with prompt "Select target directory")'
    return _osascript(script)


def _run_mac_app() -> None:
    try:
        pattern = _mac_dialog("Search pattern")
        if not pattern:
            return
        name = _mac_dialog("Report title (optional)")
        target_dir = _mac_choose_dir()
        if not target_dir:
            return
    except subprocess.CalledProcessError:
        return

    code = _run_report(pattern, target_dir, name or "gpdf report")
    if code == 0:
        _osascript('display dialog "Report saved to gpdf_report/" buttons {"OK"}')
    else:
        _osascript('display dialog "Failed. See terminal output for details." buttons {"OK"}')


def _run_tk_app() -> None:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except Exception:
        print("ERROR: Tkinter is required for the desktop app.", file=sys.stderr)
        return

    root = tk.Tk()
    root.title("gpdf report")
    root.geometry("520x260")
    root.resizable(False, False)

    tk.Label(root, text="Search pattern").pack(anchor="w", padx=16, pady=(16, 4))
    pattern_entry = tk.Entry(root, width=64)
    pattern_entry.pack(padx=16, fill="x")

    tk.Label(root, text="Target directory").pack(anchor="w", padx=16, pady=(12, 4))
    dir_frame = tk.Frame(root)
    dir_frame.pack(padx=16, fill="x")
    dir_entry = tk.Entry(dir_frame, width=52)
    dir_entry.pack(side="left", fill="x", expand=True)

    def browse_dir() -> None:
        choice = filedialog.askdirectory()
        if choice:
            dir_entry.delete(0, tk.END)
            dir_entry.insert(0, choice)

    tk.Button(dir_frame, text="Browse", command=browse_dir).pack(side="left", padx=8)

    tk.Label(root, text="Report title (optional)").pack(anchor="w", padx=16, pady=(12, 4))
    name_entry = tk.Entry(root, width=64)
    name_entry.pack(padx=16, fill="x")

    status_var = tk.StringVar(value="")
    status_label = tk.Label(root, textvariable=status_var, fg="#444")
    status_label.pack(anchor="w", padx=16, pady=(10, 0))

    def run() -> None:
        pattern = pattern_entry.get().strip()
        target_dir = dir_entry.get().strip()
        name = name_entry.get().strip() or "gpdf report"

        if not pattern:
            messagebox.showerror("Missing pattern", "Please enter a search pattern.")
            return
        if not target_dir or not os.path.isdir(target_dir):
            messagebox.showerror("Invalid directory", "Please choose a valid directory.")
            return

        status_var.set("Running... this can take a while.")
        root.update_idletasks()
        code = _run_report(pattern, target_dir, name)
        if code == 0:
            status_var.set("Done. Report saved to gpdf_report/")
        else:
            status_var.set("Failed. See terminal output for details.")

    tk.Button(root, text="Run report", command=run).pack(pady=16)

    root.mainloop()


def main() -> None:
    if platform.system() == "Darwin":
        _run_mac_app()
        return
    _run_tk_app()


if __name__ == "__main__":
    main()
