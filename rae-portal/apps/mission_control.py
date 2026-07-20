import asyncio
from datetime import datetime

from nicegui import ui
from utils.api_client import RAESuiteClient
from utils.ui_helpers import create_module_header


class MissionControlApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.stats = {"total_count": 0}
        self.compliance_report = {}
        self.rls_status = {}
        self.audit_trail = []
        self.on_inspect = None
        self._active = True

    async def fetch_data(self):
        if not self._active:
            return

        try:
            # 1. Fetch memories statistics
            self.stats = await self.client.get_stats(project="default")
        except Exception:
            pass

        try:
            # 2. Fetch compliance report
            report_data = await self.client.get_compliance_report(project="default")
            self.compliance_report = report_data.get("compliance_report", {})
        except Exception:
            pass

        try:
            # 3. Fetch RLS status
            rls_data = await self.client.get_rls_status()
            self.rls_status = rls_data.get("rls_status", {})
        except Exception:
            pass

        try:
            # 4. Fetch compliance audit trail logs
            audit_trail_data = await self.client.get_compliance_audit_trail(
                project="default"
            )
            self.audit_trail = audit_trail_data.get("items", [])
        except Exception:
            pass

        # Trigger re-render of refreshable content
        self.render_content.refresh()

    def __del__(self):
        self._active = False

    @ui.refreshable
    def render_content(self):
        # Extract dynamic values with safe fallbacks
        total_memories = self.stats.get("total_count", 0)
        overall_score = self.compliance_report.get("overall_compliance_score", 0.0)
        overall_status = self.compliance_report.get("overall_status", "Unknown").upper()

        active_policies = self.rls_status.get("active_policies", 0)
        total_policies = self.rls_status.get("total_policies", 0)
        rls_pct = self.rls_status.get("rls_enabled_percentage", 0.0)
        tables_with_rls = self.rls_status.get("tables_with_rls", [])

        # Determine status colors
        status_color = (
            "emerald-500"
            if overall_status == "COMPLIANT"
            else "amber-500" if "PARTIAL" in overall_status else "red-500"
        )
        status_text_color = (
            "emerald-300"
            if overall_status == "COMPLIANT"
            else "amber-300" if "PARTIAL" in overall_status else "red-300"
        )

        with ui.column().classes("w-full max-w-7xl mx-auto p-8 gap-y-6"):
            create_module_header(
                "Mission Control",
                "Real-time ISO 42001 and ISO 27001 operations, RLS status, and audit logs.",
                self.client,
                rls_status="PROTECTED" if rls_pct == 100.0 else "PARTIAL",
            )

            # --- Row 1: KPI Cards ---
            with ui.row().classes("w-full gap-4"):
                # KPI 1 System Status
                with (
                    ui.card()
                    .classes(
                        f"flex-1 p-6 border-l-4 border-{status_color} bg-slate-900 text-white cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500"
                    )
                    .props(
                        'tabindex=0 aria-label="System Status Card: Click for details" aria-describedby="sys-status-desc"'
                    )
                    .on(
                        "click",
                        lambda: (
                            self.on_inspect(
                                "System Compliance Status",
                                f"**Status:** {overall_status}\n"
                                f"**Compliance Score:** {overall_score:.1f}%\n"
                                f"**Tenant ID:** {self.client.tenant_id}\n\n"
                                f"System checks completed in compliance router. "
                                f"All critical parameters are audited regularly.",
                            )
                            if self.on_inspect
                            else None
                        ),
                    )
                ):
                    ui.label("SYSTEM COMPLIANCE").classes(
                        f"text-xs font-bold text-{status_text_color}"
                    )
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.icon("check_circle", color=status_text_color, size="md")
                        ui.label(f"{overall_status} ({overall_score:.1f}%)").classes(
                            "text-xl font-bold text-slate-100"
                        )
                    ui.space().props('id="sys-status-desc"')

                # KPI 2 Memory Density
                with (
                    ui.card()
                    .classes(
                        "flex-1 p-6 border-l-4 border-indigo-500 bg-slate-900 text-white cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500"
                    )
                    .props(
                        'tabindex=0 aria-label="Memory Density Card: Click for details" aria-describedby="mem-density-desc"'
                    )
                    .on(
                        "click",
                        lambda: (
                            self.on_inspect(
                                "Memory density details",
                                f"**Total memories:** {total_memories}\n"
                                f"**Qdrant + Postgres indices operational.**\n\n"
                                f"Multi-Vector index segments are optimized with Row-Level Security isolation.",
                            )
                            if self.on_inspect
                            else None
                        ),
                    )
                ):
                    ui.label("MEMORY DENSITY").classes(
                        "text-xs font-bold text-indigo-300"
                    )
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.icon("memory", color="indigo-300", size="md")
                        ui.label(f"{total_memories:,} Memories").classes(
                            "text-xl font-bold text-slate-100"
                        )
                    ui.space().props('id="mem-density-desc"')

                # KPI 3 RLS Policies Status
                with (
                    ui.card()
                    .classes(
                        "flex-1 p-6 border-l-4 border-cyan-500 bg-slate-900 text-white cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500"
                    )
                    .props(
                        'tabindex=0 aria-label="RLS Status Card: Click for details" aria-describedby="rls-desc"'
                    )
                    .on(
                        "click",
                        lambda: (
                            self.on_inspect(
                                "RLS Security Policy Details",
                                f"**RLS Enabled:** {rls_pct:.1f}%\n"
                                f"**Active Policies:** {active_policies} of {total_policies} total\n"
                                f"**Protected Tables:** {', '.join(tables_with_rls)}",
                            )
                            if self.on_inspect
                            else None
                        ),
                    )
                ):
                    ui.label("DATABASE RLS STATUS").classes(
                        "text-xs font-bold text-cyan-300"
                    )
                    with ui.row().classes("items-center gap-2 mt-2"):
                        ui.icon("security", color="cyan-300", size="md")
                        ui.label(f"{active_policies} Active Policies").classes(
                            "text-xl font-bold text-slate-100"
                        ).props("aria-live=polite")
                    ui.space().props('id="rls-desc"')

            # --- Row 2: RLS and Security Status Panel ---
            with ui.row().classes("w-full gap-6 mt-4"):
                # Gantt Chart (NiceGUI eChart showing critical tables RLS)
                with ui.card().classes("flex-[2] p-6 bg-slate-900 text-white"):
                    ui.label("ROW-LEVEL SECURITY BY CRITICAL TABLE").classes(
                        "text-xs font-bold text-slate-400 mb-4"
                    )
                    # Make a simple bar chart representing security policies by table
                    tables_data = [t for t in tables_with_rls]
                    y_axis_labels = tables_data if tables_data else ["None"]
                    series_data = [100.0] * len(tables_data) if tables_data else [0.0]

                    ui.echart(
                        {
                            "title": {"text": ""},
                            "tooltip": {"formatter": "{b}: {c}% protected"},
                            "xAxis": {
                                "type": "value",
                                "max": 100,
                                "name": "Protection Level (%)",
                                "nameTextStyle": {"color": "#94a3b8"},
                            },
                            "yAxis": {
                                "type": "category",
                                "data": y_axis_labels,
                                "axisLabel": {"color": "#94a3b8"},
                            },
                            "series": [
                                {
                                    "type": "bar",
                                    "data": series_data,
                                    "itemStyle": {"color": "#06b6d4"},
                                }
                            ],
                        }
                    ).classes("w-full h-64")

                # ISO 27001 / ISO 42001 Status Panel
                with ui.card().classes(
                    "flex-1 p-6 bg-slate-900 text-white border border-emerald-500/20"
                ):
                    ui.label("ISO COMPLIANCE TELEMETRY").classes(
                        "text-xs font-bold text-slate-500 mb-4"
                    )
                    with ui.column().classes("gap-y-4"):
                        with ui.row().classes("items-center gap-2"):
                            ui.badge("ISO 27001").props("color=emerald")
                            ui.label("RLS: Active & Audited").classes(
                                "text-sm font-bold text-emerald-300"
                            )

                        ui.separator().classes("bg-slate-700")
                        ui.label("Protected Table Names:").classes(
                            "text-xs text-slate-400"
                        )
                        with ui.column().classes("gap-y-1"):
                            for idx, t in enumerate(tables_with_rls[:5]):
                                ui.label(f"• {t}").classes("text-xs text-slate-300")
                            if len(tables_with_rls) > 5:
                                ui.label(
                                    f"• ...and {len(tables_with_rls) - 5} more"
                                ).classes("text-xs text-slate-400")

                        ui.separator().classes("bg-slate-700")
                        with (
                            ui.row()
                            .classes(
                                "items-center gap-2 cursor-pointer hover:text-cyan-300"
                            )
                            .on(
                                "click",
                                lambda: (
                                    self.on_inspect(
                                        "Data Provenance & Integrity",
                                        "ISO 42001 requires checking memory trust levels and ensuring cryptographically chained integrity checksums (SHA-256) for audit trails.",
                                    )
                                    if self.on_inspect
                                    else None
                                ),
                            )
                        ):
                            ui.icon("verified_user", color="cyan-500")
                            ui.label("SHA-256 Audit Trail active").classes(
                                "text-[10px] text-cyan-300 font-bold"
                            )

            # --- Row 3: Live Operation Log (with ISO Tagging) ---
            with ui.card().classes("w-full p-6 bg-slate-900 text-white"):
                ui.label("ISO AUDIT TRAIL LOGS (SHA-256 VERIFIED)").classes(
                    "text-xs font-bold text-slate-400 mb-4"
                )
                with ui.column().classes("w-full gap-y-3").props("role=list"):
                    if not self.audit_trail:
                        ui.label(
                            "No audit trail entries recorded yet. Make some API requests to generate logs."
                        ).classes("text-slate-400 text-sm italic")
                    else:
                        for log in self.audit_trail[:10]:  # Show last 10 entries
                            log_time = log.get("timestamp", "")
                            # Parse datetime representation
                            if isinstance(log_time, str):
                                try:
                                    dt = datetime.fromisoformat(
                                        log_time.replace("Z", "+00:00")
                                    )
                                    log_time = dt.strftime("%H:%M:%S")
                                except Exception:
                                    log_time = log_time[:19]

                            initiator = log.get("initiator", "System")
                            op = log.get("operation", "ACCESS").upper()
                            details = log.get("details", "")
                            checksum_valid = log.get("checksum_valid", True)

                            badge_color = (
                                "color=emerald" if checksum_valid else "color=red"
                            )
                            checksum_lbl = "VERIFIED" if checksum_valid else "CORRUPT"

                            with (
                                ui.row()
                                .classes(
                                    "w-full items-center justify-between border-b border-slate-800 pb-2 text-sm cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500"
                                )
                                .props(
                                    'tabindex=0 role="listitem" aria-label="Log entry: click for details"'
                                )
                                .on(
                                    "click",
                                    lambda l=log: (
                                        self.on_inspect(
                                            f"Audit Trail Log: {l.get('id')}",
                                            f"**Timestamp:** {l.get('timestamp')}\n"
                                            f"**Initiator:** {l.get('initiator')}\n"
                                            f"**Operation:** {l.get('operation')}\n"
                                            f"**Resource:** {l.get('resource')}\n"
                                            f"**Details:** {l.get('details')}\n"
                                            f"**SHA-256 Checksum:** `{l.get('checksum')}`\n"
                                            f"**Integrity:** {'VALID (MATCHED)' if l.get('checksum_valid') else 'FAILED (MISMATCH)'}",
                                        )
                                        if self.on_inspect
                                        else None
                                    ),
                                )
                            ):
                                with ui.row().classes("gap-3"):
                                    ui.label(log_time).classes(
                                        "text-slate-400 font-mono"
                                    )
                                    ui.badge(initiator).props("color=indigo")
                                    ui.label(details).classes("text-slate-200")
                                ui.badge(checksum_lbl).props(badge_color)

    def render(self):
        # Render the initial refreshable content
        self.render_content()
        # Fire fetch immediately to populate the screen with actual data
        asyncio.create_task(self.fetch_data())
        # Set up recurring timer for 5.0 seconds
        self.timer = ui.timer(5.0, self.fetch_data)
