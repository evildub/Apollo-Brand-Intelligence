"""
apollo/ui/dialogs.py
────────────────────
Universal multi-monitor window centering and transparent ThemedMessageBoxProxy.
Eliminates unstyled stark-white native popups and ensures modals open on the active monitor.
"""

import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as _native_messagebox


def center_window_on_parent(win, parent=None, w=None, h=None):
    """
    Universal multi-monitor centering helper.
    Accurately positions any modal or popup centered directly over its parent window
    on whichever monitor the parent currently resides on.
    """
    try:
        win.update_idletasks()
    except Exception:
        pass

    width = w or win.winfo_reqwidth() or 600
    height = h or win.winfo_reqheight() or 400

    # Resolve true root/top-level parent if a frame or child widget was passed
    p = parent
    while p is not None and not isinstance(p, (tk.Tk, tk.Toplevel)):
        p = getattr(p, "master", None)

    if p is not None:
        try:
            p.update_idletasks()
            master_x = p.winfo_rootx()
            master_y = p.winfo_rooty()
            master_w = p.winfo_width()
            master_h = p.winfo_height()

            if master_w > 50 and master_h > 50:
                x = master_x + (master_w - width) // 2
                y = master_y + (master_h - height) // 2
                if y < master_y:
                    y = master_y + 10
            else:
                x = (win.winfo_screenwidth() - width) // 2
                y = max(30, (win.winfo_screenheight() - height) // 2)
        except Exception:
            x = (win.winfo_screenwidth() - width) // 2
            y = max(30, (win.winfo_screenheight() - height) // 2)
    else:
        x = (win.winfo_screenwidth() - width) // 2
        y = max(30, (win.winfo_screenheight() - height) // 2)

    win.geometry(f"{width}x{height}+{x}+{y}")
    if p is not None:
        try:
            win.transient(p)
        except Exception:
            pass
    try:
        win.deiconify()
        win.lift()
        win.focus_force()
        win.update_idletasks()
    except Exception:
        pass


class ThemedMessageBoxProxy:
    """
    Transparent proxy for tkinter.messagebox that intercepts showinfo, showwarning,
    showerror, askyesno, and askyesnocancel and routes them to Apollo's active
    themed modal dialogs. Prevents unstyled white Windows popups application-wide.
    """
    active_app_provider = None

    def __init__(self, original_module=None):
        self._orig = original_module or _native_messagebox

    def _get_app(self):
        if callable(self.active_app_provider):
            return self.active_app_provider()
        inst = getattr(ThemedMessageBoxProxy, "active_instance", None)
        if inst:
            return inst
        import sys
        main_mod = sys.modules.get("main") or sys.modules.get("apollo.app")
        if main_mod and hasattr(main_mod, "EbayTool"):
            return getattr(main_mod.EbayTool, "active_instance", None)
        return None

    def showinfo(self, title=None, message=None, **options):
        inst = self._get_app()
        parent = options.get("parent")
        if inst and hasattr(inst, "_show_themed_info"):
            inst._show_themed_info(title or "Information", message or "", icon="ℹ", parent=parent)
            return "ok"
        return self._orig.showinfo(title, message, **options)

    def showwarning(self, title=None, message=None, **options):
        inst = self._get_app()
        parent = options.get("parent")
        if inst and hasattr(inst, "_show_themed_warning"):
            inst._show_themed_warning(title or "Warning", message or "", icon="⚠", parent=parent)
            return "ok"
        return self._orig.showwarning(title, message, **options)

    def showerror(self, title=None, message=None, **options):
        inst = self._get_app()
        parent = options.get("parent")
        if inst and hasattr(inst, "_show_themed_error"):
            inst._show_themed_error(title or "Error", message or "", icon="❌", parent=parent)
            return "ok"
        return self._orig.showerror(title, message, **options)

    def askyesno(self, title=None, message=None, **options):
        inst = self._get_app()
        parent = options.get("parent")
        if inst and hasattr(inst, "_show_themed_confirm"):
            return bool(inst._show_themed_confirm(title or "Confirm", message or "", yes_text="Yes", no_text="No", parent=parent))
        return self._orig.askyesno(title, message, **options)

    def askyesnocancel(self, title=None, message=None, **options):
        inst = self._get_app()
        parent = options.get("parent")
        if inst and hasattr(inst, "_show_themed_askyesnocancel"):
            return inst._show_themed_askyesnocancel(title or "Confirm", message or "", parent=parent)
        return self._orig.askyesnocancel(title, message, **options)

    def __getattr__(self, name):
        return getattr(self._orig, name)


messagebox = ThemedMessageBoxProxy(_native_messagebox)
