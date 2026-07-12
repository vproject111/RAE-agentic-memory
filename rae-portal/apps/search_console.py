import asyncio
import httpx
from nicegui import ui
from utils.api_client import RAESuiteClient

class SearchConsoleApp:
    def __init__(self, client: RAESuiteClient):
        self.client = client
        self.query = ""
        self.manifold_mode = "silicon_oracle"
        self.enable_vector = True
        self.enable_semantic = True
        self.enable_graph = False
        self.enable_fulltext = True
        self.enable_rerank = False
        self.results = []
        self.status = "Idle"
        self.total_time_ms = 0
        self.results_container = None

    async def execute_search(self):
        if not self.query:
            return
        self.status = "Searching..."
        self.results = []
        self.update_display()

        # Build payload for hybrid search
        url = f"{self.client.api_url}/v2/search/hybrid"
        payload = {
            "tenant_id": self.client.tenant_id,
            "project": "default",
            "query": self.query,
            "k": 10,
            "enable_vector_search": self.enable_vector,
            "enable_semantic_search": self.enable_semantic,
            "enable_graph_search": self.enable_graph,
            "enable_fulltext_search": self.enable_fulltext,
            "enable_reranking": self.enable_rerank,
            "reranking_model": "nomic-embed-text",
            "graph_max_depth": 3,
            "min_importance": 0.0,
            "manual_weights": None
        }
        headers = {"X-Tenant-Id": self.client.tenant_id}

        async with httpx.AsyncClient() as client:
            try:
                start_time = asyncio.get_event_loop().time()
                r = await client.post(url, json=payload, headers=headers, timeout=15.0)
                end_time = asyncio.get_event_loop().time()
                self.total_time_ms = int((end_time - start_time) * 1000)

                if r.status_code == 200:
                    data = r.json()
                    self.results = data.get("search_result", {}).get("hits", [])
                else:
                    self.results = []
                    ui.notify(f"Search API Error {r.status_code}", type="warning")
            except Exception as e:
                self.results = []
                ui.notify(f"Connection failed: {e}", type="negative")

        self.status = "Idle"
        self.update_display()

    def update_display(self):
        if not self.results_container:
            return
        self.results_container.clear()
        
        with self.results_container:
            if self.status == "Searching...":
                with ui.column().classes('w-full items-center py-12'):
                    ui.spinner('dots', size='lg', color='sky-5')
                    ui.label('Querying Manifolds & Named Vectors...').classes('text-sky-900 font-bold mt-4')
                return

            if self.query:
                with ui.row().classes('w-full items-center justify-between bg-sky-50 p-4 rounded-xl border border-sky-100 mb-6'):
                    ui.label(f'Found {len(self.results)} hits in {self.total_time_ms}ms').classes('text-sky-950 font-bold')
                    ui.badge(f'Math Manifold: {self.manifold_mode.upper()}').props('color=sky')

                if not self.results:
                    with ui.column().classes('w-full items-center py-12'):
                        ui.icon('search_off', size='lg', color='grey')
                        ui.label('No matching memories found in current space.').classes('text-slate-500 mt-2')
                else:
                    with ui.column().classes('w-full gap-4'):
                        for idx, hit in enumerate(self.results):
                            score = hit.get("score", 0.0)
                            content = hit.get("content", hit.get("memory", {}).get("content", ""))
                            layer = hit.get("layer", hit.get("memory", {}).get("layer", "semantic"))
                            source = hit.get("source", hit.get("memory", {}).get("source", "unknown"))
                            
                            with ui.card().classes('w-full p-6 shadow-sm border-l-4 border-sky-400'):
                                with ui.row().classes('w-full items-center justify-between mb-2'):
                                    with ui.row().classes('gap-2 items-center'):
                                        ui.badge(f'#{idx+1}').props('color=sky')
                                        ui.badge(layer.upper()).props('color=indigo-9')
                                        ui.label(f'Source: {source}').classes('text-xs text-slate-500')
                                    ui.label(f'Score: {score:.4f}').classes('text-sm font-black text-sky-950')
                                ui.markdown(content).classes('text-slate-800 leading-relaxed text-sm')

    def render(self):
        with ui.row().classes('w-full gap-8'):
            # Left panel: Strategy selection
            with ui.card().classes('w-80 p-6 bg-slate-50 border-r'):
                ui.label('SEARCH ENGINES').classes('text-xs font-black text-slate-400 mb-4 tracking-widest')
                
                self.vec_chk = ui.checkbox('Vector Similarity', value=self.enable_vector, on_change=lambda e: setattr(self, 'enable_vector', e.value))
                self.sem_chk = ui.checkbox('Semantic Nodes', value=self.enable_semantic, on_change=lambda e: setattr(self, 'enable_semantic', e.value))
                self.graph_chk = ui.checkbox('Graph Traversal', value=self.enable_graph, on_change=lambda e: setattr(self, 'enable_graph', e.value))
                self.ft_chk = ui.checkbox('GIN Full-Text', value=self.enable_fulltext, on_change=lambda e: setattr(self, 'enable_fulltext', e.value))
                self.rr_chk = ui.checkbox('Reranker Pass', value=self.enable_rerank, on_change=lambda e: setattr(self, 'enable_rerank', e.value))

                ui.separator().classes('my-6')
                ui.label('MATH MANIFOLD ARM').classes('text-xs font-black text-slate-400 mb-4 tracking-widest')
                
                self.mode_sel = ui.select({
                    "silicon_oracle": "Silicon Oracle (Default)",
                    "system_1_ib": "System 1: Implicit Behavior",
                    "system_37_hyper": "System 37: Hyperdimensional",
                    "system_41_scalpel": "System 41: Linguistic",
                    "system_100_fluid": "System 100: Fluid",
                    "legacy_416": "Legacy 4.1.6"
                }, value=self.manifold_mode, on_change=lambda e: setattr(self, 'manifold_mode', e.value)).classes('w-full').props('dense outlined')

            # Right panel: query and results
            with ui.column().classes('flex-grow'):
                ui.label('Hybrid Search Console').classes('text-3xl font-black text-slate-800 mb-2')
                ui.label('Query multi-strategy named vectors and compare manifold arms.').classes('text-slate-500 mb-8')

                with ui.row().classes('w-full items-center gap-4 mb-12 bg-white p-6 rounded-2xl shadow-sm border'):
                    query_input = ui.input(
                        label='Ask RAE Memory Space...', 
                        placeholder='e.g. Find all refactoring failures in setup files'
                    ).classes('flex-grow text-lg')
                    
                    # Update internal query upon text input
                    query_input.on('change', lambda: setattr(self, 'query', query_input.value))
                    
                    ui.button('SEARCH', 
                        on_click=self.execute_search
                    ).props('elevated color=sky size=lg rounded')

                self.results_container = ui.column().classes('w-full')
                self.update_display()
