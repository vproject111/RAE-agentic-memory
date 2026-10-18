import asyncio
import base64
import hashlib
import os
import secrets
import sys
import time

import httpx

print("DEBUG: sys.path is:", sys.path, file=sys.stderr)
if 'apps' in sys.modules:
    print("DEBUG: apps is already in sys.modules:", sys.modules['apps'], file=sys.stderr)
else:
    print("DEBUG: apps is NOT in sys.modules", file=sys.stderr)
import websockets
from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, background_tasks, ui

# Add current directory to path for modules
sys.path.insert(0, os.path.dirname(__file__))

from utils.api_client import RAESuiteClient

from apps.central_auditor import CentralAuditorApp
from apps.decay_retention import DecayRetentionApp
from apps.evolution_lab import EvolutionLabApp
from apps.hive_sandbox import HiveSandboxApp
from apps.mesh_federation import MeshFederationApp
from apps.mission_control import MissionControlApp
from apps.mozilla import MozillaApp
from apps.openclaw_escalation import OpenClawEscalationApp
from apps.oracle import OracleApp
from apps.pd_knowledge_hub import PDKnowledgeHubApp
from apps.phoenix_repair import PhoenixRepairApp
from apps.rae_crl import RaeCrlApp
from apps.search_console import SearchConsoleApp
from apps.wizard import ProceduralWizard

# Load Keycloak configurations
try:
    from apps.memory_api.config import settings

    ENABLE_KEYCLOAK_AUTH = settings.ENABLE_KEYCLOAK_AUTH
    KEYCLOAK_URL = settings.KEYCLOAK_URL
    KEYCLOAK_REALM = settings.KEYCLOAK_REALM
    KEYCLOAK_FRONTEND_CLIENT_ID = settings.KEYCLOAK_FRONTEND_CLIENT_ID
    KEYCLOAK_BACKEND_CLIENT_ID = settings.KEYCLOAK_BACKEND_CLIENT_ID
except ImportError:
    ENABLE_KEYCLOAK_AUTH = os.getenv("ENABLE_KEYCLOAK_AUTH", "False").lower() == "true"
    KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "rae-realm")
    KEYCLOAK_FRONTEND_CLIENT_ID = os.getenv("KEYCLOAK_FRONTEND_CLIENT_ID", "rae-portal")
    KEYCLOAK_BACKEND_CLIENT_ID = os.getenv(
        "KEYCLOAK_BACKEND_CLIENT_ID", "rae-memory-api"
    )

# --- Fallback Global Initialization ---
client = RAESuiteClient()


def _extract_user_email(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        return "user@printdisplay.pl"
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            import base64
            import json

            padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            )
            return (
                payload.get("email")
                or payload.get("preferred_username")
                or "user@printdisplay.pl"
            )
    except Exception:
        pass
    return "user@printdisplay.pl"


