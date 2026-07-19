import html
from nicegui import ui
from utils.api_client import RAESuiteClient

class OpenClawEscalationApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.on_inspect = None
        self.override_reason = ""
        self.incidents = [
            {
                "id": "INC-099",
                "time": "12:08:14",
                "level": "R4 - HIGH RISK",
                "source": "RAE-Quality Tribunal",
                "desc": "AST scan blocked pull request #409: banned package 'sentence-transformers' imported in services/embedding_service.py",
                "rules_violated": "C3 Constitution (Banned ML libraries), Zero Warning Policy"
            },
            {
                "id": "INC-100",
                "time": "14:11:02",
                "level": "R5 - CRITICAL",
                "source": "Autonomy Kernel",
                "desc": "Absolute filesystem path usage detected: '/home/grzegorz-lesniowski/cloud/RAE-Suite/...'",
                "rules_violated": "C6 Constitution (Strict Relative Paths Invariant)"
            }
        ]

    def authorize_override(self, inc_id):
        # Escape input to prevent XSS
        safe_reason = html.escape(self.override_reason.strip())
        if not safe_reason:
            ui.notify("Błąd: Uzasadnienie jest wymagane do autoryzacji obejścia (ISO 27001 / GDPR).", type="negative")
            return
        
        # Simulating digital signature and RFC 3161 timestamping for ISO 27001 compliance
        audit_hash = "SHA256:8f4c9c2b3e8a1d7f0e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7f"
        ui.notify(
            f"Obejście autoryzowane dla {inc_id}.\nPodpis: {audit_hash[:16]}...\nZapisano w Decision Ledger.", 
            type="warning"
        )
        self.override_reason = ""

    def deny_rollback(self, inc_id):
        ui.notify(f"Odrzucono obejście. Uruchamianie automatycznego wycofania zmian dla {inc_id}...", type="info")

    def render(self):
        with ui.column().classes('w-full max-w-7xl mx-auto p-8 gap-y-6'):
            # Red/amber alert block at top - using high contrast colors (red-200)
            with ui.card().classes('w-full p-6 bg-red-950/30 text-white border-l-4 border-red-600 shadow-sm'):
                with ui.row().classes('items-center gap-4'):
                    ui.icon('warning', color='red-500', size='lg')
                    with ui.column().classes('gap-y-1'):
                        ui.label('OPENCLAW ESCALATION DESK').classes('text-xl font-bold text-red-200')
                        ui.label('Manual gate overrides, AST blocks, and constitutional bypass logs.').classes('text-sm text-slate-200')

            with ui.row().classes('w-full gap-6'):
                # Active Incidents
                with ui.card().classes('flex-[2] p-6 bg-slate-900 text-white shadow-sm'):
                    ui.label('ACTIVE TRIBUNAL INCIDENTS').classes('text-xs font-bold text-slate-400 mb-4')
                    with ui.column().classes('w-full gap-y-4'):
                        for inc in self.incidents:
                            card_details = f"**Incident:** `{inc['id']}`\n**Time:** `{inc['time']}`\n**Level:** `{inc['level']}`\n**Source:** `{inc['source']}`\n\n**Description:**\n{inc['desc']}\n\n**Violated rules:**\n{inc['rules_violated']}"
                            
                            # Custom focus indicator and keyboard Space/Enter handlers (WCAG 2.4.7 / 2.1.1)
                            click_handler = lambda c_title=f"Incident {inc['id']}", c_det=card_details: self.on_inspect(c_title, c_det) if self.on_inspect else None
                            
                            with ui.card().classes('w-full p-4 bg-slate-800 border-l-4 border-red-600 cursor-pointer hover:bg-slate-700 focus:outline focus:outline-2 focus:outline-blue-500') \
                                 .props('tabindex=0 aria-label="Incident Details: ' + inc["id"] + '"') \
                                 .on('click', click_handler) \
                                 .on('keydown.enter', click_handler) \
                                 .on('keydown.space', click_handler):
                                with ui.row().classes('w-full items-center justify-between'):
                                    with ui.column().classes('gap-y-1'):
                                        ui.label(inc["id"]).classes('text-sm font-bold text-red-200')
                                        ui.label(inc["level"]).classes('text-xs text-red-300 font-bold')
                                        ui.label(inc["desc"][:80] + "...").classes('text-xs text-slate-300')
                                    ui.badge(inc["source"]).props(f'color=red-9 aria-label="Źródło: {inc["source"]}"')

                # Manual Gate Controls
                with ui.card().classes('flex-grow p-6 bg-slate-900 text-white border border-slate-800 shadow-sm'):
                    ui.label('MANUAL INTERVENTION GATE').classes('text-xs font-bold text-red-200 mb-4')
                    with ui.column().classes('w-full gap-y-4'):
                        ui.label("Resolve incident INC-100 (C6 Path Invariant)").classes('text-sm font-bold')
                        
                        # Added mandatory HTML5 required attributes for compliance (WCAG 3.3.2)
                        reason_input = ui.input(
                            label='Justification Reason (Mandatory)',
                            placeholder='e.g. Temporary path override for legacy migrations test'
                        ).classes('w-full text-white').props('dark required aria-required="true"')
                        reason_input.on('change', lambda: setattr(self, 'override_reason', reason_input.value))

                        with ui.row().classes('w-full gap-4'):
                            ui.button('AUTHORIZE BYPASS', on_click=lambda: self.authorize_override("INC-100")).props('color=red rounded')
                            ui.button('DENY & ROLLBACK', on_click=lambda: self.deny_rollback("INC-100")).props('outline color=slate rounded')
