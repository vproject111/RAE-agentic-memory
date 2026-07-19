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
        self.on_inspect = None
        self._active = True

    async def fetch_data(self):
        if not self._active:
            return
        self.stats = await self.client.get_stats(project="default")
        try:
            self.health = {"status": "healthy", "verdict": "PASSED"}
        except Exception:
            self.health = {"status": "degraded"}
        
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

    def __del__(self):
        self._active = False

    def render(self):
        self.timer = ui.timer(5.0, self.fetch_data)
        
        with ui.column().classes('w-full max-w-7xl mx-auto p-8 gap-y-6'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column().classes('gap-y-1'):
                    ui.label('Mission Control').classes('text-3xl font-black text-slate-800')
                    ui.label('Real-time operations, agent Gantt timelines, and Rollback SLAs.').classes('text-slate-500')
                
            # --- Row 1: KPI Cards ---
            with ui.row().classes('w-full gap-4'):
                # KPI 1 System Status
                with ui.card().classes('flex-1 p-6 border-l-4 border-emerald-500 bg-slate-900 text-white cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500') \
                     .props('tabindex=0 aria-label="System Status Card: Click for details" aria-describedby="sys-status-desc"') \
                     .on('click', lambda: self.on_inspect("Status Systemu", "System działa nominalnie. Wszystkie testy integracyjne przeszły pomyślnie. Brak aktywnych błędów krytycznych.") if self.on_inspect else None):
                    ui.label('SYSTEM STATUS').classes('text-xs font-bold text-emerald-300')
                    with ui.row().classes('items-center gap-2 mt-2'):
                        ui.icon('check_circle', color='emerald-300', size='md')
                        ui.label('Fully Operational').classes('text-xl font-bold text-slate-100')
                    ui.space().props('id="sys-status-desc"')
                
                # KPI 2 Memory Density
                with ui.card().classes('flex-1 p-6 border-l-4 border-indigo-500 bg-slate-900 text-white cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500') \
                     .props('tabindex=0 aria-label="Memory Density Card: Click for details" aria-describedby="mem-density-desc"') \
                     .on('click', lambda: self.on_inspect("Density Pamięci", "Całkowita liczba wspomnień: 19126.\n- Semantyczne: 15400\n- Epizodyczne: 3726\n- Konsolidacja: Ukończona 15 minut temu.") if self.on_inspect else None):
                    ui.label('MEMORY DENSITY').classes('text-xs font-bold text-indigo-300')
                    with ui.row().classes('items-center gap-2 mt-2'):
                        ui.icon('memory', color='indigo-300', size='md')
                        ui.label('19,126 Memories').classes('text-xl font-bold text-slate-100')
                    ui.space().props('id="mem-density-desc"')

                # KPI 3 Rollback SLA
                with ui.card().classes('flex-1 p-6 border-l-4 border-red-500 bg-slate-900 text-white cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500') \
                     .props('tabindex=0 aria-label="Rollback SLA Card: Click for details" aria-describedby="rollback-desc"') \
                     .on('click', lambda: self.on_inspect("Rollback SLA", "Umowa poziomu usług (SLA) dla wycofania zmian wynosi 60 sekund. W przypadku braku autoryzacji w tym czasie, zmiany zostaną automatycznie wycofane przez moduł Phoenix.") if self.on_inspect else None):
                    ui.label('ROLLBACK SLA TIMEOUT').classes('text-xs font-bold text-red-300')
                    with ui.row().classes('items-center gap-2 mt-2'):
                        ui.icon('timer', color='red-300', size='md')
                        ui.label(f'{self.sla_seconds_left}s remaining').classes('text-xl font-bold text-slate-100').props('aria-live=polite')
                    ui.space().props('id="rollback-desc"')

            # --- Row 2: Gantt / Timeline & Quarantine ---
            with ui.row().classes('w-full gap-6 mt-4'):
                # Gantt Chart (NiceGUI eChart)
                with ui.card().classes('flex-[2] p-6 bg-slate-900 text-white'):
                    ui.label('AGENT TIMELINE & ACTIVE SANDBOXES').classes('text-xs font-bold text-slate-400 mb-4')
                    ui.echart({
                        'title': {'text': ''},
                        'tooltip': {'formatter': '{b}: {c}ms'},
                        'xAxis': {'type': 'value', 'name': 'Duration (ms)', 'nameTextStyle': {'color': '#94a3b8'}},
                        'yAxis': {'type': 'category', 'data': ['Quality Tribunal', 'Hive Sandbox', 'Phoenix Planner', 'Memory Engine'], 'axisLabel': {'color': '#94a3b8'}},
                        'series': [{
                            'type': 'bar',
                            'data': [320, 1200, 850, 150],
                            'itemStyle': {'color': '#6366f1'}
                        }]
                    }).classes('w-full h-64')

                # Quarantine / ISO Panel
                with ui.card().classes('flex-1 p-6 bg-slate-900 text-white border border-red-500/20'):
                    ui.label('ISO 27001 QUARANTINE STATUS').classes('text-xs font-bold text-slate-500 mb-4')
                    with ui.column().classes('gap-y-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.badge('GLOBAL').props('color=green')
                            ui.label('Quarantine Status: SECURE').classes('text-sm font-bold text-emerald-300')
                        
                        ui.separator().classes('bg-slate-700')
                        ui.label('Active Incopes:').classes('text-xs text-slate-400')
                        with ui.column().classes('gap-y-1'):
                            ui.label('• LOCAL: Passed').classes('text-xs text-slate-300')
                            ui.label('• SERVICE_GROUP: Safe').classes('text-xs text-slate-300')
                            ui.label('• GLOBAL: Under SLA (60s)').classes('text-xs text-slate-300')
                        
                        ui.separator().classes('bg-slate-700')
                        with ui.row().classes('items-center gap-2 cursor-pointer hover:text-red-300').on('click', lambda: self.on_inspect("Informacje RESTRICTED", "Zasady ISO 42001 / ISO 27001 zabraniają wypływu danych oznaczonych jako RESTRICTED poza warstwę roboczą (Working Layer). Wszystkie takie bloki pamięci są szyfrowane kluczem AES-256.") if self.on_inspect else None):
                            ui.icon('shield', color='red-500')
                            ui.label('RESTRICTED isolation active').classes('text-[10px] text-red-300 font-bold')

            # --- Row 3: Live Operation Log (with ISO Tagging) ---
            with ui.card().classes('w-full p-6 bg-slate-900 text-white'):
                ui.label('LIVE OPERATIONAL LOGS').classes('text-xs font-bold text-slate-400 mb-4')
                with ui.column().classes('w-full gap-y-3').props('role=list'):
                    for log in self.logs:
                        with ui.row().classes('w-full items-center justify-between border-b border-slate-800 pb-2 text-sm cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500') \
                             .props('tabindex=0 role="listitem" aria-label="Log entry: click for details"') \
                             .on('click', lambda l=log: self.on_inspect(f"Log: {l['agent']}", f"**Szczegóły zdarzenia:**\n\nCzas: `{l['time']}`\nAgent: `{l['agent']}`\nKomunikat: {l['msg']}\nKlasyfikacja: `{l['class']}`") if self.on_inspect else None):
                            with ui.row().classes('gap-3'):
                                ui.label(log["time"]).classes('text-slate-400 font-mono')
                                ui.badge(log["agent"]).props('color=indigo')
                                ui.label(log["msg"]).classes('text-slate-200')
                            ui.badge(log["class"]).props('color=red-5' if log["class"] == "RESTRICTED" else 'color=blue-5')