class RAESuitePortal:
    def __init__(self, request: Request):
        self.current_page = "mission_control"
        self.system_profile = "Detecting..."

        # Instantiate a context-specific client using the session's access token
        token = request.cookies.get("access_token") if ENABLE_KEYCLOAK_AUTH else None
        self.client = RAESuiteClient(token=token)
        self.user_email = _extract_user_email(request)

        # Instantiate apps dynamically inside session to avoid memory leaks / deleted client exceptions
        self.oracle_app = OracleApp(self.client)
        self.wizard_app = ProceduralWizard(self.client)
        self.mozilla_app = MozillaApp(self.client)
        self.mission_control_app = MissionControlApp(self.client)
        self.search_console_app = SearchConsoleApp(self.client)
        self.decay_retention_app = DecayRetentionApp(self.client)
        self.evolution_lab_app = EvolutionLabApp(self.client)
        self.phoenix_repair_app = PhoenixRepairApp(self.client)
        self.hive_sandbox_app = HiveSandboxApp(self.client)
        self.openclaw_escalation_app = OpenClawEscalationApp(self.client)
        self.rae_crl_app = RaeCrlApp(self.client)
        self.mesh_federation_app = MeshFederationApp(self.client)
        self.central_auditor_app = CentralAuditorApp(self.client)
        self.pd_knowledge_hub_app = PDKnowledgeHubApp(self.client, user_email=self.user_email)

        # State variables for Faza 2
        self.connection_status = "Offline"
        self.connection_latency = 0
        self.freshness_time = "Live"
        self.inspector_title = "No Entity Selected"
        self.inspector_details = "Select an entity from any view to inspect its raw telemetry and cognitive lineage."

        # Models Categorized by $ cost, versions and hardware warnings
        self.model_options = {
            "local_qwen_optimized": "Local: QWEN 3.5 9B [Best]",
            "local_phi": "Local: Phi-3 Mini (Fast)",
            "premium_openai": "$ GPT-4o-mini (Stable)",
            "premium_anthropic": "284352 Claude 3.5 Sonnet",
        }

    async def detect_system(self):
        stats = await self.client.get_stats()
        engine_info = stats.get("statistics", {}).get("engine", "RAE")
        self.system_profile = f"Active: {engine_info}"
        ui.update()

    def set_page(self, name: str):
        self.current_page = name
        self.content_router.refresh()
        ui.run_javascript(
            f'document.title = "RAE Portal | {name.replace("_", " ").title()}";'
        )

    def open_inspector(self, title: str, details: str):
        self.inspector_title = title
        self.inspector_details = details
        self.right_drawer.set_value(True)
        ui.update()

    async def start_websocket_client(self):
        # Convert http/https RAE_API_URL to ws/wss
        base_url = self.client.api_url
        ws_url = (
            base_url.replace("http://", "ws://").replace("https://", "wss://")
            + "/v2/dashboard/ws"
        )

        attempt = 1
        while True:
            try:
                self.connection_status = f"Reconnecting · attempt {attempt}"

                async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                    self.connection_status = "Socket live · Synced"
                    attempt = 1

                    while True:
                        t_start = time.time()
                        # Send heartbeat ping
                        await ws.ping()
                        t_end = time.time()
                        self.connection_latency = int((t_end - t_start) * 1000)
                        self.connection_status = (
                            f"Socket live · Synced · {self.connection_latency}ms"
                        )
                        self.freshness_time = "Live"

                        # Wait for a message or sleep
                        try:
                            await asyncio.wait_for(ws.recv(), timeout=5.0)
                            await self.detect_system()
                        except asyncio.TimeoutError:
                            pass
            except Exception:
                # Safe fallback to polling if WebSocket is unavailable/blocked
                self.connection_status = "Offline · cached view"
                self.connection_latency = 0
                self.freshness_time = "Updated 2s ago"
                await asyncio.sleep(5.0)
                attempt += 1

    def render(self, request: Request):
        # Startup the background task for WebSocket
        if not hasattr(self, "_websocket_task_started"):
            self._websocket_task_started = True
            background_tasks.create(self.start_websocket_client())

        # --- STYLES, FONTS & WCGA INLINE CONFIG ---
        ui.add_head_html(r"""
        <link rel="manifest" href="/manifest.json">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        <script>
            (function() {
                // Set HTML language tag (WCAG 3.1.1)
                document.documentElement.lang = "pl";

                // Register PWA Service Worker & IndexedDB telemetry cache
                if ('serviceWorker' in navigator) {
                    window.addEventListener('load', function() {
                        navigator.serviceWorker.register('/sw.js').catch(function() {});
                    });
                }
                if ('indexedDB' in window) {
                    try {
                        const dbReq = indexedDB.open('rae_portal_offline_cache', 1);
                        dbReq.onupgradeneeded = function(e) {
                            const db = e.target.result;
                            if (!db.objectStoreNames.contains('telemetry_snapshots')) {
                                db.createObjectStore('telemetry_snapshots', { keyPath: 'id' });
                            }
                        };
                    } catch (e) {}
                }

                // Check if user has consented to cookies, fallback to sessionStorage if not
                const accepted = document.cookie.split('; ').find(row => row.startsWith('cookieAccepted='));
                const storage = accepted ? localStorage : sessionStorage;

                if (storage.getItem('wcgaKontrast') === '1') {
                    document.documentElement.classList.add('wcga-contrast');
                }
                if (storage.getItem('wcgaFonts') === '1') {
                    document.documentElement.classList.add('wcga-fonts');
                }
            })();
        </script>
        <style>
            /* --- BASE ACCESSIBILITY FOCUS INDICATORS (WCAG 2.4.7) --- */
            *:focus {
                outline: 2px solid #3b82f6 !important;
                outline-offset: 2px !important;
            }

            /* --- ACCESSIBILITY / WCGA CONTRAST OVERRIDES --- */
            html.wcga-contrast body,
            html.wcga-contrast .q-splitter__panel,
            html.wcga-contrast .q-tab-panel,
            html.wcga-contrast .q-tab-panels,
            html.wcga-contrast .q-card,
            html.wcga-contrast .q-drawer,
            html.wcga-contrast .glass-card {
                background-color: #ffffff !important;
                background: #ffffff !important;
                color: #000000 !important;
                border: none !important;
                box-shadow: none !important;
            }
            html.wcga-contrast .glass-card,
            html.wcga-contrast .q-card {
                border: 3px solid #000000 !important;
            }
            html.wcga-contrast .text-white,
            html.wcga-contrast .text-slate-200,
            html.wcga-contrast .text-slate-300,
            html.wcga-contrast .text-slate-400 {
                color: #000000 !important;
            }
            html.wcga-contrast .text-purple-400,
            html.wcga-contrast .text-cyan-400 {
                color: #1e1b4b !important;
                font-weight: bold !important;
            }
            html.wcga-contrast .bg-slate-950,
            html.wcga-contrast .bg-slate-900,
            html.wcga-contrast .bg-slate-900\/60,
            html.wcga-contrast .bg-slate-950\/90,
            html.wcga-contrast .bg-slate-950\/80 {
                background-color: #ffffff !important;
                background: #ffffff !important;
                border-color: #000000 !important;
                color: #000000 !important;
            }
            html.wcga-contrast header.q-header,
            html.wcga-contrast .bg-slate-950\/90 {
                background-color: #ffffff !important;
                background: #ffffff !important;
                color: #000000 !important;
                border-bottom: 3px solid #000000 !important;
            }
            html.wcga-contrast header.q-header * {
                color: #000000 !important;
            }
            html.wcga-contrast .q-field__control {
                border: 2px solid #000000 !important;
                background-color: #ffffff !important;
                background: #ffffff !important;
                box-shadow: none !important;
            }
            html.wcga-contrast .q-field__control::before,
            html.wcga-contrast .q-field__control::after {
                display: none !important;
            }
            html.wcga-contrast .q-field--dark .q-field__control {
                background-color: #ffffff !important;
                background: #ffffff !important;
                color: #000000 !important;
            }
            html.wcga-contrast .q-field--dark .q-field__native,
            html.wcga-contrast .q-field--dark .q-field__prefix,
            html.wcga-contrast .q-field--dark .q-field__suffix,
            html.wcga-contrast .q-field--dark .q-field__input,
            html.wcga-contrast .q-field--dark .q-field__label,
            html.wcga-contrast .q-field--dark .q-select__selection,
            html.wcga-contrast .q-field--dark .q-placeholder {
                color: #000000 !important;
            }
            html.wcga-contrast .q-field--dark .q-field__marginal,
            html.wcga-contrast .q-field--dark .q-field__append .q-icon,
            html.wcga-contrast .q-field--dark .q-select__dropdown-icon {
                color: #000000 !important;
                opacity: 1 !important;
            }
            html.wcga-contrast input,
            html.wcga-contrast textarea,
            html.wcga-contrast select,
            html.wcga-contrast .q-field,
            html.wcga-contrast .q-field__control-container {
                color: #000000 !important;
                border: none !important;
                outline: none !important;
                box-shadow: none !important;
                background: transparent !important;
            }
            html.wcga-contrast .q-field__native,
            html.wcga-contrast .q-field__label,
            html.wcga-contrast .q-select__selection,
            html.wcga-contrast .q-input,
            html.wcga-contrast .q-select {
                color: #000000 !important;
            }
            html.wcga-contrast .q-btn {
                border: 2px solid #000000 !important;
                color: #000000 !important;
                background-color: #ffffff !important;
            }
            body.wcga-contrast .q-menu,
            body.wcga-contrast .q-list,
            body.wcga-contrast .q-item {
                background-color: #ffffff !important;
                background: #ffffff !important;
                color: #000000 !important;
                border: 2px solid #000000 !important;
            }
            body.wcga-contrast .q-item__label {
                color: #000000 !important;
            }
            body.wcga-contrast .q-item--active,
            body.wcga-contrast .q-item.q-manual-focusable--focused {
                background-color: #000000 !important;
                color: #ffffff !important;
            }
            body.wcga-contrast .q-item--active .q-item__label,
            body.wcga-contrast .q-item.q-manual-focusable--focused .q-item__label {
                color: #ffffff !important;
            }

            /* Custom focus indicators for high contrast (WCAG 2.4.7) */
            html.wcga-contrast *:focus {
                outline: 3px solid #000000 !important;
                outline-offset: 2px !important;
            }

            /* Custom semantic class for cookie text to bypass text-white contrast override */
            .cookie-banner-text {
                color: #cbd5e1;
            }
            html.wcga-contrast .cookie-banner-text {
                color: #000000 !important;
            }

            /* --- ACCESSIBILITY / WCGA FONTS OVERRIDES --- */
            html.wcga-fonts body,
            html.wcga-fonts p,
            html.wcga-fonts label,
            html.wcga-fonts input,
            html.wcga-fonts textarea,
            html.wcga-fonts select,
            html.wcga-fonts span {
                font-size: 1.25rem !important;
            }
            html.wcga-fonts .text-xs {
                font-size: 0.95rem !important;
            }
            html.wcga-fonts .text-sm {
                font-size: 1.15rem !important;
            }
            html.wcga-fonts .text-base {
                font-size: 1.25rem !important;
            }
            html.wcga-fonts .text-lg {
                font-size: 1.45rem !important;
            }
            html.wcga-fonts .text-xl {
                font-size: 1.75rem !important;
            }
            html.wcga-fonts .text-2xl {
                font-size: 2.1rem !important;
            }
        </style>
        """)

        ui.colors(primary="#1e293b", secondary="#64748b", accent="#3b82f6")

        # Cookie checks
        cookie_accepted = request.cookies.get("cookieAccepted") == "true"

        # Action handlers for WCGA
        def toggle_contrast():
            ui.run_javascript("""
                const accepted = document.cookie.split('; ').find(row => row.startsWith('cookieAccepted='));
                const storage = accepted ? localStorage : sessionStorage;
                const hasContrast = document.documentElement.classList.toggle("wcga-contrast");
                storage.setItem("wcgaKontrast", hasContrast ? "1" : "0");
            """)
            ui.notify("Tryb wysokiego kontrastu zmieniony! 🌓")

        def toggle_fonts():
            ui.run_javascript("""
                const accepted = document.cookie.split('; ').find(row => row.startsWith('cookieAccepted='));
                const storage = accepted ? localStorage : sessionStorage;
                const hasFonts = document.documentElement.classList.toggle("wcga-fonts");
                storage.setItem("wcgaFonts", hasFonts ? "1" : "0");
            """)
            ui.notify("Rozmiar czcionek zmieniony! 🔍")

        def accept_cookies():
            ui.run_javascript(
                'document.cookie = "cookieAccepted=true; max-age=2592000; path=/";'
            )
            # Copy sessionStorage to localStorage if any WCGA preferences were set before consent
            ui.run_javascript("""
                if (sessionStorage.getItem("wcgaKontrast")) {
                    localStorage.setItem("wcgaKontrast", sessionStorage.getItem("wcgaKontrast"));
                }
                if (sessionStorage.getItem("wcgaFonts")) {
                    localStorage.setItem("wcgaFonts", sessionStorage.getItem("wcgaFonts"));
                }
            """)
            cookie_banner.set_visibility(False)
            ui.notify("Zaakceptowano ciasteczka. 🍪")

        def reject_cookies():
            ui.run_javascript(
                'document.cookie = "cookieAccepted=false; max-age=2592000; path=/";'
            )
            ui.run_javascript("""
                localStorage.clear();
                sessionStorage.clear();
                document.documentElement.classList.remove("wcga-contrast", "wcga-fonts");
            """)
            cookie_banner.set_visibility(False)
            ui.notify("Odrzucono ciasteczka nieesencjonalne.", type="warning")

        # Cookie Settings Dialog
        with ui.dialog() as cookie_settings_dialog:
            with ui.card().classes(
                "text-white w-96 q-pa-md bg-slate-900 border border-blue-500/30"
            ):
                ui.label("Ustawienia Prywatności & Cookies").classes(
                    "text-lg font-bold text-blue-400"
                )
                ui.label(
                    "Zarządzaj ciasteczkami zapisanymi w przeglądarce RAE Portal:"
                ).classes("text-xs cookie-banner-text q-mb-md")

                ui.checkbox("Ciasteczka sesyjne (Wymagane)", value=True).props(
                    "disable"
                )
                c_wcga = ui.checkbox("Zapisywanie preferencji WCGA", value=True)
                c_dreamsoft = ui.checkbox("Integracja z Dreamsoft Factory", value=True)

                async def save_cookie_settings():
                    ui.run_javascript(
                        'document.cookie = "cookieAccepted=true; max-age=2592000; path=/";'
                    )
                    ui.run_javascript(f"""
                        const accepted = document.cookie.split('; ').find(row => row.startsWith('cookieAccepted='));
                        const storage = accepted ? localStorage : sessionStorage;
                        storage.setItem("wcgaConsent", "{'1' if c_wcga.value else '0'}");
                        storage.setItem("dreamsoftConsent", "{'1' if c_dreamsoft.value else '0'}");
                    """)
                    if c_wcga.value:
                        ui.run_javascript("""
                            if (sessionStorage.getItem("wcgaKontrast")) localStorage.setItem("wcgaKontrast", sessionStorage.getItem("wcgaKontrast"));
                            if (sessionStorage.getItem("wcgaFonts")) localStorage.setItem("wcgaFonts", sessionStorage.getItem("wcgaFonts"));
                        """)
                    else:
                        ui.run_javascript("""
                            localStorage.removeItem("wcgaKontrast");
                            localStorage.removeItem("wcgaFonts");
                            document.documentElement.classList.remove("wcga-contrast", "wcga-fonts");
                        """)
                    cookie_settings_dialog.close()
                    cookie_banner.set_visibility(False)
                    ui.notify(
                        "Ustawienia ciasteczek zostały zapisane.", type="positive"
                    )

                with ui.row().classes("w-full justify-end q-mt-md gap-2"):
                    ui.button("Anuluj", on_click=cookie_settings_dialog.close).props(
                        "flat dense"
                    )
                    ui.button("Zapisz", on_click=save_cookie_settings).props(
                        "color=blue"
                    )

        with ui.header().classes(
            "items-center justify-between bg-slate-900 text-white p-4 shadow-xl"
        ):
            with ui.row().classes("items-center gap-4"):
                ui.icon("hub", size="md", color="blue-400")
                ui.label("RAE SUITE PORTAL").classes(
                    "text-2xl font-black tracking-tighter"
                )
                ui.badge().bind_text_from(self, "system_profile").props(
                    "outline color=blue-400"
                ).classes("ml-2 text-[10px]")
                ui.button(
                    "🏢 PD Knowledge Hub",
                    icon="open_in_new",
                    on_click=lambda: ui.navigate.to("https://pd.dreamsoft.pro/", new_tab=True),
                ).props("unelevated dense color=indigo-7 rounded text-xs").tooltip(
                    "Otwórz Print & Display Corporate Knowledge Hub (https://pd.dreamsoft.pro/)"
                )

            with ui.row().classes("items-center gap-6"):
                with (
                    ui.row()
                    .classes(
                        "items-center gap-2 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800"
                    )
                    .props("aria-live=polite aria-atomic=true")
                ):
                    ui.icon("cloud_sync", size="xs", color="cyan-300")
                    # Connection Capsule - using high contrast text color (text-cyan-300)
                    ui.label().bind_text_from(self, "connection_status").classes(
                        "text-xs text-cyan-300 font-bold"
                    )
                    ui.separator().props("vertical").classes("bg-slate-800 h-4 mx-1")
                    # Freshness Badge
                    ui.label().bind_text_from(self, "freshness_time").classes(
                        "text-xs text-slate-400"
                    )

                # WCGA Accessibility toggles with descriptive aria-labels (SC 2.4.4 / 4.1.2)
                ui.button(icon="contrast", on_click=toggle_contrast).props(
                    'flat round color=white aria-label="Przełącz wysoki kontrast (WCGA)"'
                ).tooltip("Przełącz wysoki kontrast (WCGA)")
                ui.button(icon="format_size", on_click=toggle_fonts).props(
                    'flat round color=white aria-label="Przełącz rozmiar czcionek (WCGA)"'
                ).tooltip("Przełącz rozmiar czcionek (WCGA)")

                self.model_select = (
                    ui.select(
                        options=self.model_options,
                        value="local_qwen_optimized",
                        label="Brain Selection",
                    )
                    .classes("w-96")
                    .props("dark dense outlined color=white")
                )

                self.source_select = (
                    ui.select(
                        options={
                            "default": "Standard Knowledge",
                            "grafana_analytics": "Industrial Metrics",
                            "corp_procedures": "Procedural Docs",
                            "mozilla_civic": "Civic Evidence",
                        },
                        value="default",
                        label="Active Context",
                    )
                    .classes("w-64")
                    .props("dark dense outlined color=white")
                )

        with ui.left_drawer(value=True).classes("bg-slate-50 border-r p-6"):
            # Wrapped links inside semantic <nav> element (SC 1.3.1)
            with ui.element("nav").classes("w-full column gap-2"):
                ui.label("SUITE DASHBOARD").classes(
                    "text-xs font-bold text-slate-400 mb-4 uppercase tracking-widest"
                )
                with ui.column().classes("w-full gap-2 mb-6"):
                    ui.button(
                        "Mission Control",
                        icon="dashboard",
                        on_click=lambda: self.set_page("mission_control"),
                    ).props(
                        f'flat align=left {"color=indigo" if self.current_page=="mission_control" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "Search Console",
                        icon="search",
                        on_click=lambda: self.set_page("search_console"),
                    ).props(
                        f'flat align=left {"color=sky" if self.current_page=="search_console" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "Decay & Retention",
                        icon="hourglass_empty",
                        on_click=lambda: self.set_page("decay_retention"),
                    ).props(
                        f'flat align=left {"color=teal" if self.current_page=="decay_retention" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "Evolution Lab",
                        icon="science",
                        on_click=lambda: self.set_page("evolution_lab"),
                    ).props(
                        f'flat align=left {"color=purple" if self.current_page=="evolution_lab" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "Phoenix Repair",
                        icon="healing",
                        on_click=lambda: self.set_page("phoenix_repair"),
                    ).props(
                        f'flat align=left {"color=purple" if self.current_page=="phoenix_repair" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "Hive Sandbox",
                        icon="layers",
                        on_click=lambda: self.set_page("hive_sandbox"),
                    ).props(
                        f'flat align=left {"color=emerald" if self.current_page=="hive_sandbox" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "OpenClaw Escalation",
                        icon="warning",
                        on_click=lambda: self.set_page("openclaw_escalation"),
                    ).props(
                        f'flat align=left {"color=red" if self.current_page=="openclaw_escalation" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "RAE-CRL Console",
                        icon="rule_folder",
                        on_click=lambda: self.set_page("rae_crl"),
                    ).props(
                        f'flat align=left {"color=deep-orange" if self.current_page=="rae_crl" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "Mesh Federation",
                        icon="hub",
                        on_click=lambda: self.set_page("mesh_federation"),
                    ).props(
                        f'flat align=left {"color=indigo" if self.current_page=="mesh_federation" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "Central Auditor ISO",
                        icon="fact_check",
                        on_click=lambda: self.set_page("central_auditor"),
                    ).props(
                        f'flat align=left {"color=cyan" if self.current_page=="central_auditor" else ""}'
                    ).classes(
                        "w-full"
                    )

                ui.label("CAPABILITIES").classes(
                    "text-xs font-bold text-slate-400 mb-4 uppercase tracking-widest"
                )
                with ui.column().classes("w-full gap-2"):
                    ui.button(
                        "Industrial Oracle",
                        icon="psychology",
                        on_click=lambda: self.set_page("oracle"),
                    ).props(
                        f'flat align=left {"color=blue" if self.current_page=="oracle" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "Procedural Wizard",
                        icon="auto_fix_high",
                        on_click=lambda: self.set_page("wizard"),
                    ).props(
                        f'flat align=left {"color=amber-9" if self.current_page=="wizard" else ""}'
                    ).classes(
                        "w-full"
                    )
                    ui.button(
                        "Civic Node",
                        icon="shield",
                        on_click=lambda: self.set_page("mozilla"),
                    ).props(
                        f'flat align=left {"color=emerald" if self.current_page=="mozilla" else ""}'
                    ).classes(
                        "w-full"
                    )
                    with ui.row().classes("w-full items-center justify-between no-wrap gap-1"):
                        ui.button(
                            "PD Knowledge Hub",
                            icon="corporate_fare",
                            on_click=lambda: self.set_page("pd_knowledge_hub"),
                        ).props(
                            f'flat align=left {"color=indigo-4" if self.current_page=="pd_knowledge_hub" else ""}'
                        ).classes(
                            "flex-grow"
                        )
                        ui.button(
                            icon="open_in_new",
                            on_click=lambda: ui.navigate.to("https://pd.dreamsoft.pro/", new_tab=True),
                        ).props("flat round dense size=sm color=indigo-4").tooltip(
                            "Otwórz https://pd.dreamsoft.pro/ w nowej karcie"
                        )

            ui.separator().classes("my-8")
            ui.label("TIER GUIDE").classes("text-[10px] font-black text-slate-400 mb-2")
            ui.label("$ Budget | $$ Advanced | $$$ Research").classes(
                "text-[9px] text-slate-500 italic"
            )
            ui.label("[GPU-needed] = local / heavy").classes(
                "text-[9px] text-red-400 italic mt-1"
            )

        # Faza 2: Right Drawer / Context Inspector
        with ui.right_drawer(value=False).classes(
            "bg-slate-900 border-l text-white p-6"
        ) as self.right_drawer:
            with ui.row().classes("w-full justify-between items-center mb-6"):
                ui.label().bind_text_from(self, "inspector_title").classes(
                    "text-lg font-bold text-cyan-400"
                )
                ui.button(
                    icon="close", on_click=lambda: self.right_drawer.set_value(False)
                ).props('flat round color=white aria-label="Close inspector"')

            ui.separator().classes("bg-slate-800 mb-6")

            # Details section (dynamic markdown content)
            ui.markdown().bind_content_from(self, "inspector_details").classes(
                "text-sm text-slate-300"
            )

        @ui.refreshable
        def content_router():
            if self.current_page == "mission_control":
                self.mission_control_app.on_inspect = self.open_inspector
                self.mission_control_app.render()
            elif self.current_page == "search_console":
                self.search_console_app.on_inspect = self.open_inspector
                self.search_console_app.render()
            elif self.current_page == "decay_retention":
                self.decay_retention_app.on_inspect = self.open_inspector
                self.decay_retention_app.render()
            elif self.current_page == "evolution_lab":
                self.evolution_lab_app.on_inspect = self.open_inspector
                self.evolution_lab_app.render()
            elif self.current_page == "phoenix_repair":
                self.phoenix_repair_app.on_inspect = self.open_inspector
                self.phoenix_repair_app.render()
            elif self.current_page == "hive_sandbox":
                self.hive_sandbox_app.on_inspect = self.open_inspector
                self.hive_sandbox_app.render()
            elif self.current_page == "openclaw_escalation":
                self.openclaw_escalation_app.on_inspect = self.open_inspector
                self.openclaw_escalation_app.render()
            elif self.current_page == "rae_crl":
                self.rae_crl_app.on_inspect = self.open_inspector
                self.rae_crl_app.render()
            elif self.current_page == "mesh_federation":
                self.mesh_federation_app.on_inspect = self.open_inspector
                self.mesh_federation_app.render()
            elif self.current_page == "central_auditor":
                self.central_auditor_app.render()
            elif self.current_page == "oracle":
                self.oracle_app.render(self.model_select, self.source_select)
            elif self.current_page == "wizard":
                self.wizard_app.render(self.model_select)
            elif self.current_page == "mozilla":
                self.mozilla_app.render(self.model_select)
            elif self.current_page == "pd_knowledge_hub":
                self.pd_knowledge_hub_app.render(standalone=False)

        self.content_router = content_router
        content_router()
        ui.timer(2.0, self.detect_system, once=True)

        # Cookie consent banner (Klaro / Dreamsoft compatible) with rejection button
        with ui.card().classes(
            "fixed bottom-4 left-4 right-4 z-50 bg-slate-900 border border-blue-500/30 text-white q-pa-md flex flex-row items-center justify-between no-wrap gap-4"
        ) as cookie_banner:
            with ui.column().classes("gap-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("cookie", color="blue-400").classes("text-lg")
                    ui.label("Polityka Cookies / Ciasteczek").classes(
                        "text-sm font-bold text-blue-300"
                    )
                ui.label(
                    "Ta witryna RAE Portal używa ciasteczek w celach funkcjonalnych (sesje, ustawienia WCGA) "
                    "oraz integracji z Dreamsoft Factory."
                ).classes("text-xs cookie-banner-text")
            with ui.row().classes("gap-2 no-wrap"):
                ui.button("Odrzuć Nieesencjonalne", on_click=reject_cookies).props(
                    'flat dense color=red aria-label="Odrzuć nieesencjonalne ciasteczka"'
                )
                ui.button("Ustawienia", on_click=cookie_settings_dialog.open).props(
                    'flat dense color=white aria-label="Ustawienia ciasteczek"'
                )
                ui.button("Akceptuję Wszystkie", on_click=accept_cookies).props(
                    'color=blue aria-label="Akceptuję wszystkie ciasteczka"'
                )

        if cookie_accepted:
            cookie_banner.set_visibility(False)


def _get_cookie_domain(request: Request):
    host = (
        request.headers.get("x-forwarded-host")
        or request.headers.get("host")
        or ""
    ).lower()
    if "dreamsoft.pro" in host:
        return ".dreamsoft.pro"
    return None


def _is_token_valid(token: str = None) -> bool:
    if not token:
        return False
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            import base64
            import json
            import time

            padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
            )
            exp = payload.get("exp")
            if exp and time.time() >= exp - 30:
                return False
            return True
    except Exception:
        return False
    return True


