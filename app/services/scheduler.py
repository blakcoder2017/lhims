"""
Scheduler Service
Runs scheduled tasks like appointment reminders and encounter auto-close
"""
import schedule
import time
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.appointment_reminder_service import send_appointment_reminders
from app.services.encounter_auto_close_service import run_encounter_auto_close


def run_appointment_reminders():
    """Run appointment reminder task"""
    db = SessionLocal()
    try:
        result = send_appointment_reminders(db)
        print(f"Appointment reminders sent: {result}")
    except Exception as e:
        print(f"Error sending appointment reminders: {e}")
    finally:
        db.close()


def run_encounter_auto_close_task():
    """Run encounter auto-close task"""
    try:
        result = run_encounter_auto_close()
        print(f"Encounter auto-close: {result['message']}")
    except Exception as e:
        print(f"Error in encounter auto-close: {e}")


def start_scheduler():
    """Start the scheduler"""
    # Schedule appointment reminders to run every hour
    schedule.every().hour.do(run_appointment_reminders)
    
    # Schedule encounter auto-close to run every hour
    schedule.every().hour.do(run_encounter_auto_close_task)
    
    # Also run immediately on startup
    run_appointment_reminders()
    run_encounter_auto_close_task()
    
    print("Scheduler started. Tasks scheduled:")
    print("  - Appointment reminders (hourly)")
    print("  - Encounter auto-close (hourly)")
    
    # Run scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    start_scheduler()
