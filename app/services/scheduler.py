"""
Scheduler Service
Runs scheduled tasks like appointment reminders
"""
import schedule
import time
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.appointment_reminder_service import send_appointment_reminders


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


def start_scheduler():
    """Start the scheduler"""
    # Schedule appointment reminders to run every hour
    schedule.every().hour.do(run_appointment_reminders)
    
    # Also run immediately on startup
    run_appointment_reminders()
    
    print("Scheduler started. Appointment reminders will run every hour.")
    
    # Run scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    start_scheduler()
