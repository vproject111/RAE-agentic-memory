# Remote Node Connection Troubleshooting

## Active Node: kubus-gpu-01
**Status:** Connected (2025-12-23)
**Control Node IP:** 100.66.252.117 (Tailscale)
**Compute Node IP:** 100.68.166.117 (Tailscale)

## Resolution Summary
The connection was established after:
1. Both machines were moved to the same Tailscale network (`koniczyek@`).
2. The agent config on `node1` was updated to `kubus-gpu-01`.
3. The `rae_endpoint` was set to the correct Tailscale IP of the control node.

## Root Cause
The node is running a legacy or incorrect script `auto_runner.py` which attempts to detect user activity via X11 (`xprintidle`). This fails when running as a headless systemd service.

## Resolution Procedure

1.  **Stop the Service**:
    ```bash
    sudo systemctl stop rae-node
    ```

2.  **Deploy Correct Agent**:
    Ensure `/opt/rae-node/agent/main.py` matches the version in `infra/node_agent/main.py` from the repo.

3.  **Fix Systemd Service**:
    Edit `/etc/systemd/system/rae-node.service`:
    ```ini
    [Service]
    # CHANGE THIS LINE:
    # ExecStart=/usr/bin/python3 /opt/rae-node/agent/auto_runner.py
    # TO THIS:
    ExecStart=/usr/bin/python3 /opt/rae-node/agent/main.py
    ```

4.  **Reload and Restart**:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl restart rae-node
    ```

5.  **Verify**:
    ```bash
    sudo systemctl status rae-node
    journalctl -u rae-node -f
    ```
    Logs should show: `Registered successfully` and `Heartbeat sent`.