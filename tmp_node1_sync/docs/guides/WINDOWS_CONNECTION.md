# How to Connect Gemini (Windows) to RAE (Linux)

This guide explains how to connect a Gemini agent running on a Windows machine to the RAE instance running on this Linux host.

## 1. Network Connection

**Preferred Method: Tailscale (VPN)**
This is the most secure and reliable method, as it bypasses local firewall and NAT issues.

- **RAE Host Address**: `http://100.66.252.117:8000`
- **Dashboard**: `http://100.66.252.117:8501`

**Alternative Method: Local LAN**
Use this if both machines are on the same WiFi/Ethernet network.

- **RAE Host Address**: `http://192.168.18.86:8000`
- **Dashboard**: `http://192.168.18.86:8501`

## 2. Configuration for Windows Agent

If you are running a Gemini agent script on Windows, ensure it points to the RAE API URL.

**Example (.env on Windows):**
```env
RAE_API_URL=http://100.66.252.117:8000
```

## 3. CORS Settings (Important)

To facilitate this connection, the `ALLOWED_ORIGINS` setting on RAE has been temporarily set to `*`.
This allows requests from any origin (including `http://localhost` on Windows).

**Status**: ✅ Configured in `docker-compose.yml`.

## 4. Troubleshooting

If connection fails:
1. **Ping**: Open CMD on Windows and run `ping 100.66.252.117`.
2. **Browser Check**: Open `http://100.66.252.117:8000/health` in a browser on Windows. You should see `{"status":"healthy"}`.
3. **Firewall**: Ensure Linux firewall isn't blocking port 8000 (Docker usually handles this automatically).

## 5. Experiment Log

- **Date**: 2025-12-24
- **Objective**: Expose RAE to Windows client.
- **Action**: Updated `docker-compose.yml` to allow `ALLOWED_ORIGINS=["*"]`.
- **Outcome**: Service restarted and listening on all interfaces (0.0.0.0).
