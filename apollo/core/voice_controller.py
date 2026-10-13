"""
voice_controller.py
───────────────────
Modular, zero-dependency, 100% offline Windows Voice Controller for Apollo.
Uses Windows native System.Speech via a lightweight background worker process.

Design Invariants:
1. COMPLETELY OPT-IN: Default is OFF. Zero threads, zero microphones, zero CPU until enabled.
2. ZERO CORE POLLUTION: Deleting this file and removing the 3 optional call points in main.py
   completely eliminates voice support without affecting any other feature in Apollo.
3. ALEXA / APOLLO WAKE WINDOW: Listens strictly for "apollo" or "hey apollo".
   Once awakened, a 20-second listening window opens with an elegant visual wash.
   Accepts minimal commands: "pause", "resume", "stop", "login", "skip term", "skip store".
   Once executed or timed out, immediately returns to idle sleep.
"""

import os
import sys
import time
import logging
import threading
import subprocess

logger = logging.getLogger("Apollo.Voice")

PS_ENGINE_SCRIPT = r"""
Add-Type -AssemblyName System.Speech

try {
    $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    $engine.SetInputToDefaultAudioDevice()

    $choices = New-Object System.Speech.Recognition.Choices
    $choices.Add([string[]]@(
        "apollo", "hey apollo",
        "pause", "apollo pause", "hey apollo pause",
        "resume", "apollo resume", "hey apollo resume",
        "stop", "apollo stop", "hey apollo stop",
        "login", "apollo login", "hey apollo login",
        "skip term", "apollo skip term", "hey apollo skip term",
        "skip store", "apollo skip store", "hey apollo skip store"
    ))

    $gb = New-Object System.Speech.Recognition.GrammarBuilder
    $gb.Append($choices)

    $grammar = New-Object System.Speech.Recognition.Grammar($gb)
    $engine.LoadGrammar($grammar)

    [Console]::Out.WriteLine("SPEECH_READY")
    [Console]::Out.Flush()

    while ($true) {
        $result = $engine.Recognize()
        if ($result -ne $null) {
            $t = $result.Text.ToLower()
            $c = [math]::Round($result.Confidence, 2)
            [Console]::Out.WriteLine("RECOGNIZED|$c|$t")
            [Console]::Out.Flush()
        }
    }
} catch {
    [Console]::Error.WriteLine("ERROR: " + $_.Exception.Message)
    [Console]::Error.Flush()
}
"""


