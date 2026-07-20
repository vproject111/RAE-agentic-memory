from nicegui import ui
from utils.api_client import RAESuiteClient
from utils.ui_helpers import create_module_header


class DecayRetentionApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.decay_rate = 0.01
        self.protected_memories = [
            {
                "id": "m-1092",
                "content": "RESTRICTED: Corporate deployment credentials format",
                "layer": "semantic",
                "age": "4 days",
                "importance": 0.95,
                "pinned": True,
            },
            {
                "id": "m-1256",
                "content": "Lessons Learned: AST parser recursive loops resolution",
                "layer": "reflective",
                "age": "8 days",
                "importance": 0.88,
                "pinned": True,
            },
            {
                "id": "m-1311",
                "content": "SLA Rollback: Negative cache validation logic",
                "layer": "semantic",
                "age": "12 days",
                "importance": 0.82,
                "pinned": True,
            },
        ]
        self.decay_curve_data = []
        self.on_inspect = None
        self._calculate_decay_curve()

    def _calculate_decay_curve(self):
        self.decay_curve_data = []
        strength = 1.0
        for day in range(31):
            self.decay_curve_data.append([day, round(strength, 4)])
            strength *= 1.0 - self.decay_rate

    def update_decay_rate(self, new_val):
        self.decay_rate = new_val
        self._calculate_decay_curve()
        ui.notify(f"Decay rate updated to {self.decay_rate:.4f}", type="info")

    def toggle_pin(self, mem_id):
        for mem in self.protected_memories:
            if mem["id"] == mem_id:
                mem["pinned"] = not mem["pinned"]
                ui.notify(
                    f"Memory {mem_id} Pin toggled to {mem['pinned']}", type="positive"
                )
                break

    def render(self):
        with ui.column().classes("w-full max-w-7xl mx-auto p-8 gap-y-6"):
            create_module_header(
                "Decay & Retention Management",
                "Monitor memory decay curves, retention rules, and protection pins.",
                self.client,
                rls_status="PROTECTED",
            )

            with ui.row().classes("w-full gap-6"):
                # Left side: Chart and parameters
                with ui.card().classes(
                    "flex-[2] p-6 bg-slate-900 text-white shadow-sm"
                ):
                    ui.label("MEMORY DECAY SIMULATOR (30 DAYS)").classes(
                        "text-xs font-bold text-slate-400 mb-4"
                    )

                    with ui.row().classes("w-full items-center gap-4 mb-4"):
                        ui.label(f"Decay Rate: {self.decay_rate:.4f}").classes(
                            "text-sm font-bold text-teal-300"
                        )
                        ui.slider(
                            min=0.001,
                            max=0.05,
                            step=0.001,
                            value=self.decay_rate,
                            on_change=lambda e: self.update_decay_rate(e.value),
                        ).classes("flex-grow")

                    ui.echart(
                        {
                            "title": {"text": ""},
                            "tooltip": {"trigger": "axis"},
                            "xAxis": {
                                "name": "Day",
                                "type": "value",
                                "min": 0,
                                "max": 30,
                                "axisLabel": {"color": "#94a3b8"},
                                "nameTextStyle": {"color": "#94a3b8"},
                            },
                            "yAxis": {
                                "name": "Strength",
                                "type": "value",
                                "min": 0,
                                "max": 1.0,
                                "axisLabel": {"color": "#94a3b8"},
                                "nameTextStyle": {"color": "#94a3b8"},
                            },
                            "series": [
                                {
                                    "type": "line",
                                    "data": self.decay_curve_data,
                                    "smooth": True,
                                    "lineStyle": {"color": "#0d9488", "width": 3},
                                    "areaStyle": {"color": "rgba(13, 148, 136, 0.1)"},
                                }
                            ],
                        }
                    ).classes("w-full h-64")

                # Right side: Retention rules
                with ui.card().classes(
                    "flex-1 p-6 bg-slate-900 text-white border border-teal-500/20 shadow-sm"
                ):
                    ui.label("RETENTION POLICIES (ISO 42001)").classes(
                        "text-xs font-bold text-teal-300 mb-4"
                    )
                    with ui.column().classes("gap-y-3 text-sm text-slate-200"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("schedule", color="teal")
                            ui.label("Sensory Memory SLA: 30 days").classes("font-bold")
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("lock", color="teal")
                            ui.label("Protected threshold: 7 days").classes("font-bold")

                        ui.separator().classes("bg-slate-800")
                        ui.label("System Decay Schedule:").classes(
                            "text-xs text-teal-300 uppercase font-black tracking-widest"
                        )
                        ui.label(
                            'Runs daily at 02:00 in the morning ("0 2 * * *").'
                        ).classes("text-xs italic text-slate-400")

            # --- Row 2: Protected/Pinned Memories Tabela ---
            with ui.card().classes("w-full p-6 bg-slate-900 text-white shadow-sm"):
                ui.label("PROTECTED MEMORY LEDGER (PINNED ITEMS)").classes(
                    "text-xs font-bold text-slate-400 mb-4"
                )

                with ui.column().classes("w-full gap-y-4").props("role=list"):
                    for mem in self.protected_memories:
                        card_details = f"**ID:** `{mem['id']}`\n**Layer:** `{mem['layer']}`\n**Age:** `{mem['age']}`\n**Importance:** `{mem['importance']:.2f}`\n\n**Content:**\n{mem['content']}"
                        with (
                            ui.row()
                            .classes(
                                "w-full items-center justify-between border-b border-slate-800 pb-3 text-sm cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500"
                            )
                            .props(
                                'tabindex=0 role="listitem" aria-label="Protected Memory entry: click for details"'
                            )
                            .on(
                                "click",
                                lambda m_title=f"Memory {mem['id']}", m_det=card_details: (
                                    self.on_inspect(m_title, m_det)
                                    if self.on_inspect
                                    else None
                                ),
                            )
                        ):
                            with ui.column().classes("gap-y-1"):
                                with ui.row().classes("gap-2 items-center"):
                                    ui.badge(mem["id"]).props("color=teal")
                                    ui.badge(mem["layer"].upper()).props("color=slate")
                                    ui.label(f'Age: {mem["age"]}').classes(
                                        "text-xs text-slate-400"
                                    )
                                ui.label(mem["content"]).classes(
                                    "text-slate-200 font-medium"
                                )

                            with ui.row().classes("items-center gap-4"):
                                ui.label(
                                    f'Importance: {mem["importance"]:.2f}'
                                ).classes("font-bold text-teal-300")
                                ui.button(
                                    "UNPIN" if mem["pinned"] else "PIN",
                                    on_click=lambda m_id=mem["id"]: self.toggle_pin(
                                        m_id
                                    ),
                                ).props(
                                    "flat color=red"
                                    if mem["pinned"]
                                    else "flat color=teal"
                                )
