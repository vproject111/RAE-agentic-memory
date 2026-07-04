#!/bin/bash
# scripts/load_testing/soak_test.sh
#
# Runs a soak test using Locust against the RAE API.
# This script starts Locust in headless mode for a long duration to check for stability and memory leaks.

# Default values
HOST=${LOCUST_HOST:-http://localhost:8000}
USERS=${LOCUST_USERS:-100} # Number of concurrent users (fewer than stress test)
HATCH_RATE=${LOCUST_HATCH_RATE:-10} # Users hatched per second
RUN_TIME=${LOCUST_RUN_TIME:-1h} # Duration of the test (e.g., 1h, 4h, 1d)
TEST_FILE="scripts/load_testing/basic_api_load.py"
LOG_FILE="soak_test.log"
REPORT_FILE="soak_test_report.html"

echo "Starting Locust Soak Test against: $HOST"
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
         --csv "soak_test_stats"

# Check if Locust command succeeded
if [ $? -eq 0 ]; then
    echo "Locust Soak Test completed successfully."
    echo "Report available at: $REPORT_FILE"
    echo "Logs available at: $LOG_FILE"
    exit 0
else
    echo "Locust Soak Test failed."
    exit 1
fi
