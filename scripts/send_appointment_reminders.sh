#!/bin/bash
# Send appointment reminders for tomorrow's appointments.
# Add to crontab (e.g. run daily at 6 PM):
#   0 18 * * * /path/to/lhims/scripts/send_appointment_reminders.sh
#
# Requires: LHIMS_BASE_URL (default http://localhost:8000)
# For authenticated calls, use a session cookie or API token.

BASE_URL="${LHIMS_BASE_URL:-http://localhost:8000}"
DAYS_AHEAD="${1:-1}"

# POST to send-reminders (requires Admin/Front Office auth)
# If using API key auth, add: -H "Authorization: Bearer YOUR_TOKEN"
curl -s -X POST "${BASE_URL}/api/v1/appointments/scheduled/send-reminders?days_ahead=${DAYS_AHEAD}" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool 2>/dev/null || true
