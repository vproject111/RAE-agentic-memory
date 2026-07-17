import os
import sys
from nicegui import ui

# Add current directory to path for modules
sys.path.append(os.path.dirname(__file__))

from utils.api_client import RAESuiteClient
from apps.oracle import OracleApp
from apps.wizard import ProceduralWizard
from apps.mozilla import MozillaApp
from apps.mission_control import MissionControlApp
from apps.search_console import SearchConsoleApp
from apps.decay_retention import DecayRetentionApp
from apps.evolution_lab import EvolutionLabApp

# --- Initialization ---
client = RAESuiteClient()
oracle_app = OracleApp(client)
wizard_app = ProceduralWizard(client)
mozilla_app = MozillaApp(client)
mission_control_app = MissionControlApp(client)
search_console_app = SearchConsoleApp(client)
decay_retention_app = DecayRetentionApp(client)
evolution_lab_app = EvolutionLabApp(client)

class RAESuitePortal:
    def __init__(self):
        self.current_page = "mission_control"
        self.system_profile = "Detecting..."
        
        # Models Categorized by $ cost, versions and hardware warnings
        self.model_options = {
            'local_qwen_optimized': 'Local: QWEN 3.5 9B [Best]',
            'local_phi': 'Local: Phi-3 Mini (Fast)',
            'premium_openai': '$ GPT-4o-mini (Stable)',
            'premium_anthropic': '284352 Claude 3.5 Sonnet'
        }
        
    async def detect_system(self):
        stats = await client.get_stats()
        engine_info = stats.get("statistics", {}).get("engine", "RAE")
        self.system_profile = f"Active: {engine_info}"
        ui.update()

    def set_page(self, name: str):
        self.current_page = name
        ui.update()

    def render(self):
        ui.colors(primary='#1e293b', secondary='#64748b', accent='#3b82f6')
        
        with ui.header().classes('items-center justify-between bg-slate-900 text-white p-4 shadow-xl'):
            with ui.row().classes('items-center gap-4'):
                ui.icon('hub', size='md', color='blue-400')
                ui.label('RAE SUITE PORTAL').classes('text-2xl font-black tracking-tighter')
                ui.badge().bind_text_from(self, 'system_profile').props('outline color=blue-400').classes('ml-2 text-[10px]')
            
            with ui.row().classes('items-center gap-6'):
                self.model_select = ui.select(
                    options=self.model_options, 
                    value="local_qwen_optimized", 
                    label="Brain Selection"
                ).classes("w-96").props('dark dense outlined color=white')
                
                self.source_select = ui.select(
                    options={
                        "default": "Standard Knowledge",
                        "grafana_analytics": "Industrial Metrics",
                        "corp_procedures": "Procedural Docs",
                        "mozilla_civic": "Civic Evidence"
                    }, 
                    value="default", 
                    label="Active Context"
                ).classes("w-64").props('dark dense outlined color=white')

        with ui.left_drawer(value=True).classes('bg-slate-50 border-r p-6'):
            ui.label('SUITE DASHBOARD').classes('text-xs font-bold text-slate-400 mb-4 uppercase tracking-widest')
            with ui.column().classes('w-full gap-2 mb-6'):
                ui.button('Mission Control', icon='dashboard', 
                          on_click=lambda: self.set_page('mission_control')).props(f'flat align=left {"color=indigo" if self.current_page=="mission_control" else ""}').classes('w-full')
                ui.button('Search Console', icon='search', 
                          on_click=lambda: self.set_page('search_console')).props(f'flat align=left {"color=sky" if self.current_page=="search_console" else ""}').classes('w-full')
                ui.button('Decay & Retention', icon='hourglass_empty', 
                          on_click=lambda: self.set_page('decay_retention')).props(f'flat align=left {"color=teal" if self.current_page=="decay_retention" else ""}').classes('w-full')
                ui.button('Evolution Lab', icon='science', 
                          on_click=lambda: self.set_page('evolution_lab')).props(f'flat align=left {"color=purple" if self.current_page=="evolution_lab" else ""}').classes('w-full')

            ui.label('CAPABILITIES').classes('text-xs font-bold text-slate-400 mb-4 uppercase tracking-widest')
            with ui.column().classes('w-full gap-2'):
                ui.button('Industrial Oracle', icon='psychology', 
                          on_click=lambda: self.set_page('oracle')).props(f'flat align=left {"color=blue" if self.current_page=="oracle" else ""}').classes('w-full')
                ui.button('Procedural Wizard', icon='auto_fix_high', 
                          on_click=lambda: self.set_page('wizard')).props(f'flat align=left {"color=amber-9" if self.current_page=="wizard" else ""}').classes('w-full')
                ui.button('Civic Node', icon='shield', 
                          on_click=lambda: self.set_page('mozilla')).props(f'flat align=left {"color=emerald" if self.current_page=="mozilla" else ""}').classes('w-full')
            
            ui.separator().classes('my-8')
            ui.label('TIER GUIDE').classes('text-[10px] font-black text-slate-400 mb-2')
            ui.label('$ Budget | $$ Advanced | $$$ Research').classes('text-[9px] text-slate-500 italic')
            ui.label('[GPU-needed] = local / heavy').classes('text-[9px] text-red-400 italic mt-1')

        @ui.refreshable
        def content_router():
            if self.current_page == "mission_control":
                mission_control_app.render()
            elif self.current_page == "search_console":
                search_console_app.render()
            elif self.current_page == "decay_retention":
                decay_retention_app.render()
            elif self.current_page == "evolution_lab":
                evolution_lab_app.render()
            elif self.current_page == "oracle":
                oracle_app.render(self.model_select, self.source_select)
            elif self.current_page == "wizard":
                wizard_app.render(self.model_select)
            elif self.current_page == "mozilla":
                mozilla_app.render(self.model_select)

        content_router()
        ui.timer(0.1, content_router.refresh)
        ui.timer(2.0, self.detect_system, once=True)

@ui.page('/')
def main_portal():
    portal = RAESuitePortal()
    portal.render()

if __name__ in {"__main__", "main"}:
    ui.run(title="RAE Suite Portal Quantum", port=8080, reload=False, dark=False)
