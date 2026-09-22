"""
Apollo Brand Intelligence - Cross-Marketplace Syndicate Hunter & Entity Resolution Modal
Interactive forensic investigation hub for discovering, visualizing, and exporting
multi-seller counterfeit rings and ghost storefronts connected by visual pHash collisions,
3PL dispatch hubs, and lexical name patterns.
"""

import os
import io
import math
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Any, Optional
from PIL import Image, ImageTk

from syndicate_graph import SyndicateGraph, SyndicateCluster, LinkEdge

FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_HEADING = ("Segoe UI", 10, "bold")
FONT_NORM = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 9, "bold")
FONT_CODE = ("Consolas", 9)
FONT_SM = ("Segoe UI", 8)


class SyndicateHunterModal(tk.Toplevel):
    """
    Dedicated Executive Modal for Cross-Marketplace Syndicate & Entity Resolution.
    Clusters seller accounts across visual image hashes, 3PL hubs, and handle patterns.
    """
    def __init__(self, master, theme: dict, listings: List[Dict[str, Any]], target_seller: Optional[str] = None):
        super().__init__(master)
        self.theme = theme or {}
        self.master = master
        self.listings = listings or []
        self.target_seller = target_seller

        self.title("🕸️ Apollo Syndicate Hunter — Cross-Marketplace Entity Resolution")

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1380, max(1120, int(screen_w * 0.92)))
        win_h = min(880, max(700, int(screen_h * 0.88)))
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(1040, 640)
        self.configure(bg=self._t("bg", "#000227"))
        self.transient(master)

        if hasattr(master, "_apply_dark_titlebar"):
            master._apply_dark_titlebar(self)
        if hasattr(master, "_load_app_icon"):
            master._load_app_icon(self)

        # Initialize Syndicate Engine
        self.graph_engine = SyndicateGraph(phash_threshold=6)
        self.clusters: List[SyndicateCluster] = []
        self.active_cluster: Optional[SyndicateCluster] = None
        self._thumb_cache: Dict[str, Any] = {}

        self._build_header_and_metrics()
        self._build_body()
        self._build_footer()

        # Run resolution on background or immediate
        self._run_analysis()

    def _t(self, key: str, default: str) -> str:
        return self.theme.get(key, default)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Header & Metric Summary Cards
    # ─────────────────────────────────────────────────────────────────────────
    def _build_header_and_metrics(self):
        top_container = tk.Frame(self, bg=self._t("panel", "#0A0E36"), padx=16, pady=10, highlightbackground=self._t("border", "#1E295D"), highlightthickness=1)
        top_container.pack(side="top", fill="x", padx=12, pady=(10, 6))

        # Title Row
        t_row = tk.Frame(top_container, bg=self._t("panel", "#0A0E36"))
        t_row.pack(side="top", fill="x", pady=(0, 8))

        tk.Label(t_row, text="🕸️ Cross-Marketplace Syndicate Hunter & Entity Resolution", font=FONT_TITLE, bg=self._t("panel", "#0A0E36"), fg=self._t("text", "#FFFFFF")).pack(side="left")
        
        tag_lbl = tk.Label(t_row, text="GENESIS-COMPLIANT MULTI-VECTOR CORRELATION", font=("Segoe UI", 8, "bold"), bg=self._t("accent", "#38BDF8"), fg="#000227", padx=8, pady=2)
        tag_lbl.pack(side="left", padx=12)

        # Metric Cards Frame
        cards_frame = tk.Frame(top_container, bg=self._t("panel", "#0A0E36"))
        cards_frame.pack(side="top", fill="x")

        self.card_syndicates = self._create_metric_card(cards_frame, "0", "DETECTED SYNDICATES", self._t("danger", "#EF4444"))
        self.card_sellers = self._create_metric_card(cards_frame, "0", "LINKED GHOST ACCOUNTS", self._t("warning", "#F59E0B"))
        self.card_photos = self._create_metric_card(cards_frame, "0", "PHOTO RE-USE COLLISIONS", self._t("accent", "#38BDF8"))
        self.card_hubs = self._create_metric_card(cards_frame, "0", "3PL LOGISTICS HUBS", self._t("success", "#10B981"))
        self.card_items = self._create_metric_card(cards_frame, str(len(self.listings)), "ANALYZED LISTINGS", self._t("subtext", "#7C8FA3"))

    def _create_metric_card(self, parent, val: str, label: str, color: str):
        card = tk.Frame(parent, bg=self._t("entry_bg", "#05071F"), padx=14, pady=8, highlightbackground=self._t("border", "#1E295D"), highlightthickness=1)
        card.pack(side="left", fill="both", expand=True, padx=4)

        v_lbl = tk.Label(card, text=val, font=("Segoe UI", 16, "bold"), bg=self._t("entry_bg", "#05071F"), fg=color)
        v_lbl.pack(anchor="w")

        l_lbl = tk.Label(card, text=label, font=("Segoe UI", 8, "bold"), bg=self._t("entry_bg", "#05071F"), fg=self._t("subtext", "#7C8FA3"))
        l_lbl.pack(anchor="w")
        return v_lbl

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Main Workspace Body (Dual-Pane)
    # ─────────────────────────────────────────────────────────────────────────
    def _build_body(self):
        body_paned = ttk.PanedWindow(self, orient="horizontal")
        body_paned.pack(side="top", fill="both", expand=True, padx=12, pady=4)

        # ── Left Master Pane (Syndicates List) ───────────────────────────────
        left_frame = tk.Frame(body_paned, bg=self._t("panel", "#0A0E36"), highlightbackground=self._t("border", "#1E295D"), highlightthickness=1)
        body_paned.add(left_frame, weight=3)

        l_hdr = tk.Frame(left_frame, bg=self._t("panel", "#0A0E36"), padx=8, pady=6)
        l_hdr.pack(side="top", fill="x")

        tk.Label(l_hdr, text="Threat Clusters & Rings", font=FONT_HEADING, bg=self._t("panel", "#0A0E36"), fg=self._t("text", "#FFFFFF")).pack(side="left")

        # Filter combo
        self.filter_var = tk.StringVar(value="All Clusters")
        f_combo = ttk.Combobox(l_hdr, textvariable=self.filter_var, values=["All Clusters", "Confirmed (Score 90+)", "Visual Collisions", "3PL Hubs Only"], state="readonly", width=18, font=FONT_SM)
        f_combo.pack(side="right")
        f_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_cluster_list())

        # Clusters Treeview
        tree_frame = tk.Frame(left_frame, bg=self._t("entry_bg", "#05071F"))
        tree_frame.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))

        cols = ("id", "score", "tier", "sellers", "items")
        self.cluster_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        self.cluster_tree.heading("id", text="Ring ID", anchor="w")
        self.cluster_tree.heading("score", text="Threat", anchor="center")
        self.cluster_tree.heading("tier", text="Confidence", anchor="w")
        self.cluster_tree.heading("sellers", text="Accounts", anchor="center")
        self.cluster_tree.heading("items", text="Items", anchor="center")

        self.cluster_tree.column("id", width=70, stretch=False)
        self.cluster_tree.column("score", width=55, stretch=False, anchor="center")
        self.cluster_tree.column("tier", width=140, stretch=True)
        self.cluster_tree.column("sellers", width=65, stretch=False, anchor="center")
        self.cluster_tree.column("items", width=55, stretch=False, anchor="center")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.cluster_tree.yview)
        self.cluster_tree.configure(yscrollcommand=sb.set)
        self.cluster_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.cluster_tree.bind("<<TreeviewSelect>>", self._on_cluster_selected)

        # ── Right Detail Inspector ───────────────────────────────────────────
        right_frame = tk.Frame(body_paned, bg=self._t("panel", "#0A0E36"), highlightbackground=self._t("border", "#1E295D"), highlightthickness=1)
        body_paned.add(right_frame, weight=5)

        self.nb = ttk.Notebook(right_frame)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)

        self.tab_evidence = tk.Frame(self.nb, bg=self._t("panel", "#0A0E36"))
        self.tab_sellers = tk.Frame(self.nb, bg=self._t("panel", "#0A0E36"))
        self.tab_items = tk.Frame(self.nb, bg=self._t("panel", "#0A0E36"))
        self.tab_graph = tk.Frame(self.nb, bg=self._t("panel", "#0A0E36"))

        self.nb.add(self.tab_evidence, text=" 🔬 Forensic Evidence Chain ")
        self.nb.add(self.tab_sellers, text=" 👥 Member Storefronts ")
        self.nb.add(self.tab_items, text=" 📦 Linked Inventory Catalog ")
        self.nb.add(self.tab_graph, text=" 🕸️ Interactive Visual Graph ")

        self._build_evidence_tab()
        self._build_sellers_tab()
        self._build_items_tab()
        self._build_graph_tab()

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Tab Implementations
    # ─────────────────────────────────────────────────────────────────────────
    def _build_evidence_tab(self):
        self.ev_scroll = tk.Frame(self.tab_evidence, bg=self._t("panel", "#0A0E36"), padx=12, pady=10)
        self.ev_scroll.pack(fill="both", expand=True)

        self.ev_title_lbl = tk.Label(self.ev_scroll, text="Select a Syndicate Cluster on the left to inspect evidence.", font=FONT_HEADING, bg=self._t("panel", "#0A0E36"), fg=self._t("text", "#FFFFFF"))
        self.ev_title_lbl.pack(anchor="w", pady=(0, 8))

        self.ev_box = tk.Text(self.ev_scroll, bg=self._t("entry_bg", "#05071F"), fg=self._t("text", "#FFFFFF"), font=FONT_NORM, wrap="word", relief="flat", highlightbackground=self._t("border", "#1E295D"), highlightthickness=1, height=12)
        self.ev_box.pack(fill="both", expand=True, pady=(0, 8))

        # Direct links / notes
        self.ev_note_lbl = tk.Label(self.ev_scroll, text="Multi-vector evidence links accounts across image perceptual hashes, physical fulfillment zip codes, and handle syntax.", font=FONT_SM, bg=self._t("panel", "#0A0E36"), fg=self._t("subtext", "#7C8FA3"))
        self.ev_note_lbl.pack(anchor="w")

    def _build_sellers_tab(self):
        sf = tk.Frame(self.tab_sellers, bg=self._t("panel", "#0A0E36"), padx=8, pady=8)
        sf.pack(fill="both", expand=True)

        cols = ("handle", "marketplace", "origin", "hub", "is_3pl", "items")
        self.sellers_tree = ttk.Treeview(sf, columns=cols, show="headings", selectmode="browse")
        self.sellers_tree.heading("handle", text="Seller Handle", anchor="w")
        self.sellers_tree.heading("marketplace", text="Platform", anchor="center")
        self.sellers_tree.heading("origin", text="Origin", anchor="w")
        self.sellers_tree.heading("hub", text="Dispatch Hub", anchor="w")
        self.sellers_tree.heading("is_3pl", text="3PL Flag", anchor="center")
        self.sellers_tree.heading("items", text="SKUs", anchor="center")

        self.sellers_tree.column("handle", width=140)
        self.sellers_tree.column("marketplace", width=80, anchor="center")
        self.sellers_tree.column("origin", width=100)
        self.sellers_tree.column("hub", width=160)
        self.sellers_tree.column("is_3pl", width=75, anchor="center")
        self.sellers_tree.column("items", width=55, anchor="center")

        sb = ttk.Scrollbar(sf, orient="vertical", command=self.sellers_tree.yview)
        self.sellers_tree.configure(yscrollcommand=sb.set)
        self.sellers_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def _build_items_tab(self):
        itf = tk.Frame(self.tab_items, bg=self._t("panel", "#0A0E36"), padx=8, pady=8)
        itf.pack(fill="both", expand=True)

        cols = ("seller", "price", "item_id", "title")
        self.items_tree = ttk.Treeview(itf, columns=cols, show="headings", selectmode="extended")
        self.items_tree.heading("seller", text="Seller", anchor="w")
        self.items_tree.heading("price", text="Price", anchor="center")
        self.items_tree.heading("item_id", text="Item ID", anchor="center")
        self.items_tree.heading("title", text="Title", anchor="w")

        self.items_tree.column("seller", width=120)
        self.items_tree.column("price", width=75, anchor="center")
        self.items_tree.column("item_id", width=110, anchor="center")
        self.items_tree.column("title", width=360)

        sb = ttk.Scrollbar(itf, orient="vertical", command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=sb.set)
        self.items_tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.items_tree.bind("<Double-1>", self._on_item_double_click)

    def _build_graph_tab(self):
        gf = tk.Frame(self.tab_graph, bg=self._t("entry_bg", "#05071F"))
        gf.pack(fill="both", expand=True)

        self.graph_canvas = tk.Canvas(gf, bg=self._t("entry_bg", "#05071F"), highlightthickness=0)
        self.graph_canvas.pack(fill="both", expand=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Action Footer Toolbar
    # ─────────────────────────────────────────────────────────────────────────
    def _build_footer(self):
        footer = tk.Frame(self, bg=self._t("panel", "#0A0E36"), padx=14, pady=10, highlightbackground=self._t("border", "#1E295D"), highlightthickness=1)
        footer.pack(side="bottom", fill="x", padx=12, pady=(4, 10))

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(footer, textvariable=self.status_var, font=FONT_NORM, bg=self._t("panel", "#0A0E36"), fg=self._t("subtext", "#7C8FA3")).pack(side="left")

        # Action Buttons
        tk.Button(footer, text="✕ Close", command=self.destroy, bg=self._t("entry_bg", "#05071F"), fg=self._t("text", "#FFFFFF"), relief="flat", padx=10, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(footer, text="📋 Copy All Handles", command=self._copy_handles, bg=self._t("entry_bg", "#05071F"), fg=self._t("text", "#FFFFFF"), relief="flat", padx=10, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(footer, text="➕ Queue Sellers", command=self._queue_sellers, bg=self._t("entry_bg", "#05071F"), fg=self._t("text", "#FFFFFF"), relief="flat", padx=10, pady=4, font=FONT_SM).pack(side="right", padx=3)
        tk.Button(footer, text="🎯 Select in Main Table", command=self._select_in_main_table, bg=self._t("accent2", "#347BB7"), fg="#FFFFFF", relief="flat", padx=12, pady=4, font=FONT_BOLD).pack(side="right", padx=4)
        tk.Button(footer, text="📊 Export Genesis Dossier", command=self._export_genesis_dossier, bg=self._t("accent", "#38BDF8"), fg="#000227", relief="flat", padx=14, pady=4, font=FONT_BOLD).pack(side="right", padx=4)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Execution & Data Populating
    # ─────────────────────────────────────────────────────────────────────────
    def _run_analysis(self):
        self.status_var.set("Running entity resolution across image pHash, 3PL hubs, and handles...")
        self.update_idletasks()

        self.clusters = self.graph_engine.analyze_listings(self.listings)

        # Update metric cards
        total_clusters = len(self.clusters)
        total_linked_sellers = sum(len(c.sellers) for c in self.clusters)
        total_visual_collisions = sum(sum(1 for e in c.edges if e.link_type == "VISUAL_HASH") for c in self.clusters)
        total_hubs = len(set(h for c in self.clusters for h in c.shared_hubs))

        self.card_syndicates.config(text=str(total_clusters))
        self.card_sellers.config(text=str(total_linked_sellers))
        self.card_photos.config(text=str(total_visual_collisions))
        self.card_hubs.config(text=str(total_hubs))

        self._refresh_cluster_list()

        # If target seller was passed, auto-select their cluster
        if self.target_seller:
            target_cluster = self.graph_engine.find_syndicate_for_seller(self.target_seller)
            if target_cluster:
                for item_id in self.cluster_tree.get_children():
                    val = self.cluster_tree.item(item_id, "values")
                    if val and val[0] == target_cluster.cluster_id:
                        self.cluster_tree.selection_set(item_id)
                        self.cluster_tree.focus(item_id)
                        break

        self.status_var.set(f"Entity Resolution Complete: Discovered {total_clusters} multi-seller syndicates.")

    def _refresh_cluster_list(self):
        for item in self.cluster_tree.get_children():
            self.cluster_tree.delete(item)

        filter_mode = self.filter_var.get()

        for c in self.clusters:
            if filter_mode == "Confirmed (Score 90+)" and c.threat_score < 90:
                continue
            if filter_mode == "Visual Collisions" and not any(e.link_type == "VISUAL_HASH" for e in c.edges):
                continue
            if filter_mode == "3PL Hubs Only" and not c.known_3pl_hubs:
                continue

            self.cluster_tree.insert("", "end", values=(
                c.cluster_id,
                f"{c.threat_score}/100",
                c.confidence_tier,
                len(c.sellers),
                len(c.items)
            ))

        # Select first if available
        children = self.cluster_tree.get_children()
        if children:
            self.cluster_tree.selection_set(children[0])
            self.cluster_tree.focus(children[0])
            self._on_cluster_selected(None)

    def _on_cluster_selected(self, event):
        sel = self.cluster_tree.selection()
        if not sel:
            return
        vals = self.cluster_tree.item(sel[0], "values")
        if not vals:
            return
        cluster_id = vals[0]

        cluster = next((c for c in self.clusters if c.cluster_id == cluster_id), None)
        if not cluster:
            return

        self.active_cluster = cluster

        # ── Populate Tab 1: Evidence ─────────────────────────────────────────
        self.ev_title_lbl.config(text=f"Syndicate {cluster.cluster_id} — Threat Score: {cluster.threat_score}/100 ({cluster.confidence_tier})")
        self.ev_box.delete("1.0", "end")

        ev_text = f"SYNDICATE THREAT REPORT: {cluster.cluster_id}\n"
        ev_text += f"{'='*60}\n"
        ev_text += f"• Confidence Level: {cluster.confidence_tier}\n"
        ev_text += f"• Threat Score: {cluster.threat_score}/100\n"
        ev_text += f"• Linked Storefronts ({len(cluster.sellers)}): {', '.join(sorted(cluster.sellers))}\n"
        ev_text += f"• Total Active Inventory: {len(cluster.items)} items\n"
        if cluster.shared_hubs:
            ev_text += f"• Primary Dispatch Hubs: {', '.join(cluster.shared_hubs)}\n"
        if cluster.known_3pl_hubs:
            ev_text += f"• Identified High-Risk 3PL Hubs: {', '.join(cluster.known_3pl_hubs)}\n"
        ev_text += f"\nCORROBORATING FORENSIC EVIDENCE:\n"
        ev_text += f"{'-'*60}\n"
        for idx, ev in enumerate(cluster.evidence_summary, 1):
            ev_text += f"  {idx}. {ev}\n"

        ev_text += f"\nINTER-ENTITY RELATIONSHIP EDGES:\n"
        ev_text += f"{'-'*60}\n"
        for edge in cluster.edges:
            ev_text += f"  • [{edge.link_type}] {edge.source_seller} ↔ {edge.target_seller}\n"
            ev_text += f"    Evidence: {edge.evidence}\n"

        self.ev_box.insert("1.0", ev_text)

        # ── Populate Tab 2: Member Storefronts ───────────────────────────────
        for item in self.sellers_tree.get_children():
            self.sellers_tree.delete(item)

        for s in sorted(cluster.sellers):
            meta = cluster.seller_details.get(s, {})
            item_count = sum(1 for i in cluster.items if i.get("seller") == s)
            self.sellers_tree.insert("", "end", values=(
                s,
                meta.get("marketplace", "eBay"),
                meta.get("origin", "N/A"),
                meta.get("normalized_hub", ""),
                "YES" if meta.get("is_3pl") else "NO",
                item_count
            ))

        # ── Populate Tab 3: Items ────────────────────────────────────────────
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)

        for itm in cluster.items:
            self.items_tree.insert("", "end", values=(
                itm.get("seller", ""),
                itm.get("price", ""),
                itm.get("item_id", ""),
                itm.get("title", "")
            ))

        # ── Populate Tab 4: Interactive Graph ────────────────────────────────
        self._render_graph_canvas(cluster)

    def _render_graph_canvas(self, cluster: SyndicateCluster):
        """Draw an interactive topological network graph of the syndicate ring on the Tkinter canvas."""
        c = self.graph_canvas
        c.delete("all")

        w = c.winfo_width() or 600
        h = c.winfo_height() or 400
        cx, cy = w // 2, h // 2

        # Draw Central Syndicate Hub Node
        c_r = 38
        c.create_oval(cx - c_r, cy - c_r, cx + c_r, cy + c_r, fill=self._t("danger", "#EF4444"), outline=self._t("text", "#FFFFFF"), width=2)
        c.create_text(cx, cy - 8, text=cluster.cluster_id, fill="#FFFFFF", font=("Segoe UI", 9, "bold"))
        c.create_text(cx, cy + 8, text=f"{cluster.threat_score}/100", fill="#FFFFFF", font=("Segoe UI", 8))

        sellers = sorted(list(cluster.sellers))
        n_sellers = len(sellers)
        if n_sellers == 0:
            return

        # Position seller nodes in an orbit around center
        orbit_r = min(w, h) * 0.36
        seller_pos = {}

        for i, s in enumerate(sellers):
            angle = (2 * math.pi * i) / n_sellers
            sx = cx + orbit_r * math.cos(angle)
            sy = cy + orbit_r * math.sin(angle)
            seller_pos[s] = (sx, sy)

            # Draw edge to center
            c.create_line(cx, cy, sx, sy, fill=self._t("border", "#1E295D"), width=2, dash=(4, 2))

        # Draw inter-seller evidentiary edges
        for edge in cluster.edges:
            p1 = seller_pos.get(edge.source_seller)
            p2 = seller_pos.get(edge.target_seller)
            if p1 and p2:
                # Color code by edge type
                e_color = self._t("accent", "#38BDF8") if edge.link_type == "VISUAL_HASH" else self._t("warning", "#F59E0B")
                width = 3 if edge.link_type == "VISUAL_HASH" else 2
                c.create_line(p1[0], p1[1], p2[0], p2[1], fill=e_color, width=width)

        # Draw seller nodes on top
        s_r = 24
        for s, (sx, sy) in seller_pos.items():
            meta = cluster.seller_details.get(s, {})
            node_color = self._t("accent2", "#347BB7") if not meta.get("is_3pl") else self._t("warning", "#F59E0B")

            c.create_oval(sx - s_r, sy - s_r, sx + s_r, sy + s_r, fill=node_color, outline=self._t("text", "#FFFFFF"), width=1)
            # Truncate label for display
            disp_name = s if len(s) <= 12 else s[:10] + ".."
            c.create_text(sx, sy, text=disp_name, fill="#FFFFFF", font=("Segoe UI", 8, "bold"))
            # Location subtitle
            hub_lbl = meta.get("normalized_hub", "")
            if hub_lbl:
                hub_short = hub_lbl.split(",")[0]
                c.create_text(sx, sy + s_r + 10, text=f"📍 {hub_short}", fill=self._t("subtext", "#7C8FA3"), font=("Segoe UI", 7))

        # Graph Legend
        legend_y = 16
        c.create_text(20, legend_y, text="LEGEND:", anchor="w", fill=self._t("text", "#FFFFFF"), font=("Segoe UI", 8, "bold"))
        c.create_line(70, legend_y, 110, legend_y, fill=self._t("accent", "#38BDF8"), width=3)
        c.create_text(115, legend_y, text="Visual pHash Collision", anchor="w", fill=self._t("accent", "#38BDF8"), font=("Segoe UI", 7))

        c.create_line(230, legend_y, 270, legend_y, fill=self._t("warning", "#F59E0B"), width=2)
        c.create_text(275, legend_y, text="3PL Hub / Handle Overlap", anchor="w", fill=self._t("warning", "#F59E0B"), font=("Segoe UI", 7))

    def _on_item_double_click(self, event):
        sel = self.items_tree.selection()
        if not sel or not self.active_cluster:
            return
        vals = self.items_tree.item(sel[0], "values")
        if not vals:
            return
        item_id = vals[2]
        matching_item = next((i for i in self.active_cluster.items if str(i.get("item_id", "")) == str(item_id)), None)
        if matching_item and matching_item.get("url"):
            webbrowser.open(matching_item["url"])

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Action Handlers
    # ─────────────────────────────────────────────────────────────────────────
    def _copy_handles(self):
        if not self.active_cluster:
            messagebox.showinfo("Syndicate Hunter", "Please select a syndicate cluster first.", parent=self)
            return
        handles = sorted(list(self.active_cluster.sellers))
        text = ", ".join(handles)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set(f"Copied {len(handles)} handles to clipboard.")
        messagebox.showinfo("Copied", f"Copied {len(handles)} handles to clipboard:\n\n{text}", parent=self)

    def _queue_sellers(self):
        if not self.active_cluster:
            return
        handles = sorted(list(self.active_cluster.sellers))
        if hasattr(self.master, "_queue_seller_batch"):
            self.master._queue_seller_batch(handles)
            self.status_var.set(f"Queued {len(handles)} sellers for storefront crawl.")
            messagebox.showinfo("Queue Updated", f"Added {len(handles)} syndicate accounts to crawl queue.", parent=self)
        else:
            self._copy_handles()

    def _select_in_main_table(self):
        """Highlight and select all listings belonging to this syndicate in Apollo's main table."""
        if not self.active_cluster:
            return
        syndicate_sellers = self.active_cluster.sellers
        selected_count = 0

        # Iterate over master's results table treeview
        tree = getattr(self.master, "result_tree", getattr(self.master, "tree", None))
        if tree:
            tree.selection_set([])  # clear current selection
            new_selection = []
            for child in tree.get_children():
                # Check item metadata
                item_data = getattr(self.master, "_item_cache", {}).get(child)
                seller_val = ""
                if item_data:
                    seller_val = item_data.get("seller", "")
                else:
                    # fallback to treeview columns
                    vals = tree.item(child, "values")
                    if len(vals) > 5:
                        seller_val = vals[5]
                if seller_val in syndicate_sellers:
                    new_selection.append(child)
                    selected_count += 1

            if new_selection:
                tree.selection_set(new_selection)
                tree.see(new_selection[0])
                self.status_var.set(f"Selected {selected_count} syndicate items in main table.")
                messagebox.showinfo("Selection Updated", f"Successfully highlighted and selected {selected_count} items belonging to Syndicate {self.active_cluster.cluster_id} in Apollo's main table.", parent=self)
            else:
                messagebox.showinfo("Syndicate Hunter", "No matching items currently present in the main table.", parent=self)

    def _export_genesis_dossier(self):
        """Export full syndicate threat intelligence dossier formatted for Genesis / Legal Counsel."""
        if not self.clusters:
            messagebox.showinfo("Export", "No syndicates detected to export.", parent=self)
            return

        default_name = f"Apollo_Syndicate_Dossier_{len(self.clusters)}_Rings.xlsx"
        filepath = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook (*.xlsx)", "*.xlsx"), ("CSV (*.csv)", "*.csv")],
            initialfile=default_name
        )
        if not filepath:
            return

        try:
            records = self.graph_engine.export_genesis_records()
            import pandas as pd  # or openpyxl
            try:
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                wb = openpyxl.Workbook()
                ws_summary = wb.active
                ws_summary.title = "Syndicate Executive Summary"

                # Header styling
                h_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
                h_fill = PatternFill(start_color="0A0E36", end_color="0A0E36", fill_type="solid")
                h_align = Alignment(horizontal="center", vertical="center")

                # Summary sheet
                sum_headers = ["Syndicate ID", "Threat Score", "Confidence Tier", "Linked Storefronts", "Primary 3PL Hub", "Total SKUs", "Corroborating Evidence"]
                ws_summary.append(sum_headers)
                for col_num in range(1, len(sum_headers) + 1):
                    cell = ws_summary.cell(row=1, column=col_num)
                    cell.font = h_font
                    cell.fill = h_fill
                    cell.alignment = h_align

                for c in self.clusters:
                    ws_summary.append([
                        c.cluster_id,
                        c.threat_score,
                        c.confidence_tier,
                        ", ".join(sorted(c.sellers)),
                        ", ".join(c.shared_hubs) if c.shared_hubs else "N/A",
                        len(c.items),
                        " | ".join(c.evidence_summary)
                    ])

                # Detailed items sheet
                ws_details = wb.create_sheet(title="Linked Inventory Catalog")
                det_headers = ["Syndicate ID", "Threat Score", "Seller Handle", "Marketplace", "Dispatch Hub", "3PL Hub Flag", "Item Title", "Item ID", "Price", "URL", "Evidence Summary"]
                ws_details.append(det_headers)
                for col_num in range(1, len(det_headers) + 1):
                    cell = ws_details.cell(row=1, column=col_num)
                    cell.font = h_font
                    cell.fill = h_fill
                    cell.alignment = h_align

                for r in records:
                    ws_details.append([r[k] for k in det_headers])

                # Adjust column widths
                for ws in [ws_summary, ws_details]:
                    for col in ws.columns:
                        max_len = max(len(str(cell.value or "")) for cell in col)
                        col_letter = openpyxl.utils.get_column_letter(col[0].column)
                        ws.column_dimensions[col_letter].width = min(45, max(12, max_len + 3))

                wb.save(filepath)
            except ImportError:
                # Fallback to CSV
                import csv
                csv_path = filepath if filepath.endswith(".csv") else filepath + ".csv"
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=records[0].keys() if records else ["Notice"])
                    writer.writeheader()
                    writer.writerows(records)

            self.status_var.set(f"Exported Genesis dossier to: {os.path.basename(filepath)}")
            messagebox.showinfo("Export Complete", f"Successfully compiled and exported Genesis Syndicate Dossier to:\n\n{filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export dossier: {e}", parent=self)