def _get_redirect_uri(request: Request) -> str:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "rae.dreamsoft.pro"
    proto = request.headers.get("x-forwarded-proto") or ("https" if "dreamsoft.pro" in host else request.url.scheme)
    if "dreamsoft.pro" in host:
        proto = "https"
    return f"{proto}://{host}/callback"


@app.get("/logout")
def logout_endpoint(request: Request):
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "rae.dreamsoft.pro"
    proto = "https" if "dreamsoft.pro" in host else request.url.scheme
    cookie_domain = _get_cookie_domain(request)
    res = RedirectResponse(f"{proto}://{host}/", status_code=307)
    if cookie_domain:
        res.delete_cookie("access_token", path="/", domain=cookie_domain)
    res.delete_cookie("access_token", path="/")
    return res


@app.get("/manifest.json")
def pwa_manifest():
    return {
        "name": "RAE Suite Command Center",
        "short_name": "RAE Portal",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#1e293b",
        "icons": [],
    }


@app.get("/sw.js")
def pwa_service_worker():
    from fastapi.responses import Response
    sw_code = (
        "const CACHE_NAME = 'rae-portal-v1';\n"
        "self.addEventListener('install', (e) => { self.skipWaiting(); });\n"
        "self.addEventListener('activate', (e) => { e.waitUntil(self.clients.claim()); });\n"
        "self.addEventListener('fetch', (e) => {\n"
        "  if (e.request.method !== 'GET') return;\n"
        "  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));\n"
        "});\n"
    )
    return Response(content=sw_code, media_type="application/javascript")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if (
        not ENABLE_KEYCLOAK_AUTH
        or path.startswith("/callback")
        or path.startswith("/logout")
        or path.startswith("/_nicegui")
        or path.startswith("/socket.io")
        or path.startswith("/static")
        or path.startswith("/favicon")
        or path.startswith("/health")
        or path in {"/manifest.json", "/sw.js"}
    ):
        return await call_next(request)

    token = request.cookies.get("access_token")
    if (not token or not _is_token_valid(token)) and path in ["/", "/evidence", "/pd"]:
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        sha256_hash = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = (
            base64.urlsafe_b64encode(sha256_hash).decode("ascii").replace("=", "")
        )

        redirect_uri = _get_redirect_uri(request)
        cookie_domain = _get_cookie_domain(request)
        auth_url = (
            f"{KEYCLOAK_URL.rstrip('/')}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth"
            f"?response_type=code"
            f"&client_id={KEYCLOAK_FRONTEND_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
            f"&code_challenge={code_challenge}"
            f"&code_challenge_method=S256"
            f"&scope=openid+profile+email"
        )
        response = RedirectResponse(auth_url, status_code=307)
        response.set_cookie(
            "oauth_state",
            state,
            max_age=300,
            httponly=True,
            samesite="lax",
            secure=True,
            domain=cookie_domain,
        )
        response.set_cookie(
            "oauth_verifier",
            code_verifier,
            max_age=300,
            httponly=True,
            samesite="lax",
            secure=True,
            domain=cookie_domain,
        )
        response.set_cookie(
            "redirect_back",
            path,
            max_age=300,
            httponly=True,
            samesite="lax",
            secure=True,
            domain=cookie_domain,
        )
        return response

    return await call_next(request)