class VoiceController:
    """Non-invasive offline voice supervisor for Apollo."""

    def __init__(self, app):
        self.app = app
        self.enabled = False
        self.process = None
        self.thread = None
        self.stop_event = threading.Event()
        
        # State tracking
        self.awake = False
        self.wake_expires_at = 0.0
        self.wake_timer_id = None
        self._wash_canvas = None

    def start(self):
        """Start listening thread if on Windows and not already running."""
        if self.enabled and self.process is not None:
            return
        self.stop_event.clear()
        self.enabled = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True, name="ApolloVoiceWorker")
        self.thread.start()
        logger.info("VoiceController started (System.Speech engine).")

    def stop(self):
        """Stop listening and cleanly terminate background process."""
        self.enabled = False
        self.stop_event.set()
        self.awake = False
        self._hide_visual_wash()
        
        proc = self.process
        self.process = None
        if proc:
            try:
                proc.terminate()
                proc.kill()
            except Exception:
                pass
        logger.info("VoiceController stopped.")

    def _worker_loop(self):
        """Background loop managing PowerShell System.Speech process."""
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command", PS_ENGINE_SCRIPT
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                creationflags=creationflags
            )
        except Exception as e:
            logger.warning(f"VoiceController could not launch speech engine: {e}")
            self.enabled = False
            return

        # Poll stdout
        while not self.stop_event.is_set() and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith("RECOGNIZED|"):
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        confidence = float(parts[1])
                        phrase = parts[2].strip().lower()
                        self._handle_phrase(phrase, confidence)
            except Exception as e:
                logger.debug(f"Voice read error: {e}")
                break

    def _handle_phrase(self, phrase: str, confidence: float):
        """Handle incoming recognized speech in accordance with the wake window."""
        now = time.time()
        logger.debug(f"Voice received: '{phrase}' (conf: {confidence})")

        clean = phrase.strip().lower()

        # Handle compound one-shot wake + command (e.g. "apollo pause", "hey apollo stop")
        for prefix in ("hey apollo ", "apollo "):
            if clean.startswith(prefix):
                cmd_part = clean[len(prefix):].strip()
                if cmd_part:
                    # Awakened with direct command
                    self.awake = True
                    self.wake_expires_at = now + 20.0
                    self.app.after(0, self._on_wake_triggered)
                    clean = cmd_part
                    break

        # Pure Wake-word triggers
        if clean in ("apollo", "hey apollo"):
            self.wake_expires_at = now + 20.0
            self.awake = True
            # Schedule UI update on main thread
            self.app.after(0, self._on_wake_triggered)
            return

        # Command triggers (only processed if currently awake within the 20s window)
        if self.awake:
            if now > self.wake_expires_at:
                self.awake = False
                self.app.after(0, self._hide_visual_wash)
                return

            # Dispatch known commands
            dispatched = False
            if clean == "pause":
                self.app.after(0, self._cmd_pause)
                dispatched = True
            elif clean == "resume":
                self.app.after(0, self._cmd_resume)
                dispatched = True
            elif clean == "stop":
                self.app.after(0, self._cmd_stop)
                dispatched = True
            elif clean == "login":
                self.app.after(0, self._cmd_login)
                dispatched = True
            elif clean == "skip term":
                self.app.after(0, self._cmd_skip_term)
                dispatched = True
            elif clean == "skip store":
                self.app.after(0, self._cmd_skip_store)
                dispatched = True

            if dispatched:
                # Command accepted - close wake window
                self.awake = False
                self.app.after(0, self._hide_visual_wash)

    # ──────────────────────────────────────────────────────────────────────────
    #  DISPATCH TARGETS (Point 100% to existing Apollo methods)
    # ──────────────────────────────────────────────────────────────────────────
    def _cmd_pause(self):
        if getattr(self.app, "running", False):
            if not getattr(self.app, "paused", False):
                self.app._toggle_pause()
                self._log_voice("Voice: Paused scan.")
            else:
                self._log_voice("Voice: Scan is already paused.")
        else:
            self._log_voice("Voice: [Pause] No active scan is currently running.")

    def _cmd_resume(self):
        if getattr(self.app, "running", False):
            if getattr(self.app, "paused", False):
                self.app._toggle_pause()
                self._log_voice("Voice: Resumed scan.")
            else:
                self._log_voice("Voice: Scan is already actively running.")
        else:
            self._log_voice("Voice: [Resume] No paused scan is currently in queue.")

    def _cmd_stop(self):
        if getattr(self.app, "running", False):
            self.app._stop_scan()
            self._log_voice("Voice: Stopped scan.")
        else:
            self._log_voice("Voice: [Stop] No active scan is currently running.")

    def _cmd_login(self):
        mkt = self.app.marketplace_combo.get().strip().lower() if hasattr(self.app, "marketplace_combo") else ""
        if "mercado" in mkt and hasattr(self.app, "_launch_meli_login"):
            self.app._launch_meli_login()
            self._log_voice("Voice: Opening Mercado Libre authentication.")
        elif "vinted" in mkt and hasattr(self.app, "_launch_vinted_session"):
            self.app._launch_vinted_session()
            self._log_voice("Voice: Opening Vinted authentication.")
        elif "tiktok" in mkt and hasattr(self.app, "_launch_tiktok_session"):
            self.app._launch_tiktok_session()
            self._log_voice("Voice: Opening TikTok Shop authentication.")
        elif "printerval" in mkt and hasattr(self.app, "_launch_printerval_session"):
            self.app._launch_printerval_session()
            self._log_voice("Voice: Opening Printerval authentication.")
        elif "printblur" in mkt and hasattr(self.app, "_launch_printblur_session"):
            self.app._launch_printblur_session()
            self._log_voice("Voice: Opening Printblur authentication.")
        elif "threadless" in mkt and hasattr(self.app, "_launch_threadless_session"):
            self.app._launch_threadless_session()
            self._log_voice("Voice: Opening Threadless authentication.")
        else:
            self._log_voice(f"Voice: No login session required for {mkt or 'active marketplace'}.")

    def _cmd_skip_term(self):
        if hasattr(self.app, "_skip_current_term"):
            self.app._skip_current_term()
            self._log_voice("Voice: Skipped search term.")

    def _cmd_skip_store(self):
        if hasattr(self.app, "_skip_current_store"):
            self.app._skip_current_store()
            self._log_voice("Voice: Skipped store target.")

    def _log_voice(self, msg: str):
        if hasattr(self.app, "_log"):
            self.app._log(f"🎙️ {msg}")

    # ──────────────────────────────────────────────────────────────────────────
    #  VISUAL WASH & FEEDBACK
    # ──────────────────────────────────────────────────────────────────────────
    def _on_wake_triggered(self):
        """Called on main GUI thread when wake-word is confirmed."""
        self._log_voice("Apollo awakened. Listening for command (20s)...")
        self._show_visual_wash()
        
        # Schedule auto-dismiss countdown
        if self.wake_timer_id:
            try: self.app.after_cancel(self.wake_timer_id)
            except Exception: pass
        self.wake_timer_id = self.app.after(20000, self._on_wake_timeout)

    def _on_wake_timeout(self):
        if self.awake:
            self.awake = False
            self._log_voice("Listening window timed out. Standing by.")
            self._hide_visual_wash()

    def _show_visual_wash(self):
        """Subtle non-interrupting visual wash along accent bar or status label."""
        try:
            # Change status text temporarily
            if hasattr(self.app, "status_var"):
                self._old_status = self.app.status_var.get()
                self.app.status_var.set("🎙️ [Apollo Listening...] 'pause' 'resume' 'stop' 'login' 'skip term'")
            
            # Subtle accent glow pulse on top accent bar
            if hasattr(self.app, "accent_bar"):
                th = getattr(self.app, "theme", {})
                pulse_color = th.get("success", th.get("accent", "#00E5FF"))
                self.app.accent_bar.config(bg=pulse_color)
        except Exception:
            pass

    def _hide_visual_wash(self):
        """Restore default visual state."""
        try:
            if hasattr(self.app, "status_var") and getattr(self, "_old_status", None):
                curr = self.app.status_var.get()
                if "Apollo Listening" in curr:
                    self.app.status_var.set(self._old_status)
            if hasattr(self.app, "accent_bar"):
                th = getattr(self.app, "theme", {})
                self.app.accent_bar.config(bg=th.get("accent", "#FFD700"))
        except Exception:
            pass
