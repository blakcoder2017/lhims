# SMS Integration Guide

## Overview

This document describes the SMS integration features implemented in LHIMS using SMSOnlineGH API.

## Features Implemented

### 1. SMS Service (`app/services/sms_onlinegh_service.py`)
- Personalized messaging support using SMSOnlineGH API
- Phone number formatting for Ghana (233XXXXXXXXX)
- Support for both simple and personalized SMS

### 2. SMS Notifications

#### Patient Admission
- Sends SMS when a patient is admitted to IPD
- Includes: Patient name, Ward name, Bed number, Admission number

#### Bill Payment
- Sends SMS when payment is received
- Includes: Patient name, Payment amount, Receipt number, Invoice balance

#### Lab Test Results
- Sends SMS when lab test results are ready
- Includes: Patient name, Test name

#### Radiology Results
- Sends SMS when radiology results are ready
- Includes: Patient name, Study type

#### Appointment Created
- Sends SMS when an appointment is scheduled
- Includes: Patient name, Appointment date/time, Department, Appointment type

### 3. Appointment Reminders
- 48-hour reminder before appointment
- 24-hour reminder before appointment
- Automated scheduled task (runs every hour)

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
SMSONLINEGH_API_KEY=your_api_key_here
SMSONLINEGH_SENDER=LHIMS
```

### SMSOnlineGH Setup

1. Register at https://smsonlinegh.com
2. Get your API key from the dashboard
3. Request a sender name (must be approved)
4. Add the API key and sender name to `.env`

## Running Appointment Reminders

### Option 1: Background Process

Run the scheduler as a background process:

```bash
python -m app.services.scheduler
```

### Option 2: Cron Job

Add to crontab to run every hour:

```bash
0 * * * * cd /path/to/lhims && python -m app.services.scheduler
```

### Option 3: Systemd Service

Create a systemd service file `/etc/systemd/system/lhims-scheduler.service`:

```ini
[Unit]
Description=LHIMS Appointment Reminder Scheduler
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/lhims
ExecStart=/path/to/venv/bin/python -m app.services.scheduler
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable and start:

```bash
sudo systemctl enable lhims-scheduler
sudo systemctl start lhims-scheduler
```

## Message Templates

All SMS messages use personalized templates with variables:

- `{$name}` - Patient name
- `{$date}` - Appointment date/time
- `{$department}` - Department name
- `{$type}` - Appointment type
- `{$amount}` - Payment amount
- `{$receipt_number}` - Receipt number
- `{$balance}` - Invoice balance
- `{$test_name}` - Lab test name
- `{$study_type}` - Radiology study type
- `{$ward_name}` - Ward name
- `{$bed_number}` - Bed number
- `{$admission_number}` - Admission number

## Testing

To test SMS functionality:

1. Ensure `SMSONLINEGH_API_KEY` is set in `.env`
2. Create a test appointment with a valid phone number
3. Check SMSOnlineGH dashboard for sent messages

## API Response Handling

SMSOnlineGH returns **HTTP 200** even when the SMS is **not** accepted. The actual outcome is in the JSON body:

- **`handshake.label == "HSHK_OK"`** → SMS accepted for delivery (treated as success).
- **`handshake.label == "MV_ERR_SENDER"`** → Sender name not approved; register/approve your sender at SMSOnlineGH.
- **`handshake.label == "HSHK_ERR_UA_AUTH"`** → **Authentication failed.** The API key was rejected. Check:
  1. `SMSONLINEGH_API_KEY` in `.env` is the exact key from your SMSOnlineGH dashboard (no extra spaces, quotes, or newlines).
  2. In `.env` use one line: `SMSONLINEGH_API_KEY=your_key_here` (no spaces around `=`).
  3. Restart the app after changing `.env`.
- Other labels → Request rejected; check `handshake` in logs.

The service (`sms_onlinegh_service.py`) only reports **success** when `handshake.label == "HSHK_OK"`. Otherwise it returns failure and prints `[SMSOnlineGH] API handshake label: ...` in the terminal so you can see why the SMS was not sent.

## Troubleshooting

### SMS Not Sending
- **HSHK_ERR_UA_AUTH** = Authentication failed. Fix:
  1. Get your API key from https://smsonlinegh.com (dashboard).
  2. In `.env`: `SMSONLINEGH_API_KEY=your_key_here` (no spaces around `=`, no quotes around the key unless the key itself contains spaces).
  3. Restart uvicorn after changing `.env`.
- **MV_ERR_SENDER** = Sender name not approved; request approval at SMSOnlineGH for your sender name.
- Check phone number format (should be 0XXXXXXXXX or 233XXXXXXXXX, Ghana only).
- Review terminal for `[SMSOnlineGH]` and `[OPD Registration SMS]` lines.

### Appointment Reminders Not Working
- Ensure scheduler is running
- Check database connection
- Verify appointments have valid phone numbers
- Review scheduler logs

## Migration Notes

### Removing SELF_PAY Option

The `SELF_PAY` option has been removed from `PaymentMechanism` enum. To update existing data:

```sql
-- Update any existing SELF_PAY records to CASH
UPDATE patients SET payment_mechanism = 'CASH' WHERE payment_mechanism = 'SELF_PAY';

-- Note: PostgreSQL enum modifications require recreating the enum type
-- This should be done via Alembic migration
```

A migration script should be created to handle this change in production.
