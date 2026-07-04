RAE_COMPUTE_NODE_GEMINI_EXECUTION.md

(Instrukcja dla Kubusia i Julki: „uruchom Gemini i zrób dokładnie to”)

# RAE Compute Node – Gemini Execution Guide

This document describes EXACTLY how to prepare a personal Linux machine
(Kubuś / Julka) as a TEMPORARY RAE COMPUTE NODE using Gemini CLI.

Gemini is used ONLY as an execution assistant.
Gemini MUST NOT:
- redesign architecture
- change APIs
- add features
- optimize beyond instructions

Gemini executes steps verbatim.

---

## 0. Role Definition (IMPORTANT – READ FIRST)

This machine is a TEMPORARY COMPUTE NODE.

It:
- executes tasks
- runs local LLMs
- can be turned off at any time

It does NOT:
- store memory
- access RAE databases
- make decisions
- modify architecture

Gemini acts as a SYSTEM INSTALLER + SCRIPT EXECUTOR.

---

## 1. Preconditions

- Linux (Ubuntu 22.04+)
- NVIDIA GPU (RTX 4080 class)
- User has sudo access
- Internet access available
- No sensitive company data on this machine

---

## 2. Install Gemini CLI

### Step 2.1 – Node.js (required)

```bash
node --version


If Node < 20:

curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y


Verify:

node --version
npm --version

Step 2.2 – Install Gemini CLI
npm install -g @google/gemini-cli


Verify:

gemini --version


Login if required.

3. Install Base System Dependencies
Gemini PROMPT (COPY & PASTE)
You are operating on a Linux machine that will act as a TEMPORARY RAE COMPUTE NODE.

Perform ONLY the following tasks:
1. Update the system
2. Install Docker and docker-compose-plugin
3. Ensure current user is added to docker group
4. Do NOT install databases
5. Do NOT expose network services
6. Confirm installation success

Execute step by step and stop after completion.


Gemini should execute:

sudo apt update && sudo apt upgrade -y
sudo apt install docker.io docker-compose-plugin -y
sudo usermod -aG docker $USER


Log out and log back in.

4. Network Setup – Tailscale (MANDATORY)
Gemini PROMPT
Install and configure Tailscale on this machine.

Requirements:
- Use default installation method
- Authenticate interactively
- Do NOT expose exit nodes
- Do NOT enable subnet routing

After installation:
- Show tailscale status
- Confirm the node is online

Stop after completion.


Expected commands:

curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale status

5. Directory Structure (STRICT)
Gemini PROMPT
Create the following directory structure exactly as specified:

/opt/rae-node/
├── agent/
├── models/
├── workdir/
└── logs/

Set ownership to the current user.
Do not create any other directories.

6. Install Local LLM Runtime (Ollama)
Gemini PROMPT
Install Ollama as a local LLM runtime.

Requirements:
- Use official installer
- Enable system service
- Verify ollama is running
- Do NOT pull models yet


Commands:

curl -fsSL https://ollama.com/install.sh | sh
systemctl status ollama

7. Pull Approved Model ONLY
Gemini PROMPT
Pull exactly ONE local model:

Model: deepseek-coder:33b

Do NOT pull additional models.
Do NOT configure cloud inference.
Confirm model availability.


Command:

ollama pull deepseek-coder:33b

8. Node Agent – Execution Scope
IMPORTANT

Gemini MUST NOT:

design the agent

invent APIs

change protocols

Gemini will ONLY:

place provided files

run provided scripts

start/stop services

The node agent code will be delivered separately.

9. systemd Service Preparation (NO START YET)
Gemini PROMPT
Prepare a systemd service file for a future process:

Service name: rae-node
Executable: /usr/bin/python3 /opt/rae-node/agent/main.py
Restart policy: always
User: current user

Do NOT start the service yet.
Only create the service file and reload systemd.


Expected file:

/etc/systemd/system/rae-node.service

10. Security Rules (NON-NEGOTIABLE)

Gemini MUST ensure:

No database clients installed

No open ports exposed

No cron jobs added

No persistent secrets stored

No SSH keys modified

11. Verification Checklist (Manual)

The setup is correct if:

docker ps works without sudo

tailscale status shows node online

ollama list shows deepseek-coder

/opt/rae-node exists

No services listen on public interfaces

12. STOP POINT

After this document:

DO NOT start node agent

DO NOT connect to RAE yet

WAIT for instructions from RAE CONTROL NODE

This machine is now READY to become a RAE compute node.


---

## 🔑 Dlaczego to zadziała (ważne dla Ciebie)

- Gemini **nie myśli architektonicznie**
- Gemini **nie dotyka core**
- Gemini działa jak:
  > „bardzo dokładny administrator systemu”

Masz:
- powtarzalność
- brak dryfu
- zero „a ja zrobiłem inaczej”

---

## Co dalej (kiedy będziesz gotów)

Następny krok (już u Ciebie):
- dostarczenie `rae-node-agent` (repo / paczka)
- wspólny test: heartbeat → poll → idle

Jeśli chcesz, w kolejnym kroku mogę:
- przygotować **gotowy prompt „EXECUTOR MODE” dla Gemini**
- albo **szkielet repo node-agent**
- albo checklistę „czy dzieciak dobrze zrobił setup”  

To jest **dokładnie ten poziom kontroli, który chcesz mieć**.
