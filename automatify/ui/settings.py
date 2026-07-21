import customtkinter as ctk

from automatify.core.config import (
    load_user_config,
    save_user_config,
    get_installed_extensions,
    get_installed_custom_apps,
)
from automatify.core.themer import list_available_themes
from automatify.core.i18n import t
from automatify.core.ui_theme import get_ui_theme, THEMES, list_ui_theme_names


class SettingsPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        lang: str = "en",
        on_back=None,
        on_saved=None,
        theme: dict | None = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._lang = lang
        self._on_back = on_back
        self._on_saved = on_saved
        self._theme = theme or get_ui_theme("emerald")
        self._l = lambda k: t(self._lang, k)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main scrollable container
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

        # Header
        header_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        header_frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(16, 14))
        header_frame.grid_columnconfigure(1, weight=1)

        self.back_btn = ctk.CTkButton(
            header_frame,
            text="❮ BACK",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            fg_color="transparent",
            text_color=self._theme["contrast"],
            hover_color=self._theme["card_bg"],
            border_width=1,
            border_color=self._theme["card_border"],
            width=85,
            height=32,
            command=self._on_back,
        )
        self.back_btn.grid(row=0, column=0, sticky="w")

        self.header_title = ctk.CTkLabel(
            header_frame,
            text="❯ SYSTEM_CONFIGURATION",
            font=ctk.CTkFont(family="Consolas", size=16, weight="bold"),
            text_color=self._theme["accent"],
        )
        self.header_title.grid(row=0, column=1, sticky="w", padx=(16, 0))

        row += 1

        # ── General Settings Section ──
        self.sec_1 = self._build_section_header("01 // GENERAL CONFIG & UI THEME", row)
        row += 1

        self.gen_box = ctk.CTkFrame(
            self.scroll,
            fg_color=self._theme["bg"],
            corner_radius=6,
            border_width=1,
            border_color=self._theme["card_border"],
        )
        self.gen_box.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.gen_box.grid_columnconfigure((0, 1), weight=1)

        # Language
        self.lbl_lang = ctk.CTkLabel(
            self.gen_box,
            text=self._l("settings_language"),
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=self._theme["text_muted"],
        )
        self.lbl_lang.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))

        self.lang_cb = ctk.CTkComboBox(
            self.gen_box,
            values=["en", "es"],
            state="readonly",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=self._theme["card_bg"],
            border_color=self._theme["card_border"],
            text_color=self._theme["text_main"],
            height=34,
        )
        self.lang_cb.grid(row=1, column=0, sticky="ew", padx=(14, 7), pady=(0, 12))

        # Interface Theme Dropdown + Color Swatch Preview Box
        self.lbl_ui_theme = ctk.CTkLabel(
            self.gen_box,
            text=self._l("settings_ui_theme"),
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=self._theme["text_muted"],
        )
        self.lbl_ui_theme.grid(row=0, column=1, sticky="w", padx=14, pady=(12, 2))

        theme_picker_frame = ctk.CTkFrame(self.gen_box, fg_color="transparent")
        theme_picker_frame.grid(row=1, column=1, sticky="ew", padx=(7, 14), pady=(0, 12))
        theme_picker_frame.grid_columnconfigure(0, weight=1)

        ui_theme_map = list_ui_theme_names()
        self._ui_theme_name_to_key = {v: k for k, v in ui_theme_map.items()}

        self.ui_theme_cb = ctk.CTkComboBox(
            theme_picker_frame,
            values=list(ui_theme_map.values()),
            state="readonly",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=self._theme["card_bg"],
            border_color=self._theme["card_border"],
            text_color=self._theme["text_main"],
            height=34,
            command=self._on_ui_theme_dropdown_change,
        )
        self.ui_theme_cb.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        # Color Swatch Preview Frame ("recuadro de color")
        self.swatch_box = ctk.CTkFrame(
            theme_picker_frame,
            fg_color=self._theme["card_bg"],
            border_width=1,
            border_color=self._theme["card_border"],
            height=34,
            width=70,
        )
        self.swatch_box.grid(row=0, column=1, sticky="e")

        self.swatch_accent = ctk.CTkFrame(
            self.swatch_box, fg_color=self._theme["accent"], width=16, height=16, corner_radius=3
        )
        self.swatch_accent.pack(side="left", padx=4, pady=8)

        self.swatch_contrast = ctk.CTkFrame(
            self.swatch_box, fg_color=self._theme["contrast"], width=16, height=16, corner_radius=3
        )
        self.swatch_contrast.pack(side="left", padx=4, pady=8)

        self.swatch_bg = ctk.CTkFrame(
            self.swatch_box, fg_color=self._theme["bg"], width=16, height=16, corner_radius=3
        )
        self.swatch_bg.pack(side="left", padx=4, pady=8)

        # Spicetify Theme & Color Scheme
        self.lbl_spicetify_theme = ctk.CTkLabel(
            self.gen_box,
            text=self._l("settings_theme") + " (Spicetify)",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=self._theme["text_muted"],
        )
        self.lbl_spicetify_theme.grid(row=2, column=0, sticky="w", padx=14, pady=(4, 2))

        self.lbl_color_scheme = ctk.CTkLabel(
            self.gen_box,
            text=self._l("settings_color_scheme"),
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=self._theme["text_muted"],
        )
        self.lbl_color_scheme.grid(row=2, column=1, sticky="w", padx=14, pady=(4, 2))

        self.theme_cb = ctk.CTkComboBox(
            self.gen_box,
            values=[],
            state="readonly",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=self._theme["card_bg"],
            border_color=self._theme["card_border"],
            text_color=self._theme["text_main"],
            height=34,
        )
        self.theme_cb.grid(row=3, column=0, sticky="ew", padx=(14, 7), pady=(0, 14))

        self.scheme_cb = ctk.CTkComboBox(
            self.gen_box,
            values=["dark", "light"],
            state="readonly",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=self._theme["card_bg"],
            border_color=self._theme["card_border"],
            text_color=self._theme["text_main"],
            height=34,
        )
        self.scheme_cb.grid(row=3, column=1, sticky="ew", padx=(7, 14), pady=(0, 14))

        row += 1

        # ── Extensions Section ──
        self.sec_2 = self._build_section_header("02 // SPICETIFY EXTENSIONS", row)
        row += 1

        self.ext_box = ctk.CTkFrame(
            self.scroll,
            fg_color=self._theme["bg"],
            corner_radius=6,
            border_width=1,
            border_color=self._theme["card_border"],
        )
        self.ext_box.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.ext_box.grid_columnconfigure(0, weight=1)

        ext_top = ctk.CTkFrame(self.ext_box, fg_color="transparent")
        ext_top.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        ext_top.grid_columnconfigure(0, weight=1)

        self.lbl_ext_detected = ctk.CTkLabel(
            ext_top,
            text="Detected extensions in Spicetify / Extensions folder:",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=self._theme["text_muted"],
        )
        self.lbl_ext_detected.grid(row=0, column=0, sticky="w")

        self.scan_btn = ctk.CTkButton(
            ext_top,
            text="↻ SCAN DISK",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            fg_color="transparent",
            border_width=1,
            border_color=self._theme["card_border"],
            text_color=self._theme["accent"],
            hover_color=self._theme["card_bg"],
            height=26,
            width=95,
            command=self._refresh_extensions,
        )
        self.scan_btn.grid(row=0, column=1, sticky="e")

        self.ext_scroll = ctk.CTkFrame(
            self.ext_box,
            fg_color=self._theme["card_bg"],
            corner_radius=4,
            border_width=1,
            border_color=self._theme["card_border"],
        )
        self.ext_scroll.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        self.ext_scroll.grid_columnconfigure(0, weight=1)

        ext_add_frame = ctk.CTkFrame(self.ext_box, fg_color="transparent")
        ext_add_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        ext_add_frame.grid_columnconfigure(0, weight=1)

        self.ext_entry = ctk.CTkEntry(
            ext_add_frame,
            placeholder_text=self._l("settings_extension_placeholder"),
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=self._theme["card_bg"],
            border_color=self._theme["card_border"],
            text_color=self._theme["text_main"],
            height=34,
        )
        self.ext_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.add_ext_btn = ctk.CTkButton(
            ext_add_frame,
            text="+ ADD EXTENSION",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            fg_color=self._theme["accent"],
            text_color="#08090d",
            hover_color=self._theme["accent_hover"],
            height=34,
            width=140,
            command=self._add_extension,
        )
        self.add_ext_btn.grid(row=0, column=1, sticky="e")

        row += 1

        # ── Custom Apps Section ──
        self.sec_3 = self._build_section_header("03 // CUSTOM APPS", row)
        row += 1

        self.app_box = ctk.CTkFrame(
            self.scroll,
            fg_color=self._theme["bg"],
            corner_radius=6,
            border_width=1,
            border_color=self._theme["card_border"],
        )
        self.app_box.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.app_box.grid_columnconfigure(0, weight=1)

        self.apps_scroll = ctk.CTkFrame(
            self.app_box,
            fg_color=self._theme["card_bg"],
            corner_radius=4,
            border_width=1,
            border_color=self._theme["card_border"],
        )
        self.apps_scroll.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        self.apps_scroll.grid_columnconfigure(0, weight=1)

        app_add_frame = ctk.CTkFrame(self.app_box, fg_color="transparent")
        app_add_frame.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        app_add_frame.grid_columnconfigure(0, weight=1)

        self.app_entry = ctk.CTkEntry(
            app_add_frame,
            placeholder_text=self._l("settings_app_placeholder"),
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=self._theme["card_bg"],
            border_color=self._theme["card_border"],
            text_color=self._theme["text_main"],
            height=34,
        )
        self.app_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.add_app_btn = ctk.CTkButton(
            app_add_frame,
            text="+ ADD APP",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            fg_color=self._theme["accent"],
            text_color="#08090d",
            hover_color=self._theme["accent_hover"],
            height=34,
            width=110,
            command=self._add_app,
        )
        self.add_app_btn.grid(row=0, column=1, sticky="e")

        row += 1

        # ── Preprocesses & Options ──
        self.sec_4 = self._build_section_header("04 // ADVANCED OPTIONS", row)
        row += 1

        self.opt_box = ctk.CTkFrame(
            self.scroll,
            fg_color=self._theme["bg"],
            corner_radius=6,
            border_width=1,
            border_color=self._theme["card_border"],
        )
        self.opt_box.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 20))
        self.opt_box.grid_columnconfigure(0, weight=1)

        self._switches: list[ctk.CTkSwitch] = []
        self.sw_sentry = self._switch_item(self.opt_box, self._l("pre_disable_sentry"), 0)
        self.sw_logging = self._switch_item(self.opt_box, self._l("pre_disable_logging"), 1)
        self.sw_rtl = self._switch_item(self.opt_box, self._l("pre_remove_rtl"), 2)
        self.sw_apis = self._switch_item(self.opt_box, self._l("pre_expose_apis"), 3)
        self.sw_css = self._switch_item(self.opt_box, self._l("opt_inject_css"), 4)
        self.sw_colors = self._switch_item(self.opt_box, self._l("opt_replace_colors"), 5)

        row += 1

        # Save / Cancel Footer
        btn_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
        btn_frame.grid(row=row, column=0, sticky="ew", padx=16, pady=(8, 24))
        btn_frame.grid_columnconfigure(0, weight=1)

        self.cancel_btn = ctk.CTkButton(
            btn_frame,
            text=self._l("settings_cancel").upper(),
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            fg_color="transparent",
            border_width=1,
            border_color=self._theme["card_border"],
            text_color=self._theme["text_muted"],
            hover_color=self._theme["card_bg"],
            width=110,
            height=38,
            command=self._on_back,
        )
        self.cancel_btn.pack(side="right", padx=(10, 0))

        self.save_btn = ctk.CTkButton(
            btn_frame,
            text="SAVE & APPLY",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            fg_color=self._theme["accent"],
            text_color="#08090d",
            hover_color=self._theme["accent_hover"],
            width=140,
            height=38,
            command=self._save,
        )
        self.save_btn.pack(side="right")

        self._ext_items: dict[str, ctk.CTkSwitch] = {}
        self._app_items: dict[str, ctk.CTkSwitch] = {}

    def _build_section_header(self, title: str, row: int) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(
            self.scroll,
            text=title,
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=self._theme["contrast"],
            anchor="w",
        )
        lbl.grid(row=row, column=0, sticky="w", padx=16, pady=(12, 6))
        return lbl

    def _switch_item(self, parent, label: str, index: int) -> ctk.CTkSwitch:
        row_f = ctk.CTkFrame(parent, fg_color="transparent")
        row_f.grid(row=index, column=0, sticky="ew", padx=14, pady=6)
        row_f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            row_f,
            text=label,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=self._theme["text_main"],
        ).grid(row=0, column=0, sticky="w")

        sw = ctk.CTkSwitch(
            row_f,
            text="",
            progress_color=self._theme["accent"],
            button_color=self._theme["text_main"],
            height=22,
            width=44,
        )
        sw.grid(row=0, column=1, sticky="e")
        self._switches.append(sw)
        return sw

    def _on_ui_theme_dropdown_change(self, selected_ui_name: str) -> None:
        key = self._ui_theme_name_to_key.get(selected_ui_name, "emerald")
        preview_theme = get_ui_theme(key)
        self.swatch_accent.configure(fg_color=preview_theme["accent"])
        self.swatch_contrast.configure(fg_color=preview_theme["contrast"])
        self.swatch_bg.configure(fg_color=preview_theme["bg"])
        self.swatch_box.configure(
            fg_color=preview_theme["card_bg"], border_color=preview_theme["card_border"]
        )

    def set_ui_theme(self, theme: dict) -> None:
        self._theme = theme
        self.scroll.configure(fg_color=theme["card_bg"], border_color=theme["card_border"])
        self.header_title.configure(text_color=theme["accent"])
        self.back_btn.configure(
            text_color=theme["contrast"],
            border_color=theme["card_border"],
            hover_color=theme["card_bg"],
        )
        self.sec_1.configure(text_color=theme["contrast"])
        self.sec_2.configure(text_color=theme["contrast"])
        self.sec_3.configure(text_color=theme["contrast"])
        self.sec_4.configure(text_color=theme["contrast"])

        self.gen_box.configure(fg_color=theme["bg"], border_color=theme["card_border"])
        self.ext_box.configure(fg_color=theme["bg"], border_color=theme["card_border"])
        self.app_box.configure(fg_color=theme["bg"], border_color=theme["card_border"])
        self.opt_box.configure(fg_color=theme["bg"], border_color=theme["card_border"])

        self.lbl_lang.configure(text_color=theme["text_muted"])
        self.lbl_ui_theme.configure(text_color=theme["text_muted"])
        self.lbl_spicetify_theme.configure(text_color=theme["text_muted"])
        self.lbl_color_scheme.configure(text_color=theme["text_muted"])
        self.lbl_ext_detected.configure(text_color=theme["text_muted"])

        self.lang_cb.configure(
            fg_color=theme["card_bg"], border_color=theme["card_border"], text_color=theme["text_main"]
        )
        self.ui_theme_cb.configure(
            fg_color=theme["card_bg"], border_color=theme["card_border"], text_color=theme["text_main"]
        )
        self.theme_cb.configure(
            fg_color=theme["card_bg"], border_color=theme["card_border"], text_color=theme["text_main"]
        )
        self.scheme_cb.configure(
            fg_color=theme["card_bg"], border_color=theme["card_border"], text_color=theme["text_main"]
        )

        self.add_ext_btn.configure(
            fg_color=theme["accent"], hover_color=theme["accent_hover"]
        )
        self.add_app_btn.configure(
            fg_color=theme["accent"], hover_color=theme["accent_hover"]
        )
        self.scan_btn.configure(
            border_color=theme["card_border"], text_color=theme["accent"], hover_color=theme["card_bg"]
        )

        self.ext_scroll.configure(fg_color=theme["card_bg"], border_color=theme["card_border"])
        self.apps_scroll.configure(fg_color=theme["card_bg"], border_color=theme["card_border"])

        self.ext_entry.configure(
            fg_color=theme["card_bg"], border_color=theme["card_border"], text_color=theme["text_main"]
        )
        self.app_entry.configure(
            fg_color=theme["card_bg"], border_color=theme["card_border"], text_color=theme["text_main"]
        )

        self.save_btn.configure(fg_color=theme["accent"], hover_color=theme["accent_hover"])
        self.cancel_btn.configure(border_color=theme["card_border"], text_color=theme["text_muted"])

        for sw in self._switches:
            sw.configure(progress_color=theme["accent"], button_color=theme["text_main"])

        self._on_ui_theme_dropdown_change(self.ui_theme_cb.get())
        self.load()

    def set_lang(self, lang: str) -> None:
        self._lang = lang
        self._l = lambda k: t(self._lang, k)

    def load(self) -> None:
        self._load_themes()
        self._load_config()

    def _load_themes(self) -> None:
        themes = list_available_themes()
        if themes:
            self.theme_cb.configure(values=themes)

    def _refresh_extensions(self) -> None:
        self._load_config()

    def _load_config(self) -> None:
        cfg = load_user_config()
        sc = cfg.get("spicetify", {})

        self.lang_cb.set(cfg.get("language", "en"))

        current_ui_theme_key = cfg.get("ui_theme", "emerald")
        ui_theme_names = list_ui_theme_names()
        current_ui_name = ui_theme_names.get(current_ui_theme_key, ui_theme_names["emerald"])
        self.ui_theme_cb.set(current_ui_name)
        self._on_ui_theme_dropdown_change(current_ui_name)

        current = sc.get("theme", "")
        if current and self.theme_cb._values and current in self.theme_cb._values:
            self.theme_cb.set(current)
        self.scheme_cb.set(sc.get("color_scheme", "dark"))

        # Load extension switches
        for w in self.ext_scroll.winfo_children():
            w.destroy()

        self._ext_items.clear()
        detected_exts = get_installed_extensions()
        user_exts = set(cfg.get("extensions", []))
        all_exts = sorted(list(set(detected_exts) | user_exts))

        if not all_exts:
            ctk.CTkLabel(
                self.ext_scroll,
                text="  No extension files detected in Spicetify / Extensions.",
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color=self._theme["text_muted"],
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        else:
            for i, ext_name in enumerate(all_exts):
                rf = ctk.CTkFrame(self.ext_scroll, fg_color="transparent")
                rf.grid(row=i, column=0, sticky="ew", padx=10, pady=4)
                rf.grid_columnconfigure(0, weight=1)

                is_active = ext_name in user_exts
                dot_col = self._theme["accent"] if is_active else self._theme["text_muted"]

                ctk.CTkLabel(
                    rf,
                    text=f"● {ext_name}",
                    font=ctk.CTkFont(family="Consolas", size=12),
                    text_color=dot_col,
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                sw = ctk.CTkSwitch(
                    rf,
                    text="",
                    progress_color=self._theme["accent"],
                    button_color=self._theme["text_main"],
                    height=20,
                    width=40,
                )
                if is_active:
                    sw.select()
                sw.grid(row=0, column=1, sticky="e")
                self._ext_items[ext_name] = sw

        # Load custom app switches
        for w in self.apps_scroll.winfo_children():
            w.destroy()

        self._app_items.clear()
        detected_apps = get_installed_custom_apps()
        user_apps = set(cfg.get("custom_apps", []))
        all_apps = sorted(list(set(detected_apps) | user_apps))

        if not all_apps:
            ctk.CTkLabel(
                self.apps_scroll,
                text="  No custom apps detected in Spicetify / CustomApps.",
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color=self._theme["text_muted"],
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=10, pady=10)
        else:
            for i, app_name in enumerate(all_apps):
                rf = ctk.CTkFrame(self.apps_scroll, fg_color="transparent")
                rf.grid(row=i, column=0, sticky="ew", padx=10, pady=4)
                rf.grid_columnconfigure(0, weight=1)

                is_active = app_name in user_apps
                dot_col = self._theme["accent"] if is_active else self._theme["text_muted"]

                ctk.CTkLabel(
                    rf,
                    text=f"● {app_name}",
                    font=ctk.CTkFont(family="Consolas", size=12),
                    text_color=dot_col,
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                sw = ctk.CTkSwitch(
                    rf,
                    text="",
                    progress_color=self._theme["accent"],
                    button_color=self._theme["text_main"],
                    height=20,
                    width=40,
                )
                if is_active:
                    sw.select()
                sw.grid(row=0, column=1, sticky="e")
                self._app_items[app_name] = sw

        # Options & Preprocesses
        pp = cfg.get("preprocesses", {})
        self.sw_sentry.select() if pp.get("disable_sentry", True) else self.sw_sentry.deselect()
        self.sw_logging.select() if pp.get("disable_ui_logging", True) else self.sw_logging.deselect()
        self.sw_rtl.select() if pp.get("remove_rtl_rule", True) else self.sw_rtl.deselect()
        self.sw_apis.select() if pp.get("expose_apis", True) else self.sw_apis.deselect()

        opt = cfg.get("options", {})
        self.sw_css.select() if opt.get("inject_css", True) else self.sw_css.deselect()
        self.sw_colors.select() if opt.get("replace_colors", True) else self.sw_colors.deselect()

    def _add_extension(self) -> None:
        name = self.ext_entry.get().strip()
        if name and name not in self._ext_items:
            i = len(self._ext_items)
            rf = ctk.CTkFrame(self.ext_scroll, fg_color="transparent")
            rf.grid(row=i, column=0, sticky="ew", padx=10, pady=4)
            rf.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                rf,
                text=f"● {name}",
                font=ctk.CTkFont(family="Consolas", size=12),
                text_color=self._theme["accent"],
                anchor="w",
            ).grid(row=0, column=0, sticky="w")

            sw = ctk.CTkSwitch(
                rf,
                text="",
                progress_color=self._theme["accent"],
                button_color=self._theme["text_main"],
                height=20,
                width=40,
            )
            sw.select()
            sw.grid(row=0, column=1, sticky="e")
            self._ext_items[name] = sw
            self.ext_entry.delete(0, "end")

    def _add_app(self) -> None:
        name = self.app_entry.get().strip()
        if name and name not in self._app_items:
            i = len(self._app_items)
            rf = ctk.CTkFrame(self.apps_scroll, fg_color="transparent")
            rf.grid(row=i, column=0, sticky="ew", padx=10, pady=4)
            rf.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                rf,
                text=f"● {name}",
                font=ctk.CTkFont(family="Consolas", size=12),
                text_color=self._theme["accent"],
                anchor="w",
            ).grid(row=0, column=0, sticky="w")

            sw = ctk.CTkSwitch(
                rf,
                text="",
                progress_color=self._theme["accent"],
                button_color=self._theme["text_main"],
                height=20,
                width=40,
            )
            sw.select()
            sw.grid(row=0, column=1, sticky="e")
            self._app_items[name] = sw
            self.app_entry.delete(0, "end")

    def _save(self) -> None:
        cfg = load_user_config()
        cfg["language"] = self.lang_cb.get()

        selected_ui_name = self.ui_theme_cb.get()
        cfg["ui_theme"] = self._ui_theme_name_to_key.get(selected_ui_name, "emerald")

        cfg.setdefault("spicetify", {})
        cfg["spicetify"]["theme"] = self.theme_cb.get()
        cfg["spicetify"]["color_scheme"] = self.scheme_cb.get()

        cfg["extensions"] = [name for name, sw in self._ext_items.items() if sw.get()]
        cfg["custom_apps"] = [name for name, sw in self._app_items.items() if sw.get()]

        cfg.setdefault("preprocesses", {})
        cfg["preprocesses"]["disable_sentry"] = bool(self.sw_sentry.get())
        cfg["preprocesses"]["disable_ui_logging"] = bool(self.sw_logging.get())
        cfg["preprocesses"]["remove_rtl_rule"] = bool(self.sw_rtl.get())
        cfg["preprocesses"]["expose_apis"] = bool(self.sw_apis.get())

        cfg.setdefault("options", {})
        cfg["options"]["inject_css"] = bool(self.sw_css.get())
        cfg["options"]["replace_colors"] = bool(self.sw_colors.get())

        save_user_config(cfg)
        if self._on_saved:
            self._on_saved()
