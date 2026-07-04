RAE_COMPUTE_NODE_GEMINI_VALIDATION.md

(Testy poprawności setupu compute node)

# RAE Compute Node – Gemini Validation & Self-Test Guide

This document defines a STRICT VALIDATION PROCEDURE.
Gemini MUST verify that the compute node was prepared correctly.

Gemini acts as:
- system auditor
- test executor
- reporter

Gemini MUST NOT:
- install new components
- fix issues silently
- change configuration

If a test fails → REPORT FAILURE and STOP.

---

## 0. Validation Mode (CRITICAL)

Gemini, before running any test, MUST acknowledge:

"I am running in VALIDATION MODE.
I will not install, modify, or fix anything.
I will only execute read-only checks and report results."

---

## 1. System Identity Test

### Gemini PROMPT



Verify system identity.

Check:

OS version

kernel version

hostname

uptime

Print results.


### Expected
- Linux
- system is stable (no reboot loops)

---

## 2. User & Permissions Test

### Gemini PROMPT



Verify current user permissions.

Tests:

Current user name

Is user in docker group?

Can user run docker without sudo?

Execute and print results.


Commands:
```bash
whoami
groups
docker ps

PASS criteria

docker ps works without sudo

3. Docker Runtime Test
Gemini PROMPT
Validate Docker installation.

Tests:
- docker version
- docker compose version
- docker daemon running

Print results.


Commands:

docker version
docker compose version
systemctl status docker

PASS criteria

No errors

Daemon active

4. Tailscale Network Test (CRITICAL)
Gemini PROMPT
Validate Tailscale connectivity.

Tests:
1. tailscale status
2. tailscale ip -4
3. Verify node is ONLINE
4. Confirm NO exit node enabled

Print full output.


Commands:

tailscale status
tailscale ip -4
tailscale status --json | grep exitNode

PASS criteria

Node is online

Has 100.x.x.x IP

exit node = false / not enabled

5. Network Exposure Test (SECURITY)
Gemini PROMPT
Verify that no unintended services are listening.

List all listening TCP ports.


Command:

ss -tulpen

PASS criteria

No unexpected public listeners

Only system services (ssh allowed)

6. Directory Structure Test
Gemini PROMPT
Verify RAE node directory structure.

Check:
- /opt/rae-node exists
- required subdirectories exist
- ownership matches current user

Print tree and permissions.


Commands:

ls -ld /opt/rae-node
tree -L 2 /opt/rae-node
stat /opt/rae-node

PASS criteria

Exact structure

No extra directories

7. Ollama Runtime Test
Gemini PROMPT
Validate Ollama installation.

Tests:
1. ollama version
2. ollama service status
3. list installed models

Print results.


Commands:

ollama --version
systemctl status ollama
ollama list

PASS criteria

Ollama running

deepseek-coder model present

8. GPU Availability Test
Gemini PROMPT
Verify GPU availability.

Tests:
- nvidia-smi
- GPU model
- VRAM amount

Print output.


Command:

nvidia-smi

PASS criteria

NVIDIA GPU visible

Correct model

No driver errors

9. systemd Service Sanity Test (NO START)
Gemini PROMPT
Validate systemd service file existence.

Tests:
- rae-node.service exists
- file content is readable
- service is NOT running

Print results.


Commands:

ls /etc/systemd/system/rae-node.service
systemctl status rae-node

PASS criteria

Service exists

Service inactive / dead

10. Forbidden Components Test
Gemini PROMPT
Check for forbidden components.

Ensure NONE of the following are installed:
- PostgreSQL client/server
- MySQL / MariaDB
- Redis
- MongoDB

Print package list matches.


Commands:

dpkg -l | egrep 'postgres|mysql|redis|mongo'

PASS criteria

No forbidden packages installed

11. Cleanup Verification
Gemini PROMPT
Verify that no temporary files remain.

Check:
- /tmp
- /var/tmp
- /opt/rae-node/workdir

Print summary.


Commands:

ls -la /opt/rae-node/workdir

PASS criteria

workdir empty

12. Final Report (MANDATORY)
Gemini MUST produce a FINAL REPORT in this format:
RAE COMPUTE NODE VALIDATION REPORT
---------------------------------
Node ID: <hostname>
Date: <ISO timestamp>

[PASS] System identity
[PASS] User permissions
[PASS] Docker runtime
[PASS] Tailscale connectivity
[PASS] Network exposure
[PASS] Directory structure
[PASS] Ollama runtime
[PASS] GPU availability
[PASS] systemd service
[PASS] Forbidden components
[PASS] Cleanup

OVERALL STATUS: PASS


If ANY test fails:

Mark test as [FAIL]

Explain why

STOP execution

DO NOT FIX

13. STOP CONDITION

After validation:

DO NOT start rae-node agent

DO NOT modify system

Send validation report to RAE control node owner

END OF DOCUMENT


---

## Dlaczego to jest bardzo dobre (krótko, ale ważne)

- **Gemini sam sprawdza swoje własne działania**  
- brak „a poprawiłem przy okazji”
- masz:
  - audyt
  - powtarzalność
  - dowód poprawności

To jest **dokładnie ten poziom rygoru**, który:
- uspokaja Ciebie
- uspokaja IT
- skaluje się na więcej node’ów

---

## Co dalej (już opcjonalnie)

Kolejne logiczne kroki (na później):
- automatyczny upload raportu do RAE
- podpis raportu (hash)
- whitelist node’ów na podstawie PASS

Ale **to, co masz teraz, w zupełności wystarczy**.

Jeśli chcesz, następnym razem mogę:
- scalić **EXECUTION + VALIDATION** w jeden workflow
- albo przygotować **template raportu do RAE**

Ten etap masz domknięty ✔️