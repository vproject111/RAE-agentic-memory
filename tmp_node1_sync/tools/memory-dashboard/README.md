# RAE Memory Dashboard

Enterprise-grade Streamlit dashboard for visualizing and managing RAE (Reflective Agentic Memory Engine) agent memories.

![RAE Dashboard](https://img.shields.io/badge/Status-Production-green)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)

## Features

### 📊 Overview Dashboard
- Real-time memory statistics across all layers (Episodic, Working, Semantic, Long-term)
- Quick analytics with interactive charts
- Layer distribution visualization
- Top tags word cloud
- Project reflection viewer

### 📅 Timeline Visualization
- Interactive scatter plot of memories over time
- Temporal heatmap showing activity patterns
- Filterable by layer, date range, and tags
- Sortable table view with CSV export
- Detailed memory inspection with pagination

### 🕸️ Knowledge Graph Explorer
- Interactive network graph visualization using PyVis
- Physics-based layout with customizable parameters
- Node type color coding (entity, concept, event, person, project)
- Graph analysis (node distribution, connectivity metrics)
- Relationship explorer for individual nodes

### ✏️ Memory Editor
- **Search Mode**: Find memories by content with advanced filters
- **Edit Mode**: Modify memory content and tags
- **Create Mode**: Manually add new memories
- Full CRUD operations with confirmation dialogs
- Filter by layer, tags, and source

### 🔍 Query Inspector
- **Single Query Mode**: Test queries with detailed score analysis
- **Comparison Mode**: Compare two queries side-by-side
- Score distribution visualization
- Result ranking and sorting
- CSV export of query results
- Query history tracking

## Installation

### Prerequisites

- Python 3.9 or higher
- RAE Memory API running and accessible
- pip package manager

### Quick Start

1. **Clone or navigate to the dashboard directory:**
   ```bash
   cd tools/memory-dashboard
   ```

2. **Run the setup script:**
   ```bash
   ./run.sh
   ```

   This script will:
   - Create a virtual environment
   - Install all dependencies
   - Create `.env` from `.env.example`
   - Launch the dashboard

3. **Access the dashboard:**
   ```
   Open http://localhost:8501 in your browser
   ```

### Manual Installation

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run dashboard
streamlit run app.py
```

## Configuration

### Environment Variables

Create a `.env` file (or copy from `.env.example`):

```bash
# RAE API Connection
RAE_API_URL=http://localhost:8000
RAE_API_KEY=your-api-key
RAE_TENANT_ID=your-tenant-id
RAE_PROJECT_ID=your-project-id

# Dashboard Settings
DASHBOARD_PORT=8501
```

### Streamlit Configuration

Edit `.streamlit/config.toml` to customize:

- Theme colors
- Server settings
- Browser behavior
- Performance options

## Usage

### Connecting to RAE API

1. Open the dashboard sidebar
2. Enter your API URL and credentials
3. Click "Connect"
4. Green status indicator confirms connection

### Viewing Memory Timeline

1. Navigate to "📅 Timeline" page
2. Select memory layers to display
3. Adjust time range (days back)
4. View scatter plot, heatmap, or table
5. Export data as CSV if needed

### Exploring Knowledge Graph

1. Navigate to "🕸️ Knowledge Graph" page
2. Adjust graph settings (physics, node size, edge width)
3. Interact with the graph:
   - Drag nodes to reposition
   - Scroll to zoom
   - Hover for details
   - Click to highlight connections
4. Use Relationship Explorer to view connections for specific nodes

### Editing Memories

1. Navigate to "✏️ Memory Editor" page
2. **Search Mode:**
   - Enter search query
   - Apply filters (layer, tags, source)
   - Click "Edit" on any result
3. **Edit Mode:**
   - Modify content and tags
   - Save changes or delete memory
4. **Create Mode:**
   - Add new memory manually
   - Select layer and add tags

### Testing Queries

1. Navigate to "🔍 Query Inspector" page
2. **Single Query:**
   - Enter query text
   - Adjust parameters (top K, reranking)
   - View ranked results and score distribution
3. **Comparison Mode:**
   - Enter two queries
   - Compare results side-by-side
   - Identify overlapping results (⭐)

## Architecture

### Directory Structure

```
memory-dashboard/
├── app.py                      # Main dashboard application
├── pages/                      # Multi-page app pages
│   ├── 1_📅_Timeline.py
│   ├── 2_🕸️_Knowledge_Graph.py
│   ├── 3_✏️_Memory_Editor.py
│   └── 4_🔍_Query_Inspector.py
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── api_client.py          # RAE API client
│   └── visualizations.py      # Chart and graph helpers
├── .streamlit/                 # Streamlit configuration
│   └── config.toml
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
└── run.sh                     # Startup script
```

### API Client

The `RAEClient` class provides:
- Connection pooling with httpx
- Automatic error handling and retries
- Response caching with TTL
- Comprehensive CRUD operations
- Session management

### Visualizations

Visualization utilities include:
- Timeline scatter plots (Plotly)
- Temporal heatmaps (Plotly)
- Network graphs (PyVis)
- Score distributions (Plotly)
- Layer distribution charts (Plotly)

## Development

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Code Style

The codebase follows:
- PEP 8 style guide
- Type hints for function signatures
- Comprehensive docstrings
- Enterprise-grade error handling

### Adding New Features

1. Create new page in `pages/` directory
2. Use naming convention: `N_emoji_Name.py`
3. Import utilities from `utils/`
4. Apply custom CSS with `apply_custom_css()`
5. Check connection with session state
6. Update README with new features

## Troubleshooting

### Connection Issues

**Problem:** Cannot connect to RAE API

**Solutions:**
- Verify RAE API is running: `curl http://localhost:8000/health`
- Check API URL in configuration
- Verify API key and tenant ID
- Check firewall/network settings

### Performance Issues

**Problem:** Dashboard is slow or unresponsive

**Solutions:**
- Reduce query result limits
- Clear Streamlit cache (click "Refresh" in sidebar)
- Check RAE API performance
- Reduce timeline date range
- Disable physics on knowledge graph

### Graph Not Displaying

**Problem:** Knowledge graph shows empty or error

**Solutions:**
- Verify graph data exists in RAE
- Check browser console for errors
- Ensure PyVis is installed correctly
- Try refreshing the page

### Import Errors

**Problem:** Module not found errors

**Solutions:**
- Verify virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt`
- Check Python version (3.9+ required)

## API Reference

### RAEClient Methods

```python
# Connection
client = RAEClient(api_url, api_key, tenant_id, project_id)
client.test_connection() -> bool

# Statistics
client.get_stats() -> Dict[str, int]

# Memory Operations
client.get_memories(layers, since, limit) -> List[Dict]
client.search_memories(query, top_k, filters) -> List[Dict]
client.query_memory(query, top_k, use_rerank) -> List[Dict]
client.update_memory(memory_id, content, tags) -> bool
client.delete_memory(memory_id) -> bool

# Graph Operations
client.get_knowledge_graph(project) -> Dict[str, Any]

# Reflection
client.get_reflection(project) -> str

# Tags
client.get_all_tags() -> List[str]
```

## Performance Optimization

### Caching

The dashboard uses Streamlit's caching:
- `@st.cache_data(ttl=60)` for statistics
- `@st.cache_data(ttl=30)` for memories
- Manual cache clearing via "Refresh" button

### Best Practices

1. **Limit result sets:** Use appropriate `top_k` and `limit` values
2. **Filter early:** Apply filters to reduce data transfer
3. **Use date ranges:** Limit timeline to relevant periods
4. **Disable physics:** Turn off graph physics for large networks
5. **Export data:** Download CSV for offline analysis

## Security Considerations

### API Keys

- Never commit `.env` file to version control
- Use environment variables for sensitive data
- Rotate API keys regularly
- Use HTTPS in production

### CORS and XSRF

- Enable XSRF protection in `config.toml`
- Configure CORS properly for production
- Use authentication middleware

### Data Privacy

- Memory content may contain sensitive data
- Implement access controls at API level
- Use tenant isolation for multi-tenancy
- Audit memory access logs

## Deployment

### Development

```bash
./run.sh
```

### Production

For production deployment:

1. **Use a production ASGI server:**
   ```bash
   streamlit run app.py --server.port=8501 --server.address=0.0.0.0
   ```

2. **Use environment variables:**
   ```bash
   export RAE_API_URL=https://api.production.com
   export RAE_API_KEY=$(cat /secrets/api-key)
   streamlit run app.py
   ```

3. **Docker deployment:**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["streamlit", "run", "app.py"]
   ```

4. **Reverse proxy (nginx):**
   ```nginx
   location /dashboard/ {
       proxy_pass http://localhost:8501/;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }
   ```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Follow code style guidelines
4. Add tests for new features
5. Update documentation
6. Submit a pull request

## License

Enterprise license - see main RAE project for details.

## Support

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/your-org/rae-agentic-memory/issues
- Documentation: https://docs.rae-memory.dev
- Email: support@rae-memory.dev

## Changelog

### v1.0.0 (2024)
- Initial enterprise release
- Timeline visualization
- Knowledge graph explorer
- Memory editor
- Query inspector
- Multi-tenancy support
- Comprehensive documentation

## Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/) - Dashboard framework
- [Plotly](https://plotly.com/) - Interactive charts
- [PyVis](https://pyvis.readthedocs.io/) - Network graphs
- [httpx](https://www.python-httpx.org/) - HTTP client
- [pandas](https://pandas.pydata.org/) - Data processing

---

**RAE Memory Dashboard** - Enterprise Memory Visualization and Management
