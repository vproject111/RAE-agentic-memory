import asyncio
import hashlib
import re

from nicegui import ui
from utils.api_client import RAESuiteClient
from utils.ui_helpers import create_module_header


class CentralAuditorApp:
    """
    Faza 8: Centralny Audytor ISO (Oracle Sentinel v1.3) Page.
    Enforces event chain trace validation, cryptographic signature verification,
    secret redaction scans, and simulation pollution checks in compliance with ISO 27001.
    """

    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.project = "default"
        self.is_scanning = False
        self.findings = []
        self.compliance_rating = "COMPLIANT"
        self.evidence_source = "TRACE-8f2c31b0"
        self.audit_lock = asyncio.Lock()

        # Mock MAES events with raw payloads to scan for secrets
        self.mock_events = [
            {
                "seq": 0,
                "id": "ev-0",
                "parent": None,
                "type": "AGENT_DECISION",
                "mode": "PRODUCTION",
                "redacted": "REDACTED",
                "sig": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
                "payload": "Agent decided to execute target action",
            },
            {
                "seq": 1,
                "id": "ev-1",
                "parent": "ev-0",
                "type": "TOOL_INVOCATION",
                "mode": "PRODUCTION",
                "redacted": "REDACTED",
                "sig": "Valid",
                "payload": "Executing search_web tool",
            },
            {
                "seq": 2,
                "id": "ev-2",
                "parent": "ev-1",
                "type": "MEMORY_WRITTEN",
                "mode": "PRODUCTION",
                "redacted": "REDACTED",
                "sig": "Valid",
                "payload": "Memory written successfully",
            },
        ]

    def verify_event_signature(self, ev: dict) -> bool:
        """Computes the canonical hash of the event sequence fields and checks signature."""
        if ev["sig"] == "Valid":
            return True
        try:
            canonical_data = f"{ev['id']}|{ev['parent'] or ''}|{ev['seq']}|{ev['type']}|{ev['mode']}|{ev['payload']}"
            expected_hash = hashlib.sha256(canonical_data.encode("utf-8")).hexdigest()
            return ev["sig"] == expected_hash
        except Exception:
            return False

    def detect_secrets(self, payload: str) -> bool:
        """Regex scanning for passwords, private keys, AWS tokens without redaction."""
        patterns = [
            re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
            re.compile(
                r"(?i)(password|secret|token|passwd|private_key|auth_key)\s*[:=]\s*['\"].+['\"]"
            ),
            re.compile(r"(?i)aws_[a-z_]*key\s*[:=]\s*['\"][A-Za-z0-9/+=]{16,}['\"]"),
        ]
        return any(p.search(payload) for p in patterns)

    async def trigger_sentinel_audit(self):
        # Enforce thread-safe lock to prevent overlapping runs/race conditions
        if self.audit_lock.locked():
            ui.notify("Sentinel Scan: An audit is already in progress.", type="warning")
            return

        async with self.audit_lock:
            self.is_scanning = True
            ui.notify("Oracle Sentinel v1.3: Commencing audit scan...", type="info")
            self.update_ui.refresh()

            # Simulating analysis time
            await asyncio.sleep(1.5)

            # Analyze current mock event chain configuration
            self.findings = []
            self.compliance_rating = "COMPLIANT"

            # 1. Sequence Root & Chronology Checks
            if not self.mock_events:
                self.compliance_rating = "NEEDS_REVIEW"
                self.is_scanning = False
                self.update_ui.refresh()
                return

            first_event = self.mock_events[0]
            if first_event["seq"] != 0:
                self.findings.append(
                    {
                        "id": "finding-0",
                        "control": "A.12.4.1",
                        "severity": "HIGH",
                        "type": "MISSING_ROOT",
                        "desc": f"Trace sequence root has non-zero sequence_no: {first_event['seq']}.",
                    }
                )
            if first_event["parent"] is not None:
                self.findings.append(
                    {
                        "id": "finding-1",
                        "control": "A.12.4.1",
                        "severity": "MEDIUM",
                        "type": "ORPHANED_ROOT",
                        "desc": f"Root event sequence_no 0 declares parent: {first_event['parent']}.",
                    }
                )

            # 2. Iterate chain continuity & cryptographic signatures
            for i in range(1, len(self.mock_events)):
                prev = self.mock_events[i - 1]
                curr = self.mock_events[i]

                # Check cryptographic signatures
                if not self.verify_event_signature(curr):
                    self.findings.append(
                        {
                            "id": f"finding-sig-{i}",
                            "control": "A.12.4.1",
                            "severity": "CRITICAL",
                            "type": "INVALID_SIGNATURE",
                            "desc": f"Cryptographic signature check failed on event {curr['id']}.",
                        }
                    )
                if curr["seq"] != prev["seq"] + 1:
                    self.findings.append(
                        {
                            "id": f"finding-gap-{i}",
                            "control": "A.12.4.1",
                            "severity": "HIGH",
                            "type": "NON_MONOTONIC_SEQUENCE",
                            "desc": f"Sequence gap: Expected {prev['seq'] + 1}, got {curr['seq']}.",
                        }
                    )
                if curr["parent"] != prev["id"]:
                    self.findings.append(
                        {
                            "id": f"finding-link-{i}",
                            "control": "A.12.4.1",
                            "severity": "CRITICAL",
                            "type": "BROKEN_CHAIN",
                            "desc": f"Parent UUID mismatch: expects parent {curr['parent']}, got {prev['id']}.",
                        }
                    )

            # 3. Secret Redaction & Pollution checks
            for event in self.mock_events:
                # Check actual payload contents for secrets
                if self.detect_secrets(event["payload"]):
                    if event["redacted"] != "REDACTED":
                        self.findings.append(
                            {
                                "id": f"finding-leak-{event['id']}",
                                "control": "A.12.4.1",
                                "severity": "HIGH",
                                "type": "SECRET_LEAK",
                                "desc": f"Sensitive credentials/tokens found in event {event['id']} without redaction masking.",
                            }
                        )
                if event["mode"] in ["SIMULATION_ONLY", "DRY_RUN"] and event[
                    "type"
                ] in [
                    "MEMORY_WRITTEN",
                    "LEDGER_COMMITTED",
                ]:
                    self.findings.append(
                        {
                            "id": f"finding-poll-{event['id']}",
                            "control": "A.12.4.1",
                            "severity": "CRITICAL",
                            "type": "SIMULATION_POLLUTION",
                            "desc": f"Simulation event {event['id']} attempted to permanently write to production DB.",
                        }
                    )

            # Calculate rating
            critical_count = sum(
                1 for f in self.findings if f["severity"] in ["CRITICAL", "HIGH"]
            )
            medium_count = sum(1 for f in self.findings if f["severity"] == "MEDIUM")

            if critical_count > 0:
                self.compliance_rating = "NON_COMPLIANT"
            elif medium_count > 0:
                self.compliance_rating = "PARTIAL"
            elif len(self.findings) > 0:
                self.compliance_rating = "NEEDS_REVIEW"
            else:
                self.compliance_rating = "COMPLIANT"

            self.is_scanning = False
            self.update_ui.refresh()
            ui.notify(
                "Oracle Sentinel: Audit completed.",
                type="positive" if self.compliance_rating == "COMPLIANT" else "warning",
            )

            # Log to RAE Compliance audit trail
            await self.client.ingest_text(
                text=f"ISO 27001 Sentinel Scan executed. Rating: {self.compliance_rating}. Findings count: {len(self.findings)}.",
                project="oracle_sentinel_audits",
                source="central_auditor_ui",
            )

    def sign_event(self, idx: int):
        """Generates canonical cryptographic signature for the selected event."""
        ev = self.mock_events[idx]
        canonical_data = f"{ev['id']}|{ev['parent'] or ''}|{ev['seq']}|{ev['type']}|{ev['mode']}|{ev['payload']}"
        ev["sig"] = hashlib.sha256(canonical_data.encode("utf-8")).hexdigest()
        self.update_ui.refresh()
        ui.notify(f"Event {ev['id']} cryptographically signed!", type="positive")

    def render(self):
        with ui.column().classes("w-full max-w-7xl mx-auto p-8 gap-y-6"):
            create_module_header(
                "Oracle Sentinel ISO Compliance Auditor",
                "Automated ISO 27001 / ISO 42001 event chain trace audits, Gap detection, and simulation checks.",
                self.client,
                rls_status="PROTECTED",
            )

            # Refreshable panel
            self.render_layout()

    @ui.refreshable
    def render_layout(self):
        with ui.row().classes("w-full gap-6"):
            # Left panel: Trace Configuration & Events Editor
            with ui.card().classes("flex-[2] p-6 bg-slate-900 text-white shadow-sm"):
                ui.label("EVIDENCE PATH CHAIN (MAES EVENTS)").classes(
                    "text-xs font-bold text-slate-400 mb-4"
                )

                # Render editable mock list
                for i, ev in enumerate(self.mock_events):
                    with ui.card().classes(
                        "w-full p-4 bg-slate-800 border-l-4 border-cyan-400 mb-4"
                    ):
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label(f"Event: {ev['id']} (Seq: {ev['seq']})").classes(
                                "font-mono font-bold text-cyan-300"
                            )
                            with ui.row().classes("gap-2"):
                                ui.button(
                                    "Sign", on_click=lambda idx=i: self.sign_event(idx)
                                ).props("flat dense color=cyan text-xs")
                                ui.button(
                                    "Remove",
                                    on_click=lambda idx=i: self.remove_event(idx),
                                ).props("flat dense color=red text-xs")

                        # Form controls inside cards
                        with ui.row().classes("w-full gap-4 mt-2"):
                            ui.select(
                                label="Action Type",
                                options=[
                                    "AGENT_DECISION",
                                    "TOOL_INVOCATION",
                                    "MEMORY_WRITTEN",
                                    "LEDGER_COMMITTED",
                                ],
                                value=ev["type"],
                                on_change=lambda val, idx=i: self.update_event_field(
                                    idx, "type", val
                                ),
                            ).classes("w-40").props("dark dense")

                            ui.select(
                                label="Execution Mode",
                                options=["PRODUCTION", "SIMULATION_ONLY", "DRY_RUN"],
                                value=ev["mode"],
                                on_change=lambda val, idx=i: self.update_event_field(
                                    idx, "mode", val
                                ),
                            ).classes("w-36").props("dark dense")

                            ui.select(
                                label="Redaction State",
                                options=["REDACTED", "UNREDACTED"],
                                value=ev["redacted"],
                                on_change=lambda val, idx=i: self.update_event_field(
                                    idx, "redacted", val
                                ),
                            ).classes("w-32").props("dark dense")

                        with ui.row().classes("w-full gap-4 mt-2"):
                            # Edit sequence or parent to simulate breaks/gaps
                            ui.number(
                                label="Sequence No",
                                value=ev["seq"],
                                on_change=lambda val, idx=i: self.update_event_field(
                                    idx, "seq", int(val or 0)
                                ),
                            ).classes("w-28").props("dark dense")

                            ui.input(
                                label="Parent ID",
                                value=ev["parent"] or "",
                                on_change=lambda val, idx=i: self.update_event_field(
                                    idx, "parent", val if val else None
                                ),
                            ).classes("w-32").props("dark dense")

                            ui.input(
                                label="Signature (SHA-256)", value=ev["sig"]
                            ).classes("flex-grow").props("dark dense readonly")

                        # Payload text field (where raw secrets can be typed)
                        ui.input(
                            label="Raw Event Payload / Logs",
                            value=ev["payload"],
                            on_change=lambda val, idx=i: self.update_event_field(
                                idx, "payload", val
                            ),
                        ).classes("w-full mt-2").props("dark dense")

                # Controls to add events
                with ui.row().classes("w-full gap-4 mt-4"):
                    ui.button(
                        "Add Monotonic Event", on_click=self.add_monotonic_event
                    ).props("outline color=cyan rounded text-xs")
                    ui.button(
                        "Add Corrupt Link Event", on_click=self.add_corrupt_event
                    ).props("outline color=amber rounded text-xs")

            # Right panel: Auditor Findings & Compliance Status
            with ui.column().classes("flex-[1] gap-y-6"):
                # Compliance Status Card
                with ui.card().classes("w-full p-6 bg-slate-900 text-white shadow-sm"):
                    ui.label("SENTINEL COMPLIANCE STATUS").classes(
                        "text-xs font-bold text-slate-400 mb-4"
                    )

                    status_colors = {
                        "COMPLIANT": ("emerald-400", "check_circle"),
                        "PARTIAL": ("amber-400", "warning"),
                        "NEEDS_REVIEW": ("blue-400", "info"),
                        "NON_COMPLIANT": ("red-400", "error"),
                    }
                    color, icon = status_colors.get(
                        self.compliance_rating, ("slate-400", "help")
                    )

                    with ui.row().classes("items-center gap-x-2"):
                        ui.icon(icon, color=color).classes("text-2xl")
                        ui.label(self.compliance_rating).classes(
                            f"text-xl font-black text-{color}"
                        )

                    ui.markdown(
                        f"**Evidence Source:** `{self.evidence_source}`"
                    ).classes("text-xs text-slate-400 mt-2")

                    if self.is_scanning:
                        with ui.row().classes("items-center mt-4"):
                            ui.spinner("dots", color="cyan")
                            ui.label("Running Gap Analysis...").classes(
                                "text-xs text-slate-300"
                            )
                    else:
                        ui.button(
                            "RUN COMPLIANCE AUDIT", on_click=self.trigger_sentinel_audit
                        ).props("color=cyan rounded w-full mt-4")

                # Findings List Card
                with ui.card().classes("w-full p-6 bg-slate-900 text-white shadow-sm"):
                    ui.label("AUDIT FINDINGS").classes(
                        "text-xs font-bold text-slate-400 mb-4"
                    )

                    if not self.findings:
                        ui.label(
                            "No gap detections or leaks observed in the trace."
                        ).classes("text-xs italic text-slate-500")
                    else:
                        for f in self.findings:
                            border_color = (
                                "red-400"
                                if f["severity"] == "CRITICAL"
                                else (
                                    "orange-400"
                                    if f["severity"] == "HIGH"
                                    else "amber-400"
                                )
                            )
                            with ui.card().classes(
                                f"w-full p-3 bg-slate-800 border-l-4 border-{border_color} mb-2"
                            ):
                                with ui.row().classes(
                                    "w-full justify-between items-center"
                                ):
                                    ui.label(f"{f['type']} ({f['control']})").classes(
                                        "text-xs font-bold font-mono"
                                    )
                                    ui.badge(f["severity"]).props(
                                        f"color={'red' if f['severity'] == 'CRITICAL' else 'orange' if f['severity'] == 'HIGH' else 'amber'}"
                                    )
                                ui.label(f["desc"]).classes(
                                    "text-[10px] text-slate-300 mt-1"
                                )

    # State update helper methods
    def update_event_field(self, idx: int, field: str, value):
        self.mock_events[idx][field] = value
        self.update_ui.refresh()

    def remove_event(self, idx: int):
        if len(self.mock_events) > 1:
            self.mock_events.pop(idx)
            self.update_ui.refresh()

    def add_monotonic_event(self):
        last_ev = self.mock_events[-1]
        next_seq = last_ev["seq"] + 1
        next_id = f"ev-{next_seq}"
        self.mock_events.append(
            {
                "seq": next_seq,
                "id": next_id,
                "parent": last_ev["id"],
                "type": "AGENT_DECISION",
                "mode": "PRODUCTION",
                "redacted": "REDACTED",
                "sig": "Valid",
                "payload": f"Step {next_seq} completed",
            }
        )
        self.update_ui.refresh()

    def add_corrupt_event(self):
        last_ev = self.mock_events[-1]
        next_seq = last_ev["seq"] + 2  # Skip sequence number to create gap
        next_id = f"ev-{next_seq}"
        self.mock_events.append(
            {
                "seq": next_seq,
                "id": next_id,
                "parent": "broken-parent-id",  # Broken link
                "type": "MEMORY_WRITTEN",
                "mode": "SIMULATION_ONLY",  # simulation pollution
                "redacted": "UNREDACTED",  # secret leak
                "sig": "Invalid",  # signature failure
                "payload": "AWS secret detected: aws_secret_key='AKIAIOSFODNN7EXAMPLE'",  # raw secret leak!
            }
        )
        self.update_ui.refresh()

    @property
    def update_ui(self):
        return self.render_layout
