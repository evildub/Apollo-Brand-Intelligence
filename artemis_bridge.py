"""
Artemis Bridge — Decoupled IPC & Intake Protocol between Apollo & Artemis.
Handles serializing verified reconnaissance batches from Apollo and staging them
into the Artemis Rights Engine intake drop-queue.
"""

import json
import os
import sys
import time
import uuid
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional

def get_artemis_base_dir() -> str:
    """Return persistent user directory for Artemis Rights Engine."""
    appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    user_dir = os.path.join(appdata, "Artemis_Rights_Engine")
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def get_intake_dir() -> str:
    """Return the shared intake drop folder for incoming enforcement batches."""
    appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or os.path.expanduser("~")
    intake_dir = os.path.join(appdata, "Artemis_Rights_Engine", "intake_queue")
    os.makedirs(intake_dir, exist_ok=True)
    return intake_dir

def get_processed_dir() -> str:
    """Return archive directory for processed intake batches."""
    p_dir = os.path.join(get_intake_dir(), "processed")
    os.makedirs(p_dir, exist_ok=True)
    return p_dir

def dispatch_batch_to_artemis(listings: List[Dict[str, Any]], source_batch_name: str = "Apollo Recon Batch") -> str:
    """Format and dispatch a list of high-conviction listings to Artemis intake queue.
    Returns the absolute path to the generated batch file."""
    if not listings:
        raise ValueError("Cannot dispatch an empty listing batch to Artemis.")

    batch_id = f"artemis_batch_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    batch_payload = {
        "batch_id": batch_id,
        "source": "Apollo Brand Intelligence",
        "batch_name": source_batch_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_items": len(listings),
        "listings": listings
    }

    intake_path = os.path.join(get_intake_dir(), f"{batch_id}.json")
    os.makedirs(os.path.dirname(intake_path), exist_ok=True)
    tmp_path = intake_path + ".tmp"

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(batch_payload, f, indent=2, ensure_ascii=False)

    os.replace(tmp_path, intake_path)
    return intake_path

def get_pending_artemis_batches() -> List[Dict[str, Any]]:
    """Scan the intake directory and return all pending intake batches."""
    intake_dir = get_intake_dir()
    batches = []
    if not os.path.exists(intake_dir):
        return batches

    for fname in sorted(os.listdir(intake_dir)):
        if fname.endswith(".json") and fname.startswith("artemis_batch_"):
            fpath = os.path.join(intake_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["_filepath"] = fpath
                    batches.append(data)
            except Exception:
                continue

    return batches

def mark_batch_as_ingested(batch_filepath: str):
    """Move processed intake batch JSON to the processed archive folder."""
    if not os.path.exists(batch_filepath):
        return
    processed_dir = get_processed_dir()
    dest = os.path.join(processed_dir, os.path.basename(batch_filepath))
    try:
        os.replace(batch_filepath, dest)
    except Exception:
        pass

def _get_detached_popen_kwargs(cwd: str) -> dict:
    """Return platform-specific kwargs to launch a completely detached GUI process."""
    kwargs = {
        "cwd": cwd,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        # DETACHED_PROCESS (0x8) | CREATE_NEW_PROCESS_GROUP (0x200)
        kwargs["creationflags"] = 0x00000008 | 0x00000200
    return kwargs

def launch_artemis_process(theme_key: Optional[str] = None) -> bool:
    """Launch Artemis Rights Engine GUI as a detached, independent process."""
    cmd_args = []
    if theme_key:
        cmd_args = ["--theme", str(theme_key)]

    # 1. If running as a frozen executable (PyInstaller bundle)
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        exe_path = os.path.join(base_dir, "Artemis.exe")
        kwargs = _get_detached_popen_kwargs(base_dir)
        if os.path.exists(exe_path):
            try:
                subprocess.Popen([exe_path] + cmd_args, **kwargs)
                return True
            except Exception:
                pass
        # Launch using self with --artemis flag
        try:
            subprocess.Popen([sys.executable, "--artemis"] + cmd_args, **kwargs)
            return True
        except Exception:
            pass

    # 2. Look for standalone artemis.py in project directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    py_path = os.path.join(base_dir, "artemis.py")
    kwargs = _get_detached_popen_kwargs(base_dir)
    if os.path.exists(py_path):
        try:
            python_exe = sys.executable
            subprocess.Popen([python_exe, py_path] + cmd_args, **kwargs)
            return True
        except Exception:
            pass

    # 3. Fallback: try python main.py --artemis
    main_path = os.path.join(base_dir, "main.py")
    if os.path.exists(main_path):
        try:
            python_exe = sys.executable
            subprocess.Popen([python_exe, main_path, "--artemis"] + cmd_args, **kwargs)
            return True
        except Exception:
            pass

    return False
