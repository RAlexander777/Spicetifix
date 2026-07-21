import customtkinter as ctk
from tkinter import messagebox

from automatify.core.utils import get_spotify_path
from automatify.core.config import read_spicetify_config, check_config_health
from automatify.core.i18n import t
from automatify.core.ui_theme import get_ui_theme
from automatify.core import spotify_control


class HomeFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_install,
        on_recover,
        on_uninstall_spicetify,
        on_uninstall_spotify,
        on_open_settings,
        theme: dict | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._actions = {
            "install": on_install,
            "recover": on_recover,
            "uninstall_sp": on_uninstall_spicetify,
            "uninstall_sf": on_uninstall_spotify,
            "settings": on_open_settings,
        }
        self._lang = "en"
        self._theme = theme or get_ui_theme("emerald")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main scrollable container so console & all cards are ALWAYS visible
        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=self._theme["card_bg"],
            corner_radius=8,
            border_width=1,
            border_color=self._theme["card_border"],
        )
        self.scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)

        row = 0

        # ── Header Bar ──
        self.header = ctk.CTkFrame(
            self.scroll,
            fg_color=self._theme["bg"],
            corner_radius=8,
            border_width=1,
            border_color=self._theme["card_border"],
            height=54,
        )
        self.header.grid(row=row, column=0, sticky="ew", padx=16, pady=(16, 12))
        self.header.grid_columnconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header,
            text="❯ AUTOMATIFY",
            font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color=self._theme["accent"],
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=(16, 0), pady=10)

        self.status_pill = ctk.CTkLabel(
            self.header,
            text="[ SYSTEM_READY ]",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=self._theme["contrast"],
        )
        self.status_pill.grid(row=0, column=1, sticky="w", padx=14, pady=10)

        self.settings_btn = ctk.CTkButton(
            self.header,
            text="⚙ CONFIG",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            width=95,
            height=32,
            fg_color=self._theme["card_bg"],
            border_width=1,
            border_color=self._theme["card_border"],
            hover_color=self._theme["bg"],
            text_color=self._theme["contrast"],
            command=self._actions["settings"],
        )
        self.settings_btn.grid(row=0, column=2, sticky="e", padx=(0, 14), pady=10)

        row += 1

        # ── Spotify Now Playing Widget ──
        self.player_box = ctk.CTkFrame(
            self.scroll,
            fg_color=self._theme["bg"],
            corner_radius=6,
            border_width=1,
            border_color=self._theme["card_border"],
        )
        self.player_box.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.player_box.grid_columnconfigure(0, weight=1)

        player_header = ctk.CTkFrame(self.player_box, fg_color="transparent")
        player_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 2))
        player_header.grid_columnconfigure(0, weight=1)

        self.lbl_now_playing_tag = ctk.CTkLabel(
            player_header,
            text="// SPOTIFY NOW PLAYING",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=self._theme["contrast"],
            anchor="w",
        )
        self.lbl_now_playing_tag.grid(row=0, column=0, sticky="w")

        self.track_info_lbl = ctk.CTkLabel(
            self.player_box,
            text="🎵 Spotify: Not Playing",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=self._theme["text_main"],
            anchor="w",
        )
        self.track_info_lbl.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))

        controls_frame = ctk.CTkFrame(self.player_box, fg_color="transparent")
        controls_frame.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 10))

        self.btn_prev = ctk.CTkButton(
            controls_frame,
            text="⏮ PREV",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            width=70,
            height=28,
            fg_color=self._theme["card_bg"],
            border_width=1,
            border_color=self._theme["card_border"],
            text_color=self._theme["text_main"],
            hover_color=self._theme["card_border"],
            command=self._on_prev_track,
        )
        self.btn_prev.pack(side="left", padx=(0, 6))

        self.btn_play = ctk.CTkButton(
            controls_frame,
            text="⏯ PLAY / PAUSE",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            width=120,
            height=28,
            fg_color=self._theme["accent"],
            text_color="#08090d",
            hover_color=self._theme["accent_hover"],
            command=self._on_play_pause,
        )
        self.btn_play.pack(side="left", padx=(0, 6))

        self.btn_next = ctk.CTkButton(
            controls_frame,
            text="⏭ NEXT",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            width=70,
            height=28,
            fg_color=self._theme["card_bg"],
            border_width=1,
            border_color=self._theme["card_border"],
            text_color=self._theme["text_main"],
            hover_color=self._theme["card_border"],
            command=self._on_next_track,
        )
        self.btn_next.pack(side="left")

        row += 1

        # ── Status cards section ──
        self.sec_status = self._section_label("STATUS", row, (0, 6))
        row += 1

        cards_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        cards_frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 14))
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="card")

        self.card_spotify = self._build_card_frame(cards_frame, 0)
        self.card_spicetify = self._build_card_frame(cards_frame, 1)
        self.card_theme = self._build_card_frame(cards_frame, 2)

        row += 1

        # ── Config Health section ──
        self._health_expanded = False
        self._health_btn = ctk.CTkButton(
            self.scroll,
            text="▶ CONFIG HEALTH",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=self._theme["text_muted"],
            anchor="w",
            fg_color="transparent",
            hover_color=self._theme["bg"],
            height=26,
            width=180,
            command=self._toggle_health,
        )
        self._health_btn.grid(row=row, column=0, sticky="w", padx=16, pady=(2, 4))
        row += 1

        self.health_frame = ctk.CTkFrame(
            self.scroll,
            fg_color=self._theme["console_bg"],
            corner_radius=6,
            border_width=1,
            border_color=self._theme["card_border"],
        )
        self.health_frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.health_frame.grid_columnconfigure(0, weight=1)
        self.health_frame.grid_remove()

        self.health_items = []
        row += 1

        # ── Actions section ──
        self.sec_actions = self._section_label("ACTIONS", row, (2, 6))
        row += 1

        btn_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 14))
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.install_btn = ctk.CTkButton(
            btn_frame,
            text="▶ RUN FULL INSTALL / UPDATE",
            height=46,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            fg_color=self._theme["accent"],
            text_color="#08090d",
            hover_color=self._theme["accent_hover"],
            command=self._actions["install"],
        )
        self.install_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.recover_btn = ctk.CTkButton(
            btn_frame,
            text="↺ RECOVER SYSTEM",
            height=46,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            fg_color=self._theme["bg"],
            border_width=1,
            border_color=self._theme["card_border"],
            text_color=self._theme["contrast"],
            hover_color=self._theme["card_border"],
            command=self._actions["recover"],
        )
        self.recover_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        row += 1

        # ── Danger zone section ──
        self.sec_danger = self._section_label("DANGER ZONE", row, (8, 4), color=self._theme["danger"])
        row += 1

        danger = ctk.CTkFrame(self.scroll, fg_color="transparent")
        danger.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 14))

        self.uninstall_sp_btn = ctk.CTkButton(
            danger,
            text="✖ Uninstall Spicetify",
            height=32,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            fg_color=self._theme["danger_bg"],
            text_color=self._theme["danger"],
            hover_color=self._theme["danger_border"],
            border_width=1,
            border_color=self._theme["danger_border"],
            command=self._confirm_uninstall_spicetify,
        )
        self.uninstall_sp_btn.pack(side="left", padx=(0, 10))

        self.uninstall_sf_btn = ctk.CTkButton(
            danger,
            text="✖ Uninstall Spotify",
            height=32,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            fg_color=self._theme["danger_bg"],
            text_color=self._theme["danger"],
            hover_color=self._theme["danger_border"],
            border_width=1,
            border_color=self._theme["danger_border"],
            command=self._confirm_uninstall_spotify,
        )
        self.uninstall_sf_btn.pack(side="left")

        row += 1

        # ── Output / Terminal Console ──
        self.sec_output = self._section_label("OUTPUT", row, (2, 4))
        row += 1

        self.log_box = ctk.CTkTextbox(
            self.scroll,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            height=160,  # Fixed height so console is ALWAYS visible
            fg_color=self._theme["console_bg"],
            text_color=self._theme["console_fg"],
            border_width=1,
            border_color=self._theme["card_border"],
            corner_radius=6,
        )
        self.log_box.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.log_box.configure(state="disabled")

        self.log("root@automatify:~$ system initialized. Ready.")

        row += 1

        # ── Progress bar ──
        self.progress = ctk.CTkProgressBar(
            self.scroll, height=6, fg_color=self._theme["bg"], progress_color=self._theme["accent"]
        )
        self.progress.grid(row=row, column=0, sticky="ew", padx=16, pady=(4, 20))
        self.progress.set(0)

        self._rebuild_texts()
        self.refresh_status()

        # Start periodic polling for Spotify Now Playing
        self._poll_now_playing()

    def set_ui_theme(self, theme: dict) -> None:
        self._theme = theme
        self.scroll.configure(fg_color=theme["card_bg"], border_color=theme["card_border"])
        self.header.configure(fg_color=theme["bg"], border_color=theme["card_border"])
        self.title_label.configure(text_color=theme["accent"])
        self.status_pill.configure(text_color=theme["contrast"])
        self.settings_btn.configure(
            fg_color=theme["card_bg"],
            border_color=theme["card_border"],
            hover_color=theme["bg"],
            text_color=theme["contrast"],
        )
        self.player_box.configure(fg_color=theme["bg"], border_color=theme["card_border"])
        self.lbl_now_playing_tag.configure(text_color=theme["contrast"])
        self.track_info_lbl.configure(text_color=theme["text_main"])
        self.btn_prev.configure(
            fg_color=theme["card_bg"], border_color=theme["card_border"], text_color=theme["text_main"]
        )
        self.btn_play.configure(fg_color=theme["accent"], hover_color=theme["accent_hover"])
        self.btn_next.configure(
            fg_color=theme["card_bg"], border_color=theme["card_border"], text_color=theme["text_main"]
        )
        self.install_btn.configure(fg_color=theme["accent"], hover_color=theme["accent_hover"])
        self.recover_btn.configure(
            fg_color=theme["bg"],
            border_color=theme["card_border"],
            text_color=theme["contrast"],
            hover_color=theme["card_border"],
        )
        self.uninstall_sp_btn.configure(
            fg_color=theme["danger_bg"], text_color=theme["danger"], border_color=theme["danger_border"]
        )
        self.uninstall_sf_btn.configure(
            fg_color=theme["danger_bg"], text_color=theme["danger"], border_color=theme["danger_border"]
        )
        self.log_box.configure(
            fg_color=theme["console_bg"], text_color=theme["console_fg"], border_color=theme["card_border"]
        )
        self.progress.configure(fg_color=theme["bg"], progress_color=theme["accent"])
        self.refresh_status()

    # ── Spotify Player Widget Actions ──
    def _poll_now_playing(self) -> None:
        try:
            info = spotify_control.get_spotify_now_playing()
            if info["playing"]:
                self.track_info_lbl.configure(
                    text=f"🎵 {info['artist']} — {info['title']}",
                    text_color=self._theme["accent"],
                )
            else:
                txt = f"🎵 {info['title']}" if info['title'] else "🎵 Spotify: Not Playing"
                self.track_info_lbl.configure(
                    text=txt,
                    text_color=self._theme["text_muted"],
                )
        except Exception:
            pass

        self.after(2000, self._poll_now_playing)

    def _on_play_pause(self) -> None:
        spotify_control.play_pause()
        self.after(300, self._poll_now_playing)

    def _on_next_track(self) -> None:
        spotify_control.next_track()
        self.after(300, self._poll_now_playing)

    def _on_prev_track(self) -> None:
        spotify_control.prev_track()
        self.after(300, self._poll_now_playing)

    # ── Section label ──
    def _section_label(
        self, text_key: str, row: int, pady: tuple, color: str | None = None
    ) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(
            self.scroll,
            text="",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=color or self._theme["contrast"],
            anchor="w",
        )
        lbl.grid(row=row, column=0, sticky="w", padx=16, pady=pady)
        setattr(self, f"_lbl_{text_key.lower().replace(' ','_')}", lbl)
        return lbl

    def _update_section_labels(self) -> None:
        l = self._lang
        arrow = "▼" if self._health_expanded else "▶"
        self._health_btn.configure(
            text=f"{arrow}  {t(l, 'config_health')}",
            text_color=self._theme["text_muted"],
        )
        for key, attr in [
            ("STATUS", "_lbl_status"),
            ("ACTIONS", "_lbl_actions"),
            ("DANGER ZONE", "_lbl_danger_zone"),
            ("OUTPUT", "_lbl_output"),
        ]:
            lbl = getattr(self, attr, None)
            if lbl:
                lbl.configure(text=f"// {t(l, key.lower().replace(' ', '_'))}")

    def _toggle_health(self) -> None:
        self._health_expanded = not self._health_expanded
        if self._health_expanded:
            self.health_frame.grid()
        else:
            self.health_frame.grid_remove()
        self._update_section_labels()

    # ── Cards ──
    def _build_card_frame(self, parent, col: int) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(
            parent,
            corner_radius=8,
            fg_color=self._theme["bg"],
            border_width=1,
            border_color=self._theme["card_border"],
        )
        frame.grid(
            row=0,
            column=col,
            sticky="ew",
            padx=(0, 6) if col == 0 else (3, 3) if col == 1 else (6, 0),
        )
        frame.grid_columnconfigure(0, weight=1)
        return frame

    def _render_card(
        self, frame: ctk.CTkFrame, title: str, subtitle: str, ok: bool
    ) -> None:
        for w in frame.winfo_children():
            w.destroy()

        dot_color = self._theme["accent"] if ok else self._theme["danger"]
        status_tag = "[ ONLINE ]" if ok else "[ MISSING ]"

        row_frame = ctk.CTkFrame(frame, fg_color="transparent")
        row_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
        row_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            row_frame,
            text=f"❯ {title}",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=self._theme["text_main"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            row_frame,
            text=status_tag,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=dot_color,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            frame,
            text=subtitle[:45],
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=self._theme["text_muted"],
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

    # ── Config Health ──
    def _render_health(self, checks: list[dict]) -> None:
        for w in self.health_items:
            w.destroy()
        self.health_items.clear()

        all_ok = all(c["ok"] for c in checks)

        if all_ok and not self._health_expanded:
            self._update_section_labels()
            return

        if not all_ok and not self._health_expanded:
            self._toggle_health()

        for i, check in enumerate(checks):
            row = ctk.CTkFrame(self.health_frame, fg_color="transparent", height=24)
            row.grid(row=i, column=0, sticky="ew", pady=2)
            row.grid_columnconfigure(1, weight=1)

            symbol = "[OK]" if check["ok"] else "[FAIL]"
            color = self._theme["accent"] if check["ok"] else self._theme["danger"]

            ctk.CTkLabel(
                row,
                text=symbol,
                font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
                text_color=color,
                width=42,
            ).grid(row=0, column=0, padx=(8, 0))

            ctk.CTkLabel(
                row,
                text=check["label"],
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color=self._theme["text_main"] if check["ok"] else self._theme["danger"],
                anchor="w",
            ).grid(row=0, column=1, sticky="w", padx=(4, 6))

            ctk.CTkLabel(
                row,
                text=check["detail"],
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color=self._theme["text_muted"],
                anchor="e",
            ).grid(row=0, column=2, sticky="e", padx=(4, 8))

            self.health_items.append(row)

    def refresh_status(self) -> None:
        l = self._lang
        spotify_ok = get_spotify_path() is not None
        sc_conf = read_spicetify_config()
        spicetify_ok = sc_conf is not None

        theme = t(l, "none")
        if sc_conf and "Setting" in sc_conf:
            tv = sc_conf["Setting"].get("current_theme", "")
            theme = tv if tv else t(l, "none")
        theme_ok = theme != t(l, "none")

        spotify_path = get_spotify_path() or ""
        spotify_sub = spotify_path[:40] if spotify_ok else t(l, "not_installed")
        spicetify_sub = t(l, "configured") if spicetify_ok else t(l, "not_configured")

        self._render_card(self.card_spotify, t(l, "spotify"), spotify_sub, spotify_ok)
        self._render_card(
            self.card_spicetify, t(l, "spicetify"), spicetify_sub, spicetify_ok
        )
        self._render_card(self.card_theme, t(l, "theme"), theme, theme_ok)

        checks = check_config_health()
        self._render_health(checks)

    # ── Language ──
    def set_lang(self, lang: str) -> None:
        self._lang = lang
        self._rebuild_texts()
        self.refresh_status()

    def _rebuild_texts(self) -> None:
        l = self._lang
        self._update_section_labels()
        self.uninstall_sp_btn.configure(text=f"✖ {t(l, 'uninstall_spicetify')}")
        self.uninstall_sf_btn.configure(text=f"✖ {t(l, 'uninstall_spotify')}")
        if self.install_btn.cget("state") == "normal":
            self.install_btn.configure(text=f"▶ {t(l, 'install_btn')}")
        self.recover_btn.configure(text=f"↺ {t(l, 'recover_btn')}")

    # ── Logging ──
    def log(self, msg: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ── Loading state ──
    def set_loading(self, loading: bool) -> None:
        l = self._lang
        if loading:
            self.status_pill.configure(text="[ EXECUTING... ]", text_color=self._theme["accent"])
            self.install_btn.configure(state="disabled", text=t(l, "working"))
            self.recover_btn.configure(state="disabled")
            self.uninstall_sp_btn.configure(state="disabled")
            self.uninstall_sf_btn.configure(state="disabled")
            self.progress.configure(mode="determinate")
            self.progress.set(0)
        else:
            self.status_pill.configure(text="[ SYSTEM_READY ]", text_color=self._theme["contrast"])
            self.install_btn.configure(state="normal", text=f"▶ {t(l, 'install_btn')}")
            self.recover_btn.configure(state="normal")
            self.uninstall_sp_btn.configure(state="normal")
            self.uninstall_sf_btn.configure(state="normal")
            self.progress.set(0)

    # ── Confirmation Dialogs ──
    def _confirm_uninstall_spicetify(self) -> None:
        l = self._lang
        if messagebox.askyesno(
            t(l, "uninstall_spicetify"),
            t(l, "confirm_uninstall_spicetify"),
            icon="warning",
        ):
            self._actions["uninstall_sp"]()

    def _confirm_uninstall_spotify(self) -> None:
        l = self._lang
        if messagebox.askyesno(
            t(l, "uninstall_spotify"),
            t(l, "confirm_uninstall_spotify"),
            icon="warning",
        ):
            self._actions["uninstall_sf"]()
