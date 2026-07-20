import hashlib

from nicegui import ui


def create_module_header(title: str, description: str, client, rls_status="PROTECTED"):
    """
    Standard reusable header component for RAE Suite Portal modules.
    Enforces ISO 27001 Multi-tenant Privacy and RLS Protection visual indications.
    """
    tenant_id = client.tenant_id if client else "00000000-0000-0000-0000-000000000000"
    salt = "rae_portal_salt_2026"
    tenant_hash = hashlib.sha256(f"{tenant_id}-{salt}".encode()).hexdigest()[:8]

    with ui.row().classes(
        "w-full flex-wrap gap-4 justify-between items-center pb-4 border-b border-slate-200/50 mb-2"
    ):
        with ui.column().classes("gap-y-1"):
            ui.label(title).classes("text-3xl font-black text-slate-800")
            ui.label(description).classes("text-slate-500 text-sm")
        with ui.row().classes("gap-2 items-center"):
            ui.icon(
                "shield",
                color="emerald" if rls_status == "PROTECTED" else "red",
                size="sm",
            )
            ui.badge(f"RLS: {rls_status}").props(
                f'color={"emerald" if rls_status == "PROTECTED" else "red"}'
            )
            ui.badge(f"TENANT: {tenant_hash.upper()}").props("color=slate")