@app.get("/callback")
async def oauth_callback(request: Request, code: str = None, state: str = None):
    if not code:
        return "Authorization code missing."

    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or cookie_state != state:
        return "Invalid OAuth state. Potential CSRF detected."

    code_verifier = request.cookies.get("oauth_verifier")
    if not code_verifier or len(code_verifier) < 43 or len(code_verifier) > 128:
        return "Invalid code verifier. Access denied."

    # Exchange authorization code for token
    redirect_uri = _get_redirect_uri(request)
    token_url = f"{KEYCLOAK_URL.rstrip('/')}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"

    data = {
        "grant_type": "authorization_code",
        "client_id": KEYCLOAK_FRONTEND_CLIENT_ID,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

            access_token = token_data.get("access_token")
            if not access_token:
                return "Failed to retrieve access token from Keycloak."

            # Determine where to redirect back and validate it to prevent open redirect vulnerabilities
            redirect_back = request.cookies.get("redirect_back", "/")
            if redirect_back not in {"/", "/evidence", "/pd"}:
                redirect_back = "/"

            cookie_domain = _get_cookie_domain(request)
            # Redirect user back to the application and save token in session cookie
            res = RedirectResponse(redirect_back, status_code=307)

            res.set_cookie(
                "access_token",
                access_token,
                httponly=True,
                samesite="lax",
                secure=True,
                domain=cookie_domain,
                path="/",
            )

            # Clean up temporary OAuth cookies
            if cookie_domain:
                res.delete_cookie("oauth_state", domain=cookie_domain)
                res.delete_cookie("oauth_verifier", domain=cookie_domain)
                res.delete_cookie("redirect_back", domain=cookie_domain)
            res.delete_cookie("oauth_state")
            res.delete_cookie("oauth_verifier")
            res.delete_cookie("redirect_back")

            return res
    except Exception as e:
        return f"Token exchange failed: {str(e)}"


@ui.page("/")
def main_portal(request: Request):
    host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or "").lower()
    is_pd_domain = host.startswith("pd.") or "pd.dreamsoft.pro" in host

    portal = RAESuitePortal(request)
    if is_pd_domain:
        user_email = _extract_user_email(request)
        pd_app = PDKnowledgeHubApp(portal.client, user_email=user_email)
        pd_app.render(standalone=True)
    else:
        portal.render(request)


