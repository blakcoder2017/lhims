#!/usr/bin/env python3
"""
Daily Bed Charge Automation Script

This script generates daily bed and ward charges for all active IPD admissions.
Should be run as a scheduled task (cron job) daily at midnight.

Usage:
    python scripts/generate_daily_bed_charges.py [--date YYYY-MM-DD] [--system-user-id 1]
    
If --date is not provided, generates charges for today.
If --system-user-id is not provided, uses user ID 1 (system user).
"""

import sys
import os
from pathlib import Path
from datetime import date, datetime
from argparse import ArgumentParser

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.services.daily_bed_charge_service import generate_daily_bed_charges_for_all_admissions


def main():
    parser = ArgumentParser(description="Generate daily bed and ward charges for IPD admissions")
    parser.add_argument(
        "--date",
        type=str,
        help="Date for which to generate charges (YYYY-MM-DD). Defaults to today.",
        default=None
    )
    parser.add_argument(
        "--system-user-id",
        type=int,
        help="User ID to use for creating charges (system user). Defaults to 1.",
        default=1
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: don't commit changes to database"
    )
    
    args = parser.parse_args()
    
    # Parse date if provided
    charge_date = date.today()
    if args.date:
        try:
            charge_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD format.")
            sys.exit(1)
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        print(f"Generating daily bed charges for date: {charge_date}")
        print(f"Using system user ID: {args.system_user_id}")
        
        if args.dry_run:
            print("DRY RUN MODE: Changes will not be committed")
            db.begin()  # Start transaction for dry run
        
        # Generate charges
        charges = generate_daily_bed_charges_for_all_admissions(
            db, charge_date, args.system_user_id
        )
        
        if args.dry_run:
            db.rollback()
            print(f"DRY RUN: Would create {len(charges)} charges")
        else:
            db.commit()
            print(f"Successfully created {len(charges)} charges")
            
            # Print summary
            if charges:
                total_amount = sum(charge.total_amount for charge in charges)
                print(f"Total charges amount: GHS {total_amount:.2f}")
        
    except Exception as e:
        db.rollback()
        print(f"Error generating charges: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

