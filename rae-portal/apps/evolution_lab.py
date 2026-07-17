import asyncio
from nicegui import ui
from utils.api_client import RAESuiteClient

class EvolutionLabApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.alpha = 0.40
        self.beta = 0.30
        self.gamma = 0.30
        self.context_switch_cost = "1,200 tokens"
        self.batch_gain = "40% saved (avg. 8.4s)"
        self.amortization_rate = "95% (warm state)"
        self.anomalies = [
            {"time": "08:12:44", "error": "CircularImportError in adapter layer", "action": "Refactored imports"},
            {"time": "09:22:15", "error": "FastAPI HTTP_422 DeprecationWarning", "action": "Updated status_code contract"},
        ]

    def render(self):
        with ui.column().classes('w-full max-w-7xl mx-auto p-8 gap-6'):
            ui.label('Evolution Lab & Kaizen').classes('text-3xl font-black text-purple-950 mb-2')
            ui.label('Monitor Multi-Armed Bandit weights, Context Economy, and Shadow Mode evaluations.').classes('text-slate-500 mb-4')

            # --- Row 1: Context Economy KPI Cards ---
            with ui.row().classes('w-full gap-4'):
                with ui.card().classes('flex-1 p-6 border-l-4 border-purple-500 shadow-sm'):
                    ui.label('CONTEXT SWITCH COST (CSC)').classes('text-xs font-bold text-slate-400')
                    ui.label(self.context_switch_cost).classes('text-2xl font-black text-slate-800 mt-2')
                
                with ui.card().classes('flex-1 p-6 border-l-4 border-purple-500 shadow-sm'):
                    ui.label('BATCH GAIN (SAVINGS)').classes('text-xs font-bold text-slate-400')
                    ui.label(self.batch_gain).classes('text-2xl font-black text-slate-800 mt-2')

                with ui.card().classes('flex-1 p-6 border-l-4 border-purple-500 shadow-sm'):
                    ui.label('AMORTIZATION RATE').classes('text-xs font-bold text-slate-400')
                    ui.label(self.amortization_rate).classes('text-2xl font-black text-slate-800 mt-2')

            # --- Row 2: MAB Pie & Shadow Mode ---
            with ui.row().classes('w-full gap-6 mt-4'):
                # MAB Weights Chart
                with ui.card().classes('flex-1 p-6 shadow-sm'):
                    ui.label('MULTI-ARMED BANDIT (MAB) MODEL ROUTER WEIGHTS').classes('text-xs font-bold text-slate-400 mb-4')
                    ui.echart({
                        'title': {'text': ''},
                        'tooltip': {'trigger': 'item'},
                        'series': [{
                            'name': 'MAB Weights',
                            'type': 'pie',
                            'radius': '70%',
                            'data': [
                                {'value': self.alpha, 'name': f'Accuracy ({self.alpha:.2f})'},
                                {'value': self.beta, 'name': f'Latency ({self.beta:.2f})'},
                                {'value': self.gamma, 'name': f'Cost ({self.gamma:.2f})'}
                            ],
                            'color': ['#a855f7', '#d8b4fe', '#f3e8ff']
                        }]
                    }).classes('w-full h-64')

                # Shadow Mode
                with ui.card().classes('flex-1 p-6 shadow-sm'):
                    ui.label('SHADOW MODEL EVALUATION').classes('text-xs font-bold text-slate-400 mb-4')
                    ui.echart({
                        'title': {'text': ''},
                        'tooltip': {'trigger': 'axis'},
                        'xAxis': {'type': 'category', 'data': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']},
                        'yAxis': {'type': 'value', 'name': 'Accuracy (%)'},
                        'series': [
                            {'name': 'Production Model', 'type': 'line', 'data': [92, 93, 91, 94, 95], 'lineStyle': {'color': '#a855f7'}},
                            {'name': 'Shadow Candidate', 'type': 'line', 'data': [88, 89, 92, 93, 94], 'lineStyle': {'color': '#cbd5e1', 'type': 'dashed'}}
                        ]
                    }).classes('w-full h-64')

            # --- Row 3: Failure Mining & Rule Generator ---
            with ui.card().classes('w-full p-6 shadow-sm'):
                ui.label('FAILURE MINING & KAIZEN RULE GENERATOR').classes('text-xs font-bold text-slate-400 mb-4')
                with ui.column().classes('w-full gap-4'):
                    for anomaly in self.anomalies:
                        with ui.row().classes('w-full items-center justify-between border-b pb-3 text-sm'):
                            with ui.column().classes('gap-1'):
                                with ui.row().classes('gap-2 items-center'):
                                    ui.badge(anomaly["time"]).props('color=purple')
                                    ui.label(anomaly["error"]).classes('text-slate-800 font-bold')
                                ui.label(f'Candidate rule: {anomaly["action"]}').classes('text-xs text-slate-500 italic')
                            ui.button('APPROVE RULE', on_click=lambda: ui.notify("Rule promoted to active guardrails", type="positive")).props('flat color=purple')