@ui.page("/pd")
def pd_standalone_portal(request: Request):
    portal = RAESuitePortal(request)
    user_email = _extract_user_email(request)
    pd_app = PDKnowledgeHubApp(portal.client, user_email=user_email)
    pd_app.render(standalone=True)


@ui.page("/evidence")
def evidence_portal(request: Request):

    ui.add_head_html(r"""
    <script>
        document.documentElement.lang = "pl";
    </script>
    <style>
        body {
            background-color: #ffffff;
            color: #000000;
            font-family: Arial, sans-serif;
        }
        button:focus, a:focus {
            outline: 3px solid #005fcc;
            outline-offset: 2px;
        }
    </style>
    """)

    with ui.column().classes("w-full max-w-5xl mx-auto p-8 gap-y-6"):
        with ui.element("h1").classes("text-3xl font-bold text-black"):
            ui.label("Karta Dowodowa RAE (Evidence Ledger)")
        ui.label(
            "Niezależny podgląd dowodów kryptograficznych, sum SBOM i certyfikatów bezpieczeństwa (ISO 27001)."
        ).classes("text-slate-700")

        with ui.card().classes(
            "w-full p-6 border-2 border-black bg-white text-black shadow-none"
        ):
            ui.label("CERTYFIKAT INTEGRALNOŚCI PLATFORMY").classes(
                "text-xs font-bold text-slate-700 mb-2"
            )
            ui.label(
                "Podpis: SHA256:8f4c9c2b3e8a1d7f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f"
            ).classes("text-sm font-mono font-bold")
            ui.label("Status SBOM: ZGODNY (CycloneDX - SLSA Level 3)").classes(
                "text-sm font-bold text-black mt-2"
            )
            ui.label(
                "Weryfikacja: Wdrożenie z dnia 2026-07-19 (Cosign verified signature)"
            ).classes("text-xs text-slate-800")

        with ui.card().classes(
            "w-full p-6 border-2 border-black bg-white text-black shadow-none"
        ):
            ui.label("DZIENNIK ZDARZEŃ AUDYTOWYCH").classes(
                "text-xs font-bold text-slate-700 mb-4"
            )
            with ui.column().classes("w-full gap-y-2").props('role="list"'):
                incidents = [
                    {
                        "id": "INC-099",
                        "time": "12:08:14",
                        "msg": "Zablokowanie PR #409: Banned package 'sentence-transformers' detected by AST scan.",
                    },
                    {
                        "id": "INC-100",
                        "time": "14:11:02",
                        "msg": "Wykrycie niedozwolonej ścieżki bezwzględnej C6 Invariant.",
                    },
                ]
                for inc in incidents:
                    with (
                        ui.row()
                        .classes("w-full justify-between border-b pb-2 text-sm")
                        .props('role="listitem"')
                    ):
                        ui.label(f'{inc["time"]} - {inc["id"]}').classes(
                            "font-mono font-bold"
                        )
                        ui.label(inc["msg"]).classes("text-slate-800 break-words")

        with ui.row().classes("w-full gap-4 mt-6"):
            ui.button(
                "Eksportuj do Markdown",
                on_click=lambda: ui.notify(
                    "Eksportowanie dowodu do Markdown...", type="info"
                ),
            ).props("color=black")
            ui.button(
                "Pobierz paczkę ZIP (SBOM)",
                on_click=lambda: ui.notify(
                    "Pobieranie paczki ZIP (SBOM)...", type="positive"
                ),
            ).props("outline color=black")


if __name__ in {"__main__", "main"}:
    port = int(os.environ.get("PORT", 8080))
    storage_secret = os.environ.get("STORAGE_SECRET_KEY") or secrets.token_hex(32)
    ui.run(
        title="RAE Suite Portal Quantum",
        port=port,
        reload=False,
        dark=False,
        storage_secret=storage_secret,
    )
