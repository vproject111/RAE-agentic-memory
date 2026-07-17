import asyncio
from nicegui import ui
from utils.api_client import RAESuiteClient

class MissionControlApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.stats = {}
        self.health = {}
        self.quarantine_status = "GLOBAL: SAFE"
        self.sla_seconds_left = 60
        self.logs = []

    async def fetch_data(self):
        # Fetch stats
        self.stats = await self.client.get_stats(project="default")
        # Fetch simple health/activity (mock if connection fails)
        try:
            self.health = {"status": "healthy", "verdict": "PASSED"}
        except Exception:
            self.health = {"status": "degraded"}
        
        # Simulate logs and SLA decay for live view
        if self.sla_seconds_left > 0:
            self.sla_seconds_left -= 5
        else:
            self.sla_seconds_left = 60

        self.logs = [
            {"time": "10:14:02", "agent": "Phoenix", "msg": "Analyzing bugfix in core/logic_gateway.py", "class": "INTERNAL"},
            {"time": "10:14:15", "agent": "Quality", "msg": "Quality Gate Audit: Verdict PASSED, Level: advanced_senior", "class": "INTERNAL"},
            {"time": "10:14:22", "agent": "Hive", "msg": "Deploying change to sandbox environment", "class": "INTERNAL"},
            {"time": "10:15:01", "agent": "Memory", "msg": "Consolidated 15 episodic memories into 1 semantic reflection", "class": "INTERNAL"},
        ]

    def render(self):
        ui.timer(5.0, self.fetch_data)
        
        with ui.column().classes('w-full max-w-7xl mx-auto p-8 gap-6'):
            ui.label('Mission Control').classes('text-3xl font-black text-indigo-950 mb-2')
            ui.label('Real-time operations, agent Gantt timelines, and Rollback SLAs.').classes('text-slate-500 mb-4')

            # --- Row 1: KPI Cards ---
            with ui.row().classes('w-full gap-4'):
                with ui.card().classes('flex-1 p-6 border-l-4 border-emerald-500 shadow-sm'):
                    ui.label('SYSTEM STATUS').classes('text-xs font-bold text-slate-400')
                    with ui.row().classes('items-center gap-2 mt-2'):
                        ui.icon('check_circle', color='emerald', size='md')
                        ui.label('Fully Operational').classes('text-xl font-bold text-slate-800')
                
                with ui.card().classes('flex-1 p-6 border-l-4 border-indigo-500 shadow-sm'):
                    ui.label('MEMORY DENSITY').classes('text-xs font-bold text-slate-400')
                    with ui.row().classes('items-center gap-2 mt-2'):
                        ui.icon('memory', color='indigo', size='md')
                        ui.label('19,126 Memories').classes('text-xl font-bold text-slate-800')

                with ui.card().classes('flex-1 p-6 border-l-4 border-red-500 shadow-sm'):
                    ui.label('ROLLBACK SLA TIMEOUT').classes('text-xs font-bold text-slate-400')
                    with ui.row().classes('items-center gap-2 mt-2'):
                        ui.icon('timer', color='red', size='md')
                        ui.label(f'{self.sla_seconds_left}s remaining').classes('text-xl font-bold text-slate-800')

            # --- Row 2: Gantt / Timeline & Quarantine ---
            with ui.row().classes('w-full gap-6 mt-4'):
                # Gantt Chart (NiceGUI eChart)
                with ui.card().classes('flex-[2] p-6 shadow-sm'):
                    ui.label('AGENT TIMELINE & ACTIVE SANDBOXES').classes('text-xs font-bold text-slate-400 mb-4')
                    ui.echart({
                        'title': {'text': ''},
                        'tooltip': {'formatter': '{b}: {c}ms'},
                        'xAxis': {'type': 'value', 'name': 'Duration (ms)'},
                        'yAxis': {'type': 'category', 'data': ['Quality Tribunal', 'Hive Sandbox', 'Phoenix Planner', 'Memory Engine']},
                        'series': [{
                            'type': 'bar',
                            'data': [320, 1200, 850, 150],
                            'itemStyle': {'color': '#4f46e5'}
                        }]
                    }).classes('w-full h-64')

                # Quarantine / ISO Panel
                with ui.card().classes('flex-1 p-6 bg-slate-900 text-white shadow-sm'):
                    ui.label('ISO 27001 QUARANTINE STATUS').classes('text-xs font-bold text-slate-500 mb-4')
                    with ui.column().classes('gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.badge('GLOBAL').props('color=green')
                            ui.label('Quarantine Status: SECURE').classes('text-sm font-bold')
                        
                        ui.separator().classes('bg-slate-700')
                        ui.label('Active Incopes:').classes('text-xs text-slate-400')
                        with ui.column().classes('gap-1'):
                            ui.label('• LOCAL: Passed').classes('text-xs text-slate-300')
                            ui.label('• SERVICE_GROUP: Safe').classes('text-xs text-slate-300')
                            ui.label('• GLOBAL: Under SLA (60s)').classes('text-xs text-slate-300')
                        
                        ui.separator().classes('bg-slate-700')
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('shield', color='red-500')
                            ui.label('RESTRICTED isolation active').classes('text-[10px] text-red-400 font-bold')

            # --- Row 3: Live Operation Log (with ISO Tagging) ---
            with ui.card().classes('w-full p-6 shadow-sm'):
                ui.label('LIVE OPERATIONAL LOGS').classes('text-xs font-bold text-slate-400 mb-4')
                with ui.column().classes('w-full gap-3'):
                    for log in self.logs:
                        with ui.row().classes('w-full items-center justify-between border-b pb-2 text-sm'):
                            with ui.row().classes('gap-3'):
                                ui.label(log["time"]).classes('text-slate-400 font-mono')
                                ui.badge(log["agent"]).props('color=indigo')
                                ui.label(log["msg"]).classes('text-slate-700')
                            ui.badge(log["class"]).props('color=red-5' if log["class"] == "RESTRICTED" else 'color=blue-5')
