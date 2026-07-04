import random
import time
from datetime import datetime

import httpx

# CONFIGURATION
API_URL = "http://127.0.0.1:9000/api/collector/ingest/"
MACHINE_CODE = "TM01"
# Hardcoded token from container DB to avoid SQLite mismatch on host
TOKEN = "3a1fcceca964deaeae60c32f9024a685bdc7f9c1"


def simulate():
    print(f"Starting machine simulator for {MACHINE_CODE}...")
    print(f"Target URL: {API_URL}")
    print(f"Using Token: {TOKEN[:5]}...{TOKEN[-5:]}")

    count = 0
    while True:  # Run indefinitely until Ctrl+C
        count += 1
        try:
            # Simulate some metrics - tuned for DEMO visuals
            temp = round(random.uniform(50.0, 95.0), 2)

            # Status distribution for nice Gantt chart
            status_pool = ["RUNNING"] * 70 + ["IDLE"] * 20 + ["ERROR"] * 10
            current_status = random.choice(status_pool)

            payload = {
                "machine_code": MACHINE_CODE,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metrics": {
                    "temp": temp,
                    "pressure": round(random.uniform(1.0, 5.0), 2),
                    "status": current_status,
                    "parts_delta": (
                        random.randint(0, 5) if current_status == "RUNNING" else 0
                    ),
                    "good_parts_delta": 0,
                },
            }

            if payload["metrics"]["parts_delta"] > 0:
                is_bad = random.random() < 0.1
                total = payload["metrics"]["parts_delta"]
                good = total - 1 if is_bad else total
                payload["metrics"]["good_parts_delta"] = max(0, good)
            else:
                payload["metrics"]["good_parts_delta"] = 0

            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] {current_status} | Temp: {temp}C | Prod: {payload['metrics']['parts_delta']}"
            )

            response = httpx.post(
                API_URL,
                json=payload,
                headers={"Authorization": f"Token {TOKEN}"},
                timeout=5.0,
            )

            if response.status_code != 201:
                print(f"Error: {response.status_code} - {response.text}")
            else:
                print("Success: 201 Created")

        except KeyboardInterrupt:
            print("\nStopping simulator...")
            break
        except Exception as e:
            print(f"Simulator error: {e}")

        time.sleep(2)


if __name__ == "__main__":
    simulate()
