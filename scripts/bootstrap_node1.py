import subprocess
import sys
import time

HOST = "100.117.242.21"
USER = "root"
PASS = "mwzmjsunp"
CMD_START = "/root/Skrypty/lumina_grzegorz"
CMD_STOP = "/root/Skrypty/lumina_stop"



def run_ssh_cmd(cmd, timeout=None):
    ssh_cmd = [
        "sshpass",
        "-p",
        PASS,
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        f"{USER}@{HOST}",
        cmd,
    ]
    return subprocess.Popen(
        ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
    )


def monitor_process(proc):
    ok_count = 0
    start_time = time.time()

    print(f"--- Monitoring '{CMD_START}' output ---")
    while True:
        # Check if process ended
        if proc.poll() is not None:
            break

        # Read line
        line = proc.stdout.readline()
        if line:
            print(f"[NODE1]: {line.strip()}")
            if "ok" in line.lower():
                ok_count += 1

            # Check for generic errors (adjust keywords if needed)
            if "error" in line.lower() or "failed" in line.lower():
                return False, ok_count

        # Timeout safety for the "minute countdown"
        if time.time() - start_time > 120 and ok_count < 4:
            print("timeout waiting for success sequence")
            return False, ok_count

        if ok_count >= 4:
            return True, ok_count

    return False, ok_count


def main():
    print(f"🚀 Attempting to bootstrap Node1 ({HOST})...")

    max_retries = 3
    for attempt in range(max_retries):
        print(f"\nAttempt {attempt+1}/{max_retries}")

        proc = run_ssh_cmd(CMD_START)
        success, oks = monitor_process(proc)

        if success:
            print(f"✅ Success! Received {oks} 'ok' signals.")
            return
        else:
            print("⚠️ Failure or error detected. Initiating recovery...")
            proc.terminate()

            # Recovery sequence
            print(f"Running '{CMD_STOP}'...")
            stop_proc = run_ssh_cmd(CMD_STOP)
            stdout, stderr = stop_proc.communicate()
            print(f"Stop output: {stdout}")

            print("Waiting 10 seconds...")
            time.sleep(10)

    print("❌ Failed to bootstrap Node1 after retries.")
    sys.exit(1)


if __name__ == "__main__":
    main()
