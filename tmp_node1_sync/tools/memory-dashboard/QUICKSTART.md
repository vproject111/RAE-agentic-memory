# RAE Memory Dashboard - Quick Start Guide

Get the dashboard running in under 5 minutes!

## Prerequisites

- Python 3.9 or higher
- RAE Memory API running at `http://localhost:8000`
- pip package manager

## Installation

### Option 1: Automated Setup (Recommended)

```bash
# Navigate to dashboard directory
cd tools/memory-dashboard

# Run setup script (creates venv, installs deps, starts dashboard)
./run.sh
```

That's it! The dashboard will open at `http://localhost:8501`

### Option 2: Manual Setup

```bash
# Navigate to dashboard directory
cd tools/memory-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp .env.example .env

# Edit .env with your settings (optional)
nano .env

# Start dashboard
streamlit run app.py
```

## Configuration

### Default Configuration

The dashboard works out of the box with these defaults:

```
API URL:     http://localhost:8000
API Key:     default-key
Tenant ID:   default-tenant
Project ID:  default-project
Port:        8501
```

### Custom Configuration

Edit `.env` file to customize:

```bash
RAE_API_URL=http://your-api:8000
RAE_API_KEY=your-api-key
RAE_TENANT_ID=your-tenant
RAE_PROJECT_ID=your-project
DASHBOARD_PORT=8501
```

## First Steps

1. **Open Dashboard**
   - Browser should open automatically
   - Or visit: http://localhost:8501

2. **Configure Connection** (in sidebar)
   - Enter API URL
   - Enter API Key
   - Enter Tenant ID
   - Enter Project ID
   - Click "Connect"

3. **Explore Pages**
   - **Overview**: See statistics and quick analytics
   - **📅 Timeline**: View memory history
   - **🕸️ Knowledge Graph**: Explore relationships
   - **✏️ Memory Editor**: Edit memories
   - **🔍 Query Inspector**: Test queries

## Common Tasks

### View Memory Timeline

1. Click "📅 Timeline" in sidebar
2. Select memory layers (EM, WM, SM, LTM)
3. Adjust time range
4. View scatter plot, heatmap, or table

### Search and Edit Memory

1. Click "✏️ Memory Editor" in sidebar
2. Enter search query
3. Click "Search"
4. Click "Edit" on any result
5. Modify content and tags
6. Click "Save Changes"

### Test a Query

1. Click "🔍 Query Inspector" in sidebar
2. Enter query text
3. Adjust parameters (Top K, reranking)
4. Click "Execute Query"
5. View ranked results and scores

### Explore Knowledge Graph

1. Click "🕸️ Knowledge Graph" in sidebar
2. Adjust graph settings
3. Interact with graph:
   - Drag nodes
   - Scroll to zoom
   - Hover for details
4. Use Relationship Explorer at bottom

## Troubleshooting

### Dashboard won't start

**Problem:** Error when running `./run.sh`

**Solutions:**
```bash
# Make script executable
chmod +x run.sh

# Or run manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### Can't connect to API

**Problem:** "Connection failed" error

**Solutions:**
1. Verify API is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check API URL in sidebar configuration

3. Verify API key and tenant ID

4. Check firewall/network settings

### No data showing

**Problem:** Empty graphs and tables

**Solutions:**
1. Verify memories exist in RAE
2. Check layer filters (select at least one)
3. Increase time range (days back)
4. Click "Refresh" in sidebar

### Slow performance

**Problem:** Dashboard is slow or unresponsive

**Solutions:**
1. Clear cache: Click "Refresh" in sidebar
2. Reduce result limits
3. Limit timeline date range
4. Disable graph physics
5. Close unused browser tabs

## Tips and Tricks

### Keyboard Shortcuts

- `R` - Rerun app (refresh)
- `Ctrl+K` - Clear cache
- `Ctrl+S` - Save (in forms)

### Performance Tips

1. **Use filters** to reduce data load
2. **Enable caching** (automatic by default)
3. **Limit time ranges** on timeline
4. **Disable physics** for large graphs
5. **Export to CSV** for offline analysis

### Data Export

Export data from any page:
- **Timeline**: CSV export button in Table View tab
- **Query Inspector**: CSV export button in Table View tab
- Includes all visible columns

### Batch Operations

For bulk operations, use the Memory Editor:
1. Search with broad query
2. Edit multiple memories sequentially
3. Use consistent tagging

## Advanced Usage

### Custom Filters

Combine multiple filters for precise results:

```
Layer: em, wm
Tags: important, project-x
Source: user-input
```

### Query Comparison

Test different phrasings:
1. Switch to "Comparison Mode"
2. Enter two queries
3. Compare results and overlap
4. Optimize query based on results

### Graph Analysis

Use graph statistics to understand:
- Node connectivity (top connected nodes)
- Entity distribution (node types)
- Relationship patterns (incoming/outgoing)

## Docker Deployment

Quick Docker deployment:

```bash
# Build image
docker build -t rae-dashboard tools/memory-dashboard/

# Run container
docker run -d -p 8501:8501 \
  -e RAE_API_URL=http://host.docker.internal:8000 \
  --name rae-dashboard \
  rae-dashboard
```

Access at: http://localhost:8501

## Support

### Documentation

- **Full README**: `tools/memory-dashboard/README.md`
- **API Reference**: See README API section
- **Summary**: `KIERUNEK_4_SUMMARY.md`

### Getting Help

If you encounter issues:
1. Check troubleshooting section above
2. Review full README
3. Check RAE API logs
4. Report issues with error details

## Next Steps

Once you're comfortable with basics:

1. **Explore all pages** - Each has unique features
2. **Review reflection** - Check project reflection on main page
3. **Customize settings** - Adjust theme in `.streamlit/config.toml`
4. **Set up monitoring** - Track dashboard usage
5. **Enable auth** - Add authentication for production

---

**Need more help?** Read the full [README.md](README.md) for comprehensive documentation.

**Dashboard Version:** 1.0.0
**Last Updated:** 2024
