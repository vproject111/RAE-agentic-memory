RAE_COMPUTE_NODE_GEMINI_AUTOMATION.md

(Automatyczna praca node’a – bez udziału użytkownika)

# RAE Compute Node – Gemini Automation Setup

This document instructs Gemini CLI to configure FULL AUTOMATION
on a RAE COMPUTE NODE.

After this setup:
- the node operates autonomously
- no human interaction is required
- the machine may be unattended for many hours
- tasks are executed only when safe

Gemini acts as:
- automation engineer
- system configurator

Gemini MUST NOT:
- change architecture
- modify RAE APIs
- expose services publicly
- bypass safety rules

---

## 0. Automation Mode Declaration (MANDATORY)

Gemini MUST confirm:

"I am configuring AUTOMATION MODE.
I will only create configuration files, scripts, and system services.
I will not install new software unless explicitly instructed."

---

## 1. Automation Design Principles (READ, DO NOT MODIFY)

The compute node must obey:

1. Pull-only task execution
2. Safe to power off anytime
3. No work if user is active
4. No long-running GPU saturation
5. Automatic recovery after reboot
6. No persistence of task data

---

## 2. Create Node Runtime Configuration

### Gemini PROMPT



Create or update the node configuration file:

Path: /opt/rae-node/agent/runtime.yaml

Include exactly the following fields.


```yaml
automation:
  enabled: true
  auto_start: true

safety:
  detect_active_user: true
  idle_required_minutes: 10
  max_cpu_percent: 80
  max_gpu_percent: 90
  max_vram_gb: 14
  cooldown_minutes: 15

execution:
  poll_interval_sec: 45
  heartbeat_interval_sec: 30
  task_timeout_minutes: 180
  retry_on_disconnect: true

3. User Activity Detection Script
Purpose

Prevent node from working while a human is using the computer.

Gemini PROMPT
Create a script that detects whether a user is actively using the system.

Rules:
- If graphical session is active OR
- if keyboard/mouse activity is detected OR
- if non-RAE GPU processes exist

Then node MUST NOT execute tasks.

Create script:
Path: /opt/rae-node/agent/check_user_idle.py

Required checks (implement all):

Active X11 / Wayland session

loginctl session state

nvidia-smi shows non-RAE processes

Script output:

exit code 0 → SAFE TO RUN

exit code 1 → DO NOT RUN

4. GPU Load Guard Script
Gemini PROMPT
Create a GPU guard script that blocks task execution
if GPU or VRAM usage exceeds configured thresholds.

Path: /opt/rae-node/agent/check_gpu_load.py


Script must:

read current GPU utilization

read VRAM usage

compare with runtime.yaml limits

return safe / unsafe status

5. Node Agent Wrapper (Automation Entry Point)
Gemini PROMPT
Create a wrapper script that controls task execution.

Path: /opt/rae-node/agent/auto_runner.py

Behavior:
1. Check automation enabled
2. Check user idle
3. Check GPU load
4. If SAFE:
   - allow node agent to poll tasks
5. If NOT SAFE:
   - skip polling
   - sleep until next interval


This wrapper MUST be the entry point for the systemd service.

6. Update systemd Service (Automation Mode)
Gemini PROMPT
Update the existing systemd service:

Service name: rae-node

Change ExecStart to:
  /usr/bin/python3 /opt/rae-node/agent/auto_runner.py

Ensure:
- Restart=always
- RestartSec=15
- Service runs as current user

Reload systemd.
DO NOT start the service yet.

7. Night / Long Absence Optimization (OPTIONAL BUT RECOMMENDED)
Gemini PROMPT
Configure system settings so that:

- system does NOT suspend while tasks are running
- system may suspend when idle and no task is running
- no permanent power changes are made

Use temporary inhibitors only.


(Hint: systemd-inhibit)

8. Logging & Observability
Gemini PROMPT
Configure logging so that:

- all automation decisions are logged
- logs are written to /opt/rae-node/logs/
- log rotation is enabled (7 days)

Do not send logs externally.

9. Dry-Run Test (MANDATORY)
Gemini PROMPT
Perform a DRY-RUN automation test.

Simulate:
1. User active
2. User idle
3. GPU busy
4. GPU free

Print which cases allow task execution
and which block it.

DO NOT execute real tasks.

10. Final Automation Report
Gemini MUST output:
RAE COMPUTE NODE – AUTOMATION STATUS
----------------------------------
Automation enabled: YES
Auto-start on boot: YES
User activity protection: ACTIVE
GPU protection: ACTIVE
Safe for unattended operation: YES

READY FOR CENTRAL CONTROL


If ANY requirement is not met:

report failure

do NOT proceed

11. STOP CONDITION

After this document:

Do NOT start rae-node service

Wait for command from RAE Control Node

No further changes allowed

END OF DOCUMENT


---

## 🧠 Co to Ci daje (krótko, ale kluczowo)

Po tym **trzecim pliku**:

- Kubuś i Julka:
  - **nie są potrzebni**
  - nie klikają
  - nie pilnują
- Ty:
  - wrzucasz zadania
  - kontrolujesz wszystko z RAE
  - wykorzystujesz ich nieobecność w 100%
- System:
  - bezpieczny
  - nie przeszkadza użytkownikowi
  - odporny na znikanie node’ów

To jest **pełna automatyzacja klasy R&D**, tylko zrobiona mądrze i po domowemu.

---

## 🔚 Co masz teraz kompletne

✅ setup  
✅ walidację  
✅ automatyzację  

**To jest pełny pakiet node’a.**

Jeśli chcesz, następnym krokiem możemy:
- spiąć to **od strony RAE (scheduler + requeue)**  
- albo przygotować **jedno polecenie „enable-node” po Twojej stronie**  
- albo zrobić **wersję v0.1 do P&D R&D**

Ale na ten moment — **masz wszystko, żeby ruszyć bez angażowania ludzi** 💪
