#!/usr/bin/env python3
"""
Apollo Automated Release Engine
Packages the compiled distribution, tags the version, and publishes a release to GitHub.
"""

import os
import sys
import shutil
import zipfile
import subprocess
import argparse
import re
from datetime import datetime

# Ensure utf-8 encoding for console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
GH_PATH = r"C:\Program Files\GitHub CLI\gh.exe" if os.path.exists(r"C:\Program Files\GitHub CLI\gh.exe") else "gh"

def get_dist_dir():
    """Locate the compiled distribution directory."""
    candidates = [
        os.path.join(TOOL_DIR, "dist", "Apollo Brand Intelligence"),
        os.path.join(TOOL_DIR, "dist", "ApolloBrandIntelligence")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

def get_current_version():
    """Extract app version from main.py."""
    main_path = os.path.join(TOOL_DIR, "main.py")
    if os.path.exists(main_path):
        with open(main_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.search(r'(?:APP_)?VERSION\s*=\s*["\']([0-9\.]+)["\']', line)
                if m:
                    return m.group(1)
    return "3.0.0"

def zip_distribution(version_tag):
    """Create a zip archive of the compiled dist folder."""
    dist_dir = get_dist_dir()
    if not os.path.exists(dist_dir):
        print(f"❌ Distribution folder not found at: {dist_dir}")
        print("Please run build_exe.bat first to compile the binary.")
        sys.exit(1)

    zip_filename = f"ApolloBrandIntelligence-{version_tag}.zip"
    zip_path = os.path.join(TOOL_DIR, "dist", zip_filename)

    print(f"📦 Compressing distribution into: {zip_filename}...")
    total_files = sum(len(files) for _, _, files in os.walk(dist_dir))
    processed = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.dirname(dist_dir))
                zipf.write(file_path, arcname)
                processed += 1
                if processed % 50 == 0 or processed == total_files:
                    pct = int((processed / total_files) * 100)
                    print(f"  [{pct}%] Archived {processed}/{total_files} files...")

    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"✅ Successfully created {zip_filename} ({zip_size_mb:.1f} MB)")
    return [zip_path]

def git_commit_and_push(version_tag, message=""):
    """Commit tracked changes and push to GitHub origin."""
    print("🔄 Syncing source code to GitHub...")
    try:
        subprocess.run(["git", "add", "."], cwd=TOOL_DIR, check=True)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=TOOL_DIR, capture_output=True, text=True)
        if status.stdout.strip():
            msg = message if message else f"Release {version_tag} — Multi-Platform Vinted & Mercado Libre Suite"
            subprocess.run(["git", "commit", "-m", msg], cwd=TOOL_DIR, check=True)
            print(f"  ✓ Committed source changes: {msg}")
        else:
            print("  ✓ No uncommitted source changes.")

        # Push main branch
        subprocess.run(["git", "push", "-u", "origin", "main"], cwd=TOOL_DIR, check=True)
        print("  ✓ Pushed source to GitHub origin/main.")
    except Exception as e:
        print(f"⚠ Git sync notice: {e}")

def publish_github_release(version_tag, zip_paths, title="", notes=""):
    """Publish a release to GitHub with the attached zip files."""
    print(f"🚀 Publishing GitHub Release {version_tag}...")
    rel_title = title if title else f"Apollo Brand Intelligence {version_tag} — Multi-Platform Vinted & Mercado Libre Enterprise Suite"
    
    notes_file = os.path.join(TOOL_DIR, "release_notes.md")
    if not notes and os.path.exists(notes_file):
        with open(notes_file, "r", encoding="utf-8", errors="ignore") as f:
            notes = f.read()

    rel_notes = notes if notes else f"Automated build and release for {version_tag} published on {datetime.now().strftime('%Y-%m-%d %H:%M')}."

    cmd = [
        GH_PATH, "release", "create", version_tag,
        *zip_paths,
        "--title", rel_title,
        "--notes", rel_notes
    ]

    try:
        res = subprocess.run(cmd, cwd=TOOL_DIR, capture_output=True, text=True, check=True)
        print("🎉 Release Published Successfully!")
        print(res.stdout.strip())
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr.lower():
            print(f"ℹ Release {version_tag} already exists. Uploading zip assets...")
            for zp in zip_paths:
                up_cmd = [GH_PATH, "release", "upload", version_tag, zp, "--clobber"]
                subprocess.run(up_cmd, cwd=TOOL_DIR, check=True)
            print(f"✅ Successfully updated assets on release {version_tag}!")
        else:
            print(f"❌ GitHub release error: {e.stderr}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Apollo Release Automation")
    parser.add_argument("--version", "-v", help="Version tag (e.g. v1.5.0)")
    parser.add_argument("--title", "-t", help="Release title")
    parser.add_argument("--notes", "-n", help="Release notes string or path to markdown file")
    parser.add_argument("--skip-git", action="store_true", help="Skip git commit and push")
    args = parser.parse_args()

    ver_val = args.version or get_current_version()
    tag = ver_val if ver_val.startswith("v") else f"v{ver_val}"

    notes_content = args.notes or ""
    if notes_content and os.path.exists(notes_content):
        with open(notes_content, "r", encoding="utf-8", errors="ignore") as f:
            notes_content = f.read()

    print("==================================================")
    print(f"☀ APOLLO AUTOMATED RELEASE ENGINE — {tag}")
    print("==================================================")

    if not args.skip_git:
        git_commit_and_push(tag, message=args.title)

    zip_paths = zip_distribution(tag)
    publish_github_release(tag, zip_paths, title=args.title, notes=notes_content)

    print(f"\n🏆 All steps complete! Download your release on your work PC from:")
    print(f"   https://github.com/evildub/Apollo-Brand-Intelligence/releases/tag/{tag}\n")

if __name__ == "__main__":
    main()
