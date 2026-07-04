# RAE Node Setup Instructions (for Piotrek & Julka)

This guide explains how to connect a new Worker Node to the ScreenWatcher RAE Cluster via Tailscale.

## 1. Prerequisites
- **Tailscale**: Must be logged into the same network (Tailnet).
- **Python 3.10+**: Required to run the Node Agent.
- **Ollama**: Installed and running (for LLM tasks).
- **NVIDIA GPU**: (RTX 4080) Ensure latest drivers are installed for `nvidia-smi` support.

## 2. Prepare the Agent
Copy the `infra/node_agent` directory from the RAE repository or from the ScreenWatcher project to the target machine.

## 3. Configuration (`config.yaml`)
Create or edit `config.yaml` in the agent directory. Replace `NODE_NAME` with a unique identifier (e.g., `node-piotrek` or `node-julka`).

```yaml
node_id: "NODE_NAME"
rae_endpoint: "http://100.66.252.117:8000" # Central RAE Control Node (Tailscale IP)
heartbeat_interval_sec: 10
ollama_api_url: "http://localhost:11434"
capabilities:
  gpu: true
  vram_gb: 16
  system_ram_gb: 128
  model_support: ["deepseek-coder:33b", "deepseek-coder:6.7b"]
```

## 4. Installation & Launch
Open terminal in the `node_agent` directory:

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# 2. Install dependencies
pip install httpx pyyaml

# 3. Start the agent
python main.py
```

## 5. Verification
Once the agent is running:
1. It will output `Registering at http://100.66.252.117:8000/control/nodes/register...`
2. It should show `Registered successfully as NODE_NAME`.
3. The Node will then appear in the Control Node dashboard and be ready to receive tasks (Inference, Code Cycles, Shell commands).

## Troubleshooting
- **Connectivity**: Ensure you can `ping 100.66.252.117`. If not, check Tailscale connection.
- **Firewall**: Ensure the Node can make outgoing HTTP requests to port 8000 on the Control Node.
- **Ollama**: Verify Ollama is running by visiting `http://localhost:11434` in a browser.
