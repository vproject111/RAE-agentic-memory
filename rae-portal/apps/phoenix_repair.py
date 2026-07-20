from nicegui import ui
from utils.api_client import RAESuiteClient
from utils.ui_helpers import create_module_header


class PhoenixRepairApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.on_inspect = None
        self.incident_active = False
        self.candidates = [
            {
                "id": "PHX-101",
                "file": "core/math_controller.py",
                "issue": "Performance regression in no-LLM benchmarks",
                "status": "Ready to Simulate",
                "attempts": 2,
                "diff": "- profile: 'research'\n+ profile: 'cheap'\n- # Expensive Multi-Armed Bandit enabled\n+ # Disabled MAB and logging, forcing L1 heuristics",
            },
            {
                "id": "PHX-102",
                "file": "apps/memory_api/main.py",
                "issue": "FastAPI HTTP_422_UNPROCESSABLE_ENTITY deprecation",
                "status": "Simulation Passed",
                "attempts": 1,
                "diff": "- status_code=status.HTTP_422_UNPROCESSABLE_ENTITY\n+ status_code=status.HTTP_422_UNPROCESSABLE_ENTITY",
            },
        ]

    def simulate_repair(self, repair_id):
        ui.notify(
            f"Simulating repair for {repair_id}... Diffs generated successfully.",
            type="positive",
        )

    def apply_repair(self, repair_id):
        ui.notify(f"Applying repair {repair_id} directly in sandbox...", type="info")

    def render(self):
        with ui.column().classes("w-full max-w-7xl mx-auto p-8 gap-y-6"):
            create_module_header(
                "Phoenix Planner & Self-Healing",
                "Automatic repair loop, bugfix simulations, and rollback managers.",
                self.client,
                rls_status="PROTECTED",
            )

            with ui.row().classes("w-full gap-6"):
                # Left panel: Repair candidates
                with ui.card().classes(
                    "flex-[2] p-6 bg-slate-900 text-white shadow-sm"
                ):
                    ui.label("REPAIR LOOP STATUS").classes(
                        "text-xs font-bold text-slate-400 mb-4"
                    )
                    with ui.column().classes("w-full gap-y-4").props("role=list"):
                        for cand in self.candidates:
                            card_details = f"**Candidate:** `{cand['id']}`\n**File:** `{cand['file']}`\n**Issue:** {cand['issue']}\n**Status:** `{cand['status']}`\n**Attempts:** `{cand['attempts']}/3`"
                            with (
                                ui.card()
                                .classes(
                                    "w-full p-4 bg-slate-800 border-l-4 border-purple-400 cursor-pointer hover:bg-slate-700 focus:outline focus:outline-2 focus:outline-blue-500"
                                )
                                .props(
                                    'tabindex=0 role="listitem" aria-label="Repair Candidate: click for details"'
                                )
                                .on(
                                    "click",
                                    lambda c_title=f"Repair {cand['id']}", c_det=card_details: (
                                        self.on_inspect(c_title, c_det)
                                        if self.on_inspect
                                        else None
                                    ),
                                )
                            ):
                                with ui.row().classes(
                                    "w-full items-center justify-between"
                                ):
                                    with ui.column().classes("gap-y-1"):
                                        ui.label(cand["id"]).classes(
                                            "text-sm font-bold text-purple-300"
                                        )
                                        ui.label(cand["file"]).classes(
                                            "text-xs text-slate-300 font-mono"
                                        )
                                        ui.label(cand["issue"]).classes(
                                            "text-xs text-slate-400"
                                        )
                                    with ui.column().classes("items-end"):
                                        ui.badge(cand["status"]).props("color=purple")
                                        ui.label(
                                            f'Attempts: {cand["attempts"]}/3'
                                        ).classes("text-[10px] text-slate-400")

                # Right panel: Diff Viewer & Controls
                with ui.card().classes(
                    "flex-grow p-6 bg-slate-900 text-white border border-purple-500/20 shadow-sm"
                ):
                    ui.label("PROPOSED DIFF & SIMULATE").classes(
                        "text-xs font-bold text-purple-300 mb-4"
                    )
                    with ui.column().classes("w-full gap-y-4"):
                        ui.label(
                            "Proposed changes for core/math_controller.py"
                        ).classes("text-sm font-bold")
                        # Code Diff Block
                        with ui.card().classes(
                            "w-full p-4 bg-slate-950 font-mono text-xs text-slate-300 border border-slate-800"
                        ):
                            ui.label("- profile: 'research'").classes("text-red-300")
                            ui.label("+ profile: 'cheap'").classes("text-emerald-300")
                            ui.label(
                                "- # Expensive Multi-Armed Bandit enabled"
                            ).classes("text-red-300")
                            ui.label(
                                "+ # Disabled MAB and logging, forcing L1 heuristics"
                            ).classes("text-emerald-300")

                        with ui.row().classes("w-full gap-4"):
                            ui.button(
                                "SIMULATE",
                                on_click=lambda: self.simulate_repair("PHX-101"),
                            ).props("color=purple rounded")
                            ui.button(
                                "APPLY REPAIR",
                                on_click=lambda: self.apply_repair("PHX-101"),
                            ).props("outline color=purple rounded")

            # --- FAZA 7: Rollback SLA Manager & Quarantine Monitors ---
            ui.label("ROLLBACK SLA MANAGER & QUARANTINE CONTROL").classes(
                "text-sm font-bold text-slate-300 mt-8 mb-2"
            )

            with ui.row().classes("w-full gap-6"):
                # Left Column: SLA Reference & Live Quarantine Monitor
                with ui.column().classes("flex-[1] gap-y-6"):
                    # SLA Reference Card
                    with ui.card().classes(
                        "w-full p-6 bg-slate-900 text-white shadow-sm"
                    ):
                        ui.label("SLA MATRIX LIMITS (ISO 27001)").classes(
                            "text-xs font-bold text-slate-400 mb-4"
                        )
                        with ui.column().classes("w-full gap-y-2"):
                            ui.markdown("Container Restart: **15.0s**")
                            ui.markdown("Git Worktree Revert: **30.0s**")
                            ui.markdown("Config Restore: **60.0s**")
                            ui.markdown("DB Schema Rollback: **120.0s**")
                            ui.markdown("Vector Projection Rollback: **300.0s**")

                    # Live Quarantine & SLA Countdown Card
                    with ui.card().classes(
                        "w-full p-6 bg-slate-900 text-white shadow-sm"
                    ):
                        ui.label("LIVE INCIDENT MONITOR").classes(
                            "text-xs font-bold text-slate-400 mb-4"
                        )

                        # System status indicator
                        self.status_container = ui.row().classes("items-center gap-x-2")
                        with self.status_container:
                            self.status_icon = ui.icon(
                                "check_circle", color="emerald"
                            ).classes("text-xl")
                            self.status_label = ui.label(
                                "ALL SYSTEMS OPERATIONAL"
                            ).classes("text-sm font-bold text-emerald-400")

                        # Live recovery progress bar & countdown
                        self.timer_container = ui.column().classes(
                            "w-full gap-y-2 mt-4 hidden"
                        )
                        with self.timer_container:
                            ui.label("Automatic SLA Recovery In Progress...").classes(
                                "text-xs text-purple-300"
                            )
                            self.progress_bar = ui.linear_progress(value=1.0).props(
                                "color=purple show-value=false"
                            )
                            self.timer_lbl = ui.label(
                                "Time to rollback: 15.0s"
                            ).classes("text-sm font-mono text-purple-200")

                        # Quarantine logs
                        ui.label("Quarantined Contexts:").classes(
                            "text-xs text-slate-400 mt-4"
                        )
                        self.quarantine_list = ui.column().classes(
                            "w-full gap-y-1 mt-1"
                        )
                        with self.quarantine_list:
                            self.no_incident_lbl = ui.label(
                                "No active quarantined contexts"
                            ).classes("text-xs italic text-slate-500")

                        with ui.row().classes("w-full gap-4 mt-6"):
                            ui.button(
                                "TRIGGER INCIDENT",
                                on_click=self.trigger_simulated_incident,
                            ).props("color=red rounded text-xs")
                            ui.button(
                                "CLEAR QUARANTINE",
                                on_click=self.clear_quarantine,
                            ).props("outline color=slate-400 rounded text-xs")

                # Right Column: Rollback Plan Verification Simulator
                with ui.card().classes(
                    "flex-[1] p-6 bg-slate-900 text-white shadow-sm"
                ):
                    ui.label("ROLLBACK PLAN VERIFIER").classes(
                        "text-xs font-bold text-slate-400 mb-4"
                    )

                    # Simulation form fields
                    self.val_plan_id = ui.input("Plan ID", value="PLAN-202").classes(
                        "w-full"
                    )
                    self.val_action = ui.select(
                        label="Action Type",
                        options={
                            "container_restart": "container_restart (max 15s)",
                            "git_worktree_revert": "git_worktree_revert (max 30s)",
                            "config_restore": "config_restore (max 60s)",
                            "db_schema_rollback": "db_schema_rollback (max 120s)",
                            "vector_projection_rollback": "vector_projection_rollback (max 300s)",
                        },
                        value="container_restart",
                    ).classes("w-full")
                    self.val_sla = ui.number(
                        "SLA Threshold (seconds)", value=12.0
                    ).classes("w-full")
                    self.val_risk = ui.select(
                        label="Risk Class",
                        options=["R1", "R2", "R3", "R4", "R5"],
                        value="R4",
                    ).classes("w-full")
                    self.val_sandbox = ui.checkbox(
                        "Verified in Sandbox", value=True
                    ).classes("mt-2")

                    ui.button(
                        "VERIFY ROLLBACK PLAN",
                        on_click=self.verify_simulated_plan,
                    ).props("color=purple rounded w-full mt-4")

                    # Output alert banner
                    self.verification_banner = ui.card().classes(
                        "w-full p-4 mt-4 hidden bg-slate-800 text-xs"
                    )

    def trigger_simulated_incident(self):
        if getattr(self, "incident_active", False):
            ui.notify(
                "An incident is already active and recovery is in progress.",
                type="warning",
            )
            return

        self.incident_active = True

        # Update system status
        self.status_icon.props("name=warning color=red")
        self.status_label.set_text("DEGRADED: INCIDENT ACTIVE")
        self.status_label.classes(replace="text-red-400")

        # Display quarantined context logs
        self.quarantine_list.clear()
        with self.quarantine_list:
            ui.label("• ctx-phoenix-autoheal [IncidentScope: SERVICE_GROUP]").classes(
                "text-xs text-red-300 font-mono"
            )
            ui.label("• ctx-phoenix-autoheal_dep1 [Quarantined dependency]").classes(
                "text-xs text-slate-400 font-mono"
            )
            ui.label("• ctx-phoenix-autoheal_dep2 [Quarantined dependency]").classes(
                "text-xs text-slate-400 font-mono"
            )

        # Activate SLA timer countdown (e.g. 15s limit)
        self.timer_container.classes(remove="hidden")
        self.timer_seconds = 15.0
        self.progress_bar.set_value(1.0)
        self.timer_lbl.set_text(f"Time to rollback: {self.timer_seconds:.1f}s")

        # Start NiceGUI timer tick
        self.incident_timer = ui.timer(0.1, self.tick_incident_timer)
        ui.notify(
            "SLA Incident Triggered! Automatic rollback scheduled in 15 seconds.",
            type="warning",
        )

    def tick_incident_timer(self):
        self.timer_seconds -= 0.1
        if self.timer_seconds <= 0:
            self.timer_seconds = 0
            if hasattr(self, "incident_timer"):
                self.incident_timer.cancel()
            self.incident_active = False
            self.progress_bar.set_value(0)
            self.timer_lbl.set_text("Rollback completed successfully!")

            # Resolve incident
            self.status_icon.props("name=check_circle color=emerald")
            self.status_label.set_text("ALL SYSTEMS OPERATIONAL (Auto-recovered)")
            self.status_label.classes(replace="text-emerald-400")
            self.quarantine_list.clear()
            with self.quarantine_list:
                ui.label("All quarantines cleared.").classes("text-xs text-emerald-300")

            ui.notify(
                "SLA SLA Recovery SLA Rollback completed in sandbox limit under 15s!",
                type="positive",
            )
        else:
            self.progress_bar.set_value(self.timer_seconds / 15.0)
            self.timer_lbl.set_text(f"Time to rollback: {self.timer_seconds:.1f}s")

    def clear_quarantine(self):
        if getattr(self, "incident_active", False):
            try:
                self.incident_timer.cancel()
            except Exception:
                pass
            self.incident_active = False

        self.timer_container.classes(add="hidden")
        self.status_icon.props("name=check_circle color=emerald")
        self.status_label.set_text("ALL SYSTEMS OPERATIONAL")
        self.status_label.classes(replace="text-emerald-400")
        self.quarantine_list.clear()
        with self.quarantine_list:
            self.no_incident_lbl = ui.label("No active quarantined contexts").classes(
                "text-xs italic text-slate-500"
            )
        ui.notify("All quarantines cleared manually.", type="info")

    async def verify_simulated_plan(self):
        # Implementation matches RAE core RollbackSLAManager.verify_plan()
        action = self.val_action.value
        sla = float(self.val_sla.value or 0.0)
        risk = self.val_risk.value
        sandbox = self.val_sandbox.value
        plan_id = (self.val_plan_id.value or "PLAN-MOCK").strip()

        # Sanitization: validate Plan ID format via regex
        import re

        if not re.match(r"^PLAN-\d+$", plan_id):
            ui.notify(
                "Invalid Plan ID format. Must match PLAN-### (e.g. PLAN-202).",
                type="negative",
            )
            return

        # Max bounds
        sla_matrix = {
            "container_restart": 15.0,
            "git_worktree_revert": 30.0,
            "config_restore": 60.0,
            "db_schema_rollback": 120.0,
            "vector_projection_rollback": 300.0,
        }
        max_allowed = sla_matrix.get(action, 30.0)

        self.verification_banner.classes(remove="hidden")
        self.verification_banner.clear()

        if sla > max_allowed:
            with self.verification_banner:
                ui.label("PLAN REJECTED").classes("text-red-400 font-bold")
                ui.label(
                    f"SLA threshold of {sla}s exceeds the maximum limit of {max_allowed}s allowed for '{action}' under ISO 27001 SLA Matrix."
                ).classes("text-slate-300 mt-1")
            ui.notify(f"Rollback plan {plan_id} rejected!", type="negative")

            # Log audit event
            await self.client.ingest_text(
                text=f"ISO 27001 AUDIT: Rollback plan {plan_id} for {action} rejected. Reason: SLA threshold {sla}s > max {max_allowed}s.",
                project="rollback_audit_log",
                source="sla_manager_ui",
            )
            return

        if risk in ["R4", "R5"] and not sandbox:
            with self.verification_banner:
                ui.label("PLAN REJECTED").classes("text-red-400 font-bold")
                ui.label(
                    f"High-risk deployment '{risk}' cannot be approved because rollback action '{action}' has not been successfully verified in a sandbox environment."
                ).classes("text-slate-300 mt-1")
            ui.notify(f"Rollback plan {plan_id} rejected!", type="negative")

            # Log audit event
            await self.client.ingest_text(
                text=f"ISO 27001 AUDIT: Rollback plan {plan_id} for high-risk {risk} rejected. Reason: Sandbox verification missing.",
                project="rollback_audit_log",
                source="sla_manager_ui",
            )
            return

        # Approved
        with self.verification_banner:
            ui.label("PLAN APPROVED").classes("text-emerald-400 font-bold")
            ui.label(
                f"Rollback plan '{plan_id}' ({action}) successfully verified against SLA threshold ({sla}s <= {max_allowed}s). Ready for deployment."
            ).classes("text-slate-300 mt-1")
        ui.notify(f"Rollback plan {plan_id} approved!", type="positive")

        # Log audit event
        await self.client.ingest_text(
            text=f"ISO 27001 AUDIT: Rollback plan {plan_id} ({action}) verified and approved with SLA threshold {sla}s.",
            project="rollback_audit_log",
            source="sla_manager_ui",
        )
