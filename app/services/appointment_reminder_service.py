"""
Appointment Reminder Service
Sends SMS reminders to patients 48 hours and 24 hours before appointments
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from app.models.scheduled_appointment_models import Appointment, AppointmentStatus, AppointmentType
from app.models.patient_models import Patient
from app.services.sms_onlinegh_service import send_personalized_sms_notification, is_valid_phone


def send_appointment_reminders(db: Session) -> dict:
    """
    Send SMS reminders for upcoming appointments
    - 48 hours before appointment
    - 24 hours before appointment
    
    Returns:
        dict with counts of reminders sent
    """
    now = datetime.now()
    reminder_48h_window_start = now + timedelta(hours=47)
    reminder_48h_window_end = now + timedelta(hours=49)
    reminder_24h_window_start = now + timedelta(hours=23)
    reminder_24h_window_end = now + timedelta(hours=25)
    
    # Get appointments scheduled for 48 hours from now
    appointments_48h = db.query(Appointment).join(Patient).filter(
        and_(
            Appointment.status == AppointmentStatus.SCHEDULED,
            Appointment.is_active == True,
            Appointment.scheduled_date >= reminder_48h_window_start,
            Appointment.scheduled_date <= reminder_48h_window_end
        )
    ).all()
    
    # Get appointments scheduled for 24 hours from now
    appointments_24h = db.query(Appointment).join(Patient).filter(
        and_(
            Appointment.status == AppointmentStatus.SCHEDULED,
            Appointment.is_active == True,
            Appointment.scheduled_date >= reminder_24h_window_start,
            Appointment.scheduled_date <= reminder_24h_window_end
        )
    ).all()
    
    reminders_sent_48h = 0
    reminders_sent_24h = 0
    
    # Send 48-hour reminders (only if valid Ghana mobile number)
    for appointment in appointments_48h:
        if appointment.patient and appointment.patient.phone_number and is_valid_phone(appointment.patient.phone_number):
            try:
                scheduled_date_str = appointment.scheduled_date.strftime("%Y-%m-%d at %H:%M")
                message_template = "Hello {$name}. Reminder: You have an appointment scheduled for {$date} at {$department}. Please arrive on time. Thank you!"
                destinations = [{
                    "number": appointment.patient.phone_number,
                    "values": [
                        f"{appointment.patient.first_name} {appointment.patient.last_name}",
                        scheduled_date_str,
                        appointment.department
                    ]
                }]
                if send_personalized_sms_notification(message_template, destinations):
                    reminders_sent_48h += 1
            except Exception as e:
                print(f"Error sending 48h reminder for appointment {appointment.id}: {e}")
    
    # Send 24-hour reminders (only if valid Ghana mobile number)
    for appointment in appointments_24h:
        if appointment.patient and appointment.patient.phone_number and is_valid_phone(appointment.patient.phone_number):
            try:
                scheduled_date_str = appointment.scheduled_date.strftime("%Y-%m-%d at %H:%M")
                message_template = "Hello {$name}. Reminder: Your appointment is tomorrow ({$date}) at {$department}. Please arrive on time. Thank you!"
                destinations = [{
                    "number": appointment.patient.phone_number,
                    "values": [
                        f"{appointment.patient.first_name} {appointment.patient.last_name}",
                        scheduled_date_str,
                        appointment.department
                    ]
                }]
                if send_personalized_sms_notification(message_template, destinations):
                    reminders_sent_24h += 1
            except Exception as e:
                print(f"Error sending 24h reminder for appointment {appointment.id}: {e}")
    
    return {
        "reminders_48h_sent": reminders_sent_48h,
        "reminders_24h_sent": reminders_sent_24h,
        "total_sent": reminders_sent_48h + reminders_sent_24h
    }
