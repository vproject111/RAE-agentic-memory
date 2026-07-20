import asyncio
from nicegui import ui
from utils.api_client import RAESuiteClient

class MeshFederationApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.peers = []
        self.peer_statuses = {}  # peer_id -> status dict
        self.invite_code = ""
        self.on_inspect = None

    async def load_data(self):
        try:
            self.peers = await self.client.list_mesh_peers()
            for p in self.peers:
                pid = p.get("peer_id")
                if pid:
                    status = await self.client.get_mesh_peer_status(pid)
                    self.peer_statuses[pid] = status
            ui.update()
        except Exception as e:
            ui.notify(f"Failed to load peers: {e}", type="negative")

    async def create_invite(self, host_url: str):
        if not host_url:
            ui.notify("Host URL is required", type="warning")
            return
        res = await self.client.create_mesh_invite(host_url)
        if "invite_code" in res:
            self.invite_code = res["invite_code"]
            ui.notify("Invite code generated successfully!", type="positive")
            ui.update()
        else:
            ui.notify(f"Failed to generate invite: {res.get('error', 'unknown error')}", type="negative")

    async def join_peer(self, code: str, peer_id: str, public_url: str, name: str):
        if not code or not peer_id or not public_url or not name:
            ui.notify("All fields are required to join a peer", type="warning")
            return
        ui.notify("Initiating secure P2P handshake...", type="info")
        res = await self.client.join_mesh(code, peer_id, public_url, name)
        if "status" in res and res["status"] == "connected":
            ui.notify(f"Connected to host peer {res.get('host_peer_id')}!", type="positive")
            await self.load_data()
        else:
            ui.notify(f"Failed to join peer: {res.get('error', 'unknown error')}", type="negative")

    async def register_peer_manually(self, peer_id: str, name: str, url: str, token: str, transport_type: str):
        if not peer_id or not name or not url or not token:
            ui.notify("All fields are required to register a peer manually", type="warning")
            return
        res = await self.client.register_mesh_peer(peer_id, name, url, token, transport_type)
        if "status" in res and res["status"] == "success":
            ui.notify(f"Peer {peer_id} registered/updated manually!", type="positive")
            await self.load_data()
        else:
            ui.notify(f"Failed to register peer: {res.get('error', 'unknown error')}", type="negative")

    async def manual_sync(self, peer_id: str):
        ui.notify(f"Starting manual sync for peer {peer_id}...", type="info")
        res = await self.client.trigger_mesh_peer_sync(peer_id)
        if "status" in res and res["status"] == "success":
            mem_count = res.get("synced_memories", 0)
            ui.notify(f"Sync complete! Synced {mem_count} memories.", type="positive")
            await self.load_data()
        else:
            ui.notify(f"Sync failed: {res.get('error', 'unknown error')}", type="negative")

    async def revoke_peer(self, peer_id: str):
        res = await self.client.revoke_mesh_peer(peer_id)
        if "status" in res and res["status"] == "success":
            ui.notify(f"Peer {peer_id} revoked successfully.", type="positive")
            await self.load_data()
        else:
            ui.notify(f"Failed to revoke peer: {res.get('error', 'unknown error')}", type="negative")

    def render(self):
        # Trigger data loading in background
        asyncio.create_task(self.load_data())

        with ui.column().classes('w-full max-w-7xl mx-auto p-8 gap-y-6'):
            ui.label('Mesh Federation & P2P Trust').classes('text-3xl font-black text-slate-800 mb-2')
            ui.label('Configure secure peer-to-peer relationships, transport routing, and manage decentralized memory synchronization.').classes('text-slate-500 mb-4')

            # --- Row 1: Peer Configuration (Invite / Join / Register) ---
            with ui.row().classes('w-full gap-6'):
                # Box 1: Create Invite Code
                with ui.card().classes('flex-1 p-6 bg-slate-900 text-white border border-slate-850 shadow-sm'):
                    ui.label('GENERATE INVITE CODE (HOST)').classes('text-xs font-bold text-slate-400 mb-4')
                    host_url_input = ui.input(label='Host URL (our endpoint)', placeholder='http://my-node-url:8000').classes('w-full q-mb-md').props('dark outlined')
                    ui.button('Generate Invite', on_click=lambda: self.create_invite(host_url_input.value)).props('color=blue').classes('w-full')
                    
                    # Display invite code if created
                    with ui.column().classes('w-full q-mt-md gap-1').bind_visibility_from(self, 'invite_code'):
                        ui.label('Share this invite code:').classes('text-xs text-slate-400')
                        ui.input(value='').bind_value_from(self, 'invite_code').classes('w-full font-mono text-xs').props('dark outlined readonly')

                # Box 2: Join Peer using Invite
                with ui.card().classes('flex-1 p-6 bg-slate-900 text-white border border-slate-850 shadow-sm'):
                    ui.label('JOIN PEER (CLIENT)').classes('text-xs font-bold text-slate-400 mb-4')
                    invite_code_input = ui.input(label='Invite Code').classes('w-full q-mb-xs').props('dark outlined')
                    join_peer_id = ui.input(label='Own Peer ID', placeholder='e.g., node-2').classes('w-full q-mb-xs').props('dark outlined')
                    join_pub_url = ui.input(label='Own Public URL', placeholder='http://node-2-url:8000').classes('w-full q-mb-xs').props('dark outlined')
                    join_name = ui.input(label='Own Display Name', placeholder='e.g., Node 2').classes('w-full q-mb-md').props('dark outlined')
                    ui.button('Join Mesh Network', on_click=lambda: self.join_peer(
                        invite_code_input.value, join_peer_id.value, join_pub_url.value, join_name.value
                    )).props('color=sky').classes('w-full')

                # Box 3: Configure Transport & Direct Register
                with ui.card().classes('flex-1 p-6 bg-slate-900 text-white border border-slate-850 shadow-sm'):
                    ui.label('MANUAL PEER SETUP').classes('text-xs font-bold text-slate-400 mb-4')
                    manual_peer_id = ui.input(label='Peer ID').classes('w-full q-mb-xs').props('dark outlined')
                    manual_name = ui.input(label='Peer Name').classes('w-full q-mb-xs').props('dark outlined')
                    manual_url = ui.input(label='Peer URL').classes('w-full q-mb-xs').props('dark outlined')
                    manual_token = ui.input(label='Auth Token', type='password').classes('w-full q-mb-xs').props('dark outlined')
                    
                    # Choose Transport type
                    transport_select = ui.select(
                        options={
                            'http': 'Tailscale / VPN (Direct HTTP)',
                            'ssh': 'Reverse SSH Tunnel',
                            'tor': 'Tor SOCKS5h (.onion)',
                            'relay': 'NATS / Matrix Relay Broker'
                        },
                        value='http',
                        label='Transport Protocol'
                    ).classes('w-full q-mb-md').props('dark outlined')
                    
                    ui.button('Save Peer Configuration', on_click=lambda: self.register_peer_manually(
                        manual_peer_id.value, manual_name.value, manual_url.value, manual_token.value, transport_select.value
                    )).props('color=teal').classes('w-full')

            # --- Row 2: Status Grid & Peers Tabela ---
            with ui.card().classes('w-full p-6 bg-slate-900 text-white shadow-sm'):
                with ui.row().classes('w-full justify-between items-center mb-6'):
                    ui.label('CONNECTED PEERS & SYNCHRONIZATION LEDGER').classes('text-xs font-bold text-slate-400')
                    ui.button('Refresh Status', icon='refresh', on_click=self.load_data).props('flat color=blue')

                if not self.peers:
                    ui.label('No peers connected yet. Use invite/join to build peer-to-peer trust.').classes('text-sm text-slate-400 italic q-pa-md')
                else:
                    with ui.column().classes('w-full gap-y-4').props('role=list'):
                        for peer in self.peers:
                            pid = peer.get("peer_id")
                            status_info = self.peer_statuses.get(pid, {})
                            
                            status = status_info.get("status", "offline")
                            latency = status_info.get("latency_ms", -1)
                            stats = status_info.get("sync_stats", {})
                            success_count = stats.get("success_count", 0)
                            failed_count = stats.get("failed_count", 0)
                            last_sync = stats.get("last_synced_at", "Never")
                            
                            transport = peer.get("transport_type", "http").upper()
                            
                            card_details = f"**Peer ID:** `{pid}`\n**Name:** `{peer.get('name')}`\n**Endpoint URL:** `{peer.get('url')}`\n**Transport:** `{transport}`\n**Status:** `{status.upper()}`\n**Latency:** `{latency} ms`"
                            
                            with ui.row().classes('w-full items-center justify-between border-b border-slate-800 pb-3 text-sm cursor-pointer hover:bg-slate-800 focus:outline focus:outline-2 focus:outline-blue-500') \
                                 .props('tabindex=0 role="listitem" aria-label="Peer details: click for more info"') \
                                 .on('click', lambda p_title=f"Peer {pid}", p_det=card_details: self.on_inspect(p_title, p_det) if self.on_inspect else None):
                                
                                with ui.column().classes('gap-y-1'):
                                    with ui.row().classes('gap-2 items-center'):
                                        ui.badge(pid).props('color=blue')
                                        ui.badge(transport).props('color=slate')
                                        if status == "online":
                                            ui.badge(f"ONLINE · {latency}ms").props('color=teal')
                                        else:
                                            ui.badge("OFFLINE").props('color=red')
                                    ui.label(peer.get("name", "Unnamed Peer")).classes('text-slate-200 font-medium')
                                    ui.label(peer.get("url")).classes('text-xs text-slate-400 font-mono')
                                    
                                with ui.row().classes('items-center gap-6'):
                                    with ui.column().classes('items-end'):
                                        ui.label(f'Success: {success_count} · Failed: {failed_count}').classes('text-xs font-bold text-slate-300')
                                        ui.label(f'Last Synced: {last_sync}').classes('text-[10px] text-slate-400')
                                        
                                    with ui.row().classes('gap-2'):
                                        ui.button(
                                            'Sync Now', 
                                            icon='sync',
                                            on_click=lambda p_id=pid: self.manual_sync(p_id)
                                        ).props('flat color=teal dense')
                                        ui.button(
                                            'Revoke', 
                                            icon='delete',
                                            on_click=lambda p_id=pid: self.revoke_peer(p_id)
                                        ).props('flat color=red dense')
