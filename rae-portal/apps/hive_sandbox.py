from nicegui import ui
from utils.api_client import RAESuiteClient

class HiveSandboxApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.on_inspect = None
        self.sandboxes = [
            {
                "id": "SBX-9982",
                "project": "default-lab",
                "container": "rae-sandbox-worker-1",
                "cpu_usage": "14%",
                "mem_usage": "112MB/512MB",
                "manifest_status": "VALID",
                "sbom_signature": "VERIFIED (Cosign)",
                "details": "Active git-worktree sandbox. Network constraints: Default-deny egress active. Trivy reports 0 vulnerability hits."
            },
            {
                "id": "SBX-9983",
                "project": "civic-evidence",
                "container": "rae-sandbox-worker-2",
                "cpu_usage": "2%",
                "mem_usage": "48MB/512MB",
                "manifest_status": "VALID",
                "sbom_signature": "VERIFIED (Cosign)",
                "details": "Suspended git-worktree sandbox. Locked resources."
            }
        ]

    def render(self):
        with ui.column().classes('w-full max-w-7xl mx-auto p-8 gap-y-6'):
            ui.label('Hive Sandboxes & Worktrees').classes('text-3xl font-black text-slate-800 mb-2')
            ui.label('Isolated OCI container runtimes, SBOM validations, and resources cgroups.').classes('text-slate-500 mb-4')

            with ui.row().classes('w-full gap-6'):
                # Active Sandboxes Table
                with ui.card().classes('w-full p-6 bg-slate-900 text-white shadow-sm'):
                    ui.label('ACTIVE SANDBOX RUNTIMES').classes('text-xs font-bold text-slate-400 mb-4')
                    with ui.column().classes('w-full gap-y-4').props('role=list'):
                        for sbx in self.sandboxes:
                            card_details = f"**Sandbox:** `{sbx['id']}`\n**Container:** `{sbx['container']}`\n**CPU:** `{sbx['cpu_usage']}`\n**Memory:** `{sbx['mem_usage']}`\n**Manifest:** `{sbx['manifest_status']}`\n**SBOM:** `{sbx['sbom_signature']}`\n\n**Details:**\n{sbx['details']}"
                            with ui.row().classes('w-full items-center justify-between border-b border-slate-800 pb-3 text-sm cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500') \
                                 .props('tabindex=0 role="listitem" aria-label="Sandbox runtime: click for details"') \
                                 .on('click', lambda s_title=f"Sandbox {sbx['id']}", s_det=card_details: self.on_inspect(s_title, s_det) if self.on_inspect else None):
                                with ui.row().classes('gap-4'):
                                    ui.badge(sbx["id"]).props('color=emerald')
                                    ui.label(sbx["container"]).classes('font-mono font-bold text-slate-200')
                                    ui.label(f'CPU: {sbx["cpu_usage"]}').classes('text-xs text-slate-400')
                                    ui.label(f'Memory: {sbx["mem_usage"]}').classes('text-xs text-slate-400')
                                with ui.row().classes('gap-2'):
                                    ui.badge(sbx["manifest_status"]).props('color=green-9')
                                    ui.badge(sbx["sbom_signature"]).props('color=blue-9')
