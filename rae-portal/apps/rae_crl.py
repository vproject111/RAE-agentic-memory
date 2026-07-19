import os
from nicegui import ui
from utils.api_client import RAESuiteClient

class RaeCrlApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.on_inspect = None

    def render(self):
        # We read the RAE_CRL_URL from environment or fallback to localhost:8503
        crl_url = os.environ.get("RAE_CRL_URL", "http://localhost:8503")
        
        with ui.column().classes('w-full p-6 gap-y-4'):
            # WCAG 2.4.6 semantic heading
            with ui.element('h1').classes('text-3xl font-bold text-slate-800'):
                ui.label('Cognitive Research Layer (RAE-CRL)')
            ui.label('Federated memory verification, epistemic DAG conflict analyses, and journal audits.').classes('text-slate-500 mb-2')
            
            # Embed the running RAE-CRL UI container via an iframe
            ui.html(f'''
                <iframe 
                    src="{crl_url}" 
                    title="RAE-CRL Dashboard"
                    style="width: 100%; height: 75vh; border: 2px solid #334155; border-radius: 12px; background: #ffffff;"
                    aria-label="RAE-CRL Interactive Dashboard Console"
                ></iframe>
            ''').classes('w-full')
