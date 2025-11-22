"""
Seed Script: Clear Orphaned Beds

This script clears beds that are marked as OCCUPIED in the database
but don't have any active admissions associated with them.

It will:
1. Find all beds with status OCCUPIED
2. Check if there's an active admission (status = ADMITTED) for each bed
3. If no active admission exists, set bed status to AVAILABLE
4. Update ward occupancy counts accordingly
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import SessionLocal
from app.models.ipd_models import Bed, Ward, BedStatus, AdmissionStatus


def get_table_counts(db: Session):
    """Display current counts"""
    from sqlalchemy import text
    
    total_beds = db.query(Bed).filter(Bed.is_active == True).count()
    occupied_beds = db.query(Bed).filter(
        Bed.is_active == True,
        Bed.status == BedStatus.OCCUPIED
    ).count()
    
    # Use raw SQL to avoid column issues
    result = db.execute(text("SELECT COUNT(*) FROM admissions WHERE is_active = true AND status = 'admitted'"))
    active_admissions = result.scalar() or 0
    
    print(f"\n📊 Current Database State:")
    print(f"   Total Beds (active): {total_beds}")
    print(f"   Occupied Beds: {occupied_beds}")
    print(f"   Active Admissions: {active_admissions}")
    print()


def clear_orphaned_beds(db: Session, dry_run: bool = True):
    """
    Clear beds that are marked as OCCUPIED but have no active admissions.
    
    Args:
        db: Database session
        dry_run: If True, only show what would be changed without making changes
    """
    # Find all occupied beds
    occupied_beds = db.query(Bed).filter(
        Bed.is_active == True,
        Bed.status == BedStatus.OCCUPIED
    ).all()
    
    print(f"🔍 Found {len(occupied_beds)} occupied beds to check...\n")
    
    orphaned_beds = []
    valid_beds = []
    
    from sqlalchemy import text
    
    for bed in occupied_beds:
        # Check if there's an active admission for this bed using raw SQL to avoid column issues
        result = db.execute(
            text(
                "SELECT id, admission_number FROM admissions "
                "WHERE bed_id = :bed_id AND is_active = true AND status = 'admitted' LIMIT 1"
            ),
            {"bed_id": bed.id}
        ).first()
        active_admission = result if result else None
        
        if not active_admission:
            orphaned_beds.append(bed)
            print(f"   ⚠️  Bed {bed.bed_number} (ID: {bed.id}) in Ward {bed.ward.name if bed.ward else 'N/A'} is OCCUPIED but has no active admission")
        else:
            valid_beds.append(bed)
            admission_number = active_admission[1] if isinstance(active_admission, tuple) and len(active_admission) > 1 else 'N/A'
            print(f"   ✅ Bed {bed.bed_number} (ID: {bed.id}) is correctly OCCUPIED (has active admission: {admission_number})")
    
    print(f"\n📋 Summary:")
    print(f"   Valid occupied beds: {len(valid_beds)}")
    print(f"   Orphaned beds (will be cleared): {len(orphaned_beds)}")
    
    if not orphaned_beds:
        print("\n✅ No orphaned beds found! All beds are correctly marked.")
        return
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
        print("\n   Beds that would be cleared:")
        for bed in orphaned_beds:
            print(f"      - Bed {bed.bed_number} (ID: {bed.id}) in Ward: {bed.ward.name if bed.ward else 'N/A'}")
        print("\n   Run with --confirm to apply changes")
        return
    
    # Actually clear the orphaned beds
    print("\n🔄 Clearing orphaned beds...")
    
    # Group beds by ward to update occupancy counts
    ward_bed_counts = {}
    for bed in orphaned_beds:
        ward_id = bed.ward_id
        if ward_id not in ward_bed_counts:
            ward_bed_counts[ward_id] = 0
        ward_bed_counts[ward_id] += 1
    
    # Update bed statuses
    cleared_count = 0
    for bed in orphaned_beds:
        bed.status = BedStatus.AVAILABLE
        cleared_count += 1
        print(f"   ✅ Cleared bed {bed.bed_number} (ID: {bed.id})")
    
    # Update ward occupancy counts
    for ward_id, count in ward_bed_counts.items():
        ward = db.query(Ward).filter(Ward.id == ward_id).first()
        if ward:
            # Decrement occupancy (but don't go below 0)
            new_occupancy = max(0, ward.current_occupancy - count)
            if new_occupancy != ward.current_occupancy:
                print(f"   📉 Updated ward {ward.name} occupancy: {ward.current_occupancy} → {new_occupancy}")
                ward.current_occupancy = new_occupancy
    
    db.commit()
    
    print(f"\n✅ Successfully cleared {cleared_count} orphaned bed(s)")
    print(f"✅ Updated {len(ward_bed_counts)} ward(s) occupancy counts")


def verify_cleanup(db: Session):
    """Verify the cleanup was successful"""
    print("\n🔍 Verifying cleanup...")
    
    occupied_beds = db.query(Bed).filter(
        Bed.is_active == True,
        Bed.status == BedStatus.OCCUPIED
    ).all()
    
    from sqlalchemy import text
    
    orphaned_count = 0
    for bed in occupied_beds:
        result = db.execute(
            text(
                "SELECT id FROM admissions "
                "WHERE bed_id = :bed_id AND is_active = true AND status = 'admitted' LIMIT 1"
            ),
            {"bed_id": bed.id}
        ).first()
        active_admission = result if result else None
        
        if not active_admission:
            orphaned_count += 1
            print(f"   ⚠️  Still orphaned: Bed {bed.bed_number} (ID: {bed.id})")
    
    if orphaned_count == 0:
        print("   ✅ All beds are correctly marked!")
    else:
        print(f"   ⚠️  {orphaned_count} bed(s) still orphaned")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clear orphaned beds (occupied but no active admission)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    parser.add_argument('--confirm', action='store_true', help='Confirm and apply changes')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt (use with --confirm)')
    parser.add_argument('--verify', action='store_true', help='Verify cleanup after applying changes')
    
    args = parser.parse_args()
    
    # Default to dry-run if neither --dry-run nor --confirm is specified
    dry_run = not args.confirm
    
    if not dry_run:
        print("⚠️  WARNING: This will modify the database!")
        if not args.yes:
            response = input("   Are you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("   Cancelled.")
                return
        else:
            print("   Proceeding with --yes flag...")
    
    db = SessionLocal()
    try:
        print("=" * 60)
        print("🧹 Clear Orphaned Beds Script")
        print("=" * 60)
        
        get_table_counts(db)
        
        clear_orphaned_beds(db, dry_run=dry_run)
        
        if args.verify and not dry_run:
            verify_cleanup(db)
        
        get_table_counts(db)
        
        print("\n" + "=" * 60)
        print("✅ Script completed")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

