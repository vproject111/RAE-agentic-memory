#!/bin/bash
# scripts/load_testing/stress_test.sh
#
# Runs a stress test using Locust against the RAE API.
# This script starts Locust in headless mode for a specified duration and number of users.

# Default values
HOST=${LOCUST_HOST:-http://localhost:8000}
USERS=${LOCUST_USERS:-1000} # Number of concurrent users
HATCH_RATE=${LOCUST_HATCH_RATE:-100} # Users hatched per second
RUN_TIME=${LOCUST_RUN_TIME:-3m} # Duration of the test (e.g., 30s, 3m, 1h)
TEST_FILE="scripts/load_testing/basic_api_load.py"
LOG_FILE="stress_test.log"
REPORT_FILE="stress_test_report.html"

echo "Starting Locust Stress Test against: $HOST"
echo "Users: $USERS, Hatch Rate: $HATCH_RATE, Run Time: $RUN_TIME"

# Ensure the RAE API is running.
# In a real CI/CD environment, this would be part of the test setup.
# For local execution, ensure your `docker compose up` is running.

# Run Locust in headless mode
.venv/bin/locust -f "$TEST_FILE" \
         --host "$HOST" \
         --headless \
         -u "$USERS" \
         -r "$HATCH_RATE" \
         -t "$RUN_TIME" \
         --logfile "$LOG_FILE" \
         --html "$REPORT_FILE" \
         --csv "stress_test_stats"

# Check if Locust command succeeded
if [ $? -eq 0 ]; then
    echo "Locust Stress Test completed successfully."
    echo "Report available at: $REPORT_FILE"
    echo "Logs available at: $LOG_FILE"
    exit 0
else
    echo "Locust Stress Test failed."
    exit 1
fi
