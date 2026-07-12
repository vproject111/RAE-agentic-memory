import asyncio
from nicegui import ui
from utils.api_client import RAESuiteClient

class DecayRetentionApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.decay_rate = 0.01
        self.protected_memories = [
            {"id": "m-1092", "content": "RESTRICTED: Corporate deployment credentials format", "layer": "semantic", "age": "4 days", "importance": 0.95, "pinned": True},
            {"id": "m-1256", "content": "Lessons Learned: AST parser recursive loops resolution", "layer": "reflective", "age": "8 days", "importance": 0.88, "pinned": True},
            {"id": "m-1311", "content": "SLA Rollback: Negative cache validation logic", "layer": "semantic", "age": "12 days", "importance": 0.82, "pinned": True},
        ]
        self.decay_curve_data = []
        self._calculate_decay_curve()

    def _calculate_decay_curve(self):
        # Calculate memory strength over 30 days based on decay rate
        self.decay_curve_data = []
        strength = 1.0
        for day in range(31):
            self.decay_curve_data.append([day, round(strength, 4)])
            strength *= (1.0 - self.decay_rate)

    def update_decay_rate(self, new_val):
        self.decay_rate = new_val
        self._calculate_decay_curve()
        # Trigger chart reload
        ui.notify(f"Decay rate updated to {self.decay_rate:.4f}", type="info")

    def toggle_pin(self, mem_id):
        for mem in self.protected_memories:
            if mem["id"] == mem_id:
                mem["pinned"] = not mem["pinned"]
                ui.notify(f"Memory {mem_id} Pin toggled to {mem['pinned']}", type="positive")
                break

    def render(self):
        with ui.column().classes('w-full max-w-7xl mx-auto p-8 gap-6'):
            ui.label('Decay & Retention Management').classes('text-3xl font-black text-teal-950 mb-2')
            ui.label('Monitor memory decay curves, retention rules, and protection pins.').classes('text-slate-500 mb-4')

            with ui.row().classes('w-full gap-6'):
                # Left side: Chart and parameters
                with ui.card().classes('flex-[2] p-6 shadow-sm'):
                    ui.label('MEMORY DECAY SIMULATOR (30 DAYS)').classes('text-xs font-bold text-slate-400 mb-4')
                    
                    with ui.row().classes('w-full items-center gap-4 mb-4'):
                        ui.label(f'Decay Rate: {self.decay_rate:.4f}').classes('text-sm font-bold text-teal-950')
                        ui.slider(min=0.001, max=0.05, step=0.001, value=self.decay_rate, on_change=lambda e: self.update_decay_rate(e.value)).classes('flex-grow')

                    ui.echart({
                        'title': {'text': ''},
                        'tooltip': {'trigger': 'axis'},
                        'xAxis': {'name': 'Day', 'type': 'value', 'min': 0, 'max': 30},
                        'yAxis': {'name': 'Strength', 'type': 'value', 'min': 0, 'max': 1.0},
                        'series': [{
                            'type': 'line',
                            'data': self.decay_curve_data,
                            'smooth': True,
                            'lineStyle': {'color': '#0d9488', 'width': 3},
                            'areaStyle': {'color': 'rgba(13, 148, 136, 0.1)'}
                        }]
                    }).classes('w-full h-64')

                # Right side: Retention rules
                with ui.card().classes('flex-1 p-6 bg-teal-50 border-teal-100 shadow-sm'):
                    ui.label('RETENTION POLICIES (ISO 42001)').classes('text-xs font-bold text-teal-800 mb-4')
                    with ui.column().classes('gap-3 text-sm text-slate-800'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('schedule', color='teal')
                            ui.label('Sensory Memory SLA: 30 days').classes('font-bold')
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('lock', color='teal')
                            ui.label('Protected threshold: 7 days').classes('font-bold')
                        
                        ui.separator().classes('bg-teal-200')
                        ui.label('System Decay Schedule:').classes('text-xs text-teal-900 uppercase font-black tracking-widest')
                        ui.label('Runs daily at 02:00 in the morning ("0 2 * * *").').classes('text-xs italic text-slate-600')

            # --- Row 2: Protected/Pinned Memories Tabela ---
            with ui.card().classes('w-full p-6 shadow-sm'):
                ui.label('PROTECTED MEMORY LEDGER (PINNED ITEMS)').classes('text-xs font-bold text-slate-400 mb-4')
                
                with ui.column().classes('w-full gap-4'):
                    for mem in self.protected_memories:
                        with ui.row().classes('w-full items-center justify-between border-b pb-3 text-sm'):
                            with ui.column().classes('gap-1'):
                                with ui.row().classes('gap-2 items-center'):
                                    ui.badge(mem["id"]).props('color=teal')
                                    ui.badge(mem["layer"].upper()).props('color=slate')
                                    ui.label(f'Age: {mem["age"]}').classes('text-xs text-slate-400')
                                ui.label(mem["content"]).classes('text-slate-800 font-medium')
                            
                            with ui.row().classes('items-center gap-4'):
                                ui.label(f'Importance: {mem["importance"]:.2f}').classes('font-bold text-teal-950')
                                ui.button(
                                    'UNPIN' if mem["pinned"] else 'PIN', 
                                    on_click=lambda m_id=mem["id"]: self.toggle_pin(m_id)
                                ).props('flat color=red' if mem["pinned"] else 'flat color=teal')
