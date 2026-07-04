RAE_COMPUTE_NODE_GEMINI_AUTOMATION_TESTS.md

(Testy automatycznej pracy compute node – unattended mode)

# RAE Compute Node – Automation Tests & Verification

This document defines MANDATORY TESTS for AUTOMATION MODE
configured on a RAE COMPUTE NODE.

Gemini acts strictly as:
- test executor
- system observer
- report generator

Gemini MUST NOT:
- install software
- modify files
- fix configuration
- restart services unless explicitly instructed

If any test FAILS → report and STOP.

---

## 0. Test Mode Declaration (MANDATORY)

Before running tests Gemini MUST state:

"I am running in AUTOMATION TEST MODE.
I will not change system state unless explicitly instructed.
I will only simulate or observe behavior."

---

## 1. Preconditions Check

### Gemini PROMPT



Verify that the following files exist:

/opt/rae-node/agent/runtime.yaml

/opt/rae-node/agent/auto_runner.py

/opt/rae-node/agent/check_user_idle.py

/opt/rae-node/agent/check_gpu_load.py

/etc/systemd/system/rae-node.service

Print existence and permissions.


### PASS criteria
- All files exist
- Files are readable
- No unexpected files present

---

## 2. Automation Disabled Test (Safety Baseline)

### Gemini PROMPT



Temporarily inspect runtime.yaml and verify:

automation.enabled == true

Do NOT modify the file.
Only read and print relevant section.


### PASS criteria
- automation.enabled is true
- auto_start is true

---

## 3. User Activity Detection Tests (CRITICAL)

### 3.1 Active User Simulation

### Gemini PROMPT



Simulate ACTIVE USER scenario.

Checks:

graphical session active (loginctl)

user logged in

run check_user_idle.py

Print:

detected state

exit code


### PASS criteria
- Script returns exit code 1 (DO NOT RUN)

---

### 3.2 Idle User Simulation

### Gemini PROMPT



Simulate IDLE USER scenario.

Requirements:

no active graphical session

no keyboard/mouse activity

run check_user_idle.py

Print:

detected state

exit code


### PASS criteria
- Script returns exit code 0 (SAFE TO RUN)

---

## 4. GPU Load Guard Tests (CRITICAL)

### 4.1 GPU Busy Scenario

### Gemini PROMPT



Simulate GPU BUSY scenario.

Method:

detect current GPU load

compare with runtime.yaml thresholds

run check_gpu_load.py

Print:

GPU utilization

VRAM usage

script exit code


### PASS criteria
- exit code indicates NOT SAFE when thresholds exceeded

---

### 4.2 GPU Free Scenario

### Gemini PROMPT



Simulate GPU FREE scenario.

Conditions:

GPU usage below thresholds

run check_gpu_load.py

Print:

GPU utilization

VRAM usage

script exit code


### PASS criteria
- exit code indicates SAFE TO RUN

---

## 5. Auto Runner Decision Logic Test

### Gemini PROMPT



Run auto_runner.py in DRY-RUN mode.

Simulate combinations:

User active + GPU free

User idle + GPU busy

User idle + GPU free

For each case:

print decision (RUN / SKIP)

do NOT poll real tasks


### PASS criteria
- Only case (3) allows RUN
- All others SKIP

---

## 6. systemd Integration Test (NO EXECUTION)

### Gemini PROMPT



Inspect rae-node systemd service.

Verify:

ExecStart points to auto_runner.py

Restart policy is always

Service is ENABLED

Service is NOT currently running

Print findings.


### PASS criteria
- All conditions met
- Service inactive

---

## 7. Reboot Safety Test (SIMULATION)

### Gemini PROMPT



Simulate reboot scenario (NO REAL REBOOT).

Verify logically:

systemd service is enabled

auto_runner would start on boot

automation rules would be enforced

Explain reasoning based on config.


### PASS criteria
- Correct startup order
- No manual steps required after reboot

---

## 8. Unattended Operation Test (LONG ABSENCE)

### Gemini PROMPT



Evaluate unattended operation safety.

Check:

task timeouts

cooldown settings

retry behavior

Confirm that:

node can run for 8–10 hours unattended

node can be powered off anytime

no task causes system lock

Print assessment.


### PASS criteria
- All safety conditions satisfied

---

## 9. Negative Test – Forbidden Behavior

### Gemini PROMPT



Verify that automation CANNOT:

start tasks when user is active

start tasks when GPU overloaded

persist task data after completion

bypass safety scripts

Explain why each is blocked.


### PASS criteria
- All forbidden behaviors correctly blocked

---

## 10. Final Automation Test Report (MANDATORY)

Gemini MUST output EXACTLY:


RAE COMPUTE NODE – AUTOMATION TEST REPORT

Node: <hostname>
Date: <ISO timestamp>

[PASS] Preconditions
[PASS] Automation config
[PASS] User activity detection
[PASS] GPU guard
[PASS] Auto-runner logic
[PASS] systemd integration
[PASS] Reboot safety
[PASS] Unattended operation
[PASS] Negative safety tests

OVERALL STATUS: READY FOR UNATTENDED USE


If ANY test fails:
- Mark as [FAIL]
- Explain precisely
- OVERALL STATUS: NOT READY
- STOP

---

## 11. STOP CONDITION

After tests:
- Do NOT start rae-node service
- Send report to RAE Control Node owner
- Await explicit enable command

END OF DOCUMENT

🔒 Co masz teraz domknięte (ważne)

Po tej wiadomości masz pełny, zamknięty zestaw po stronie dzieciaków:

Execution (instalacja)

Validation (czy instalacja OK)

Automation (samodzielna praca)

Automation Tests (czy automaty są bezpieczne)

To jest ten poziom rygoru, który:

pozwala spać spokojnie,

pozwala im iść do pracy,

pozwala Tobie w pełni sterować systemem.

Odpowiedź na pytanie wprost

Tak — te testy są potrzebne.
Teraz już są kompletne.

Jeśli chcesz, następnym logicznym krokiem będzie:

jedno polecenie po Twojej stronie: enable-node kubus-gpu-01

albo spięcie raportów testów bezpośrednio do RAE memory

Ale po stronie node’ów temat jest zamknięty i bezpieczny