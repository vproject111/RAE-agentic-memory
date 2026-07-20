from nicegui import ui
from utils.api_client import RAESuiteClient
from utils.ui_helpers import create_module_header


class PhoenixRepairApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.on_inspect = None
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
