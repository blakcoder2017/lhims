#!/usr/bin/env python3
"""
Update Lab Orders to Latest Template Versions
=============================================
This script updates all lab orders to use the latest PUBLISHED 
template version instead of older versions.

Usage:
    python3 update_lab_orders_to_latest_version.py

Note: This only updates the template reference - the actual results
are stored in result_json and won't be changed. The new version will
be used for future result entries.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:password123@localhost:5433/lhims')

engine = create_engine(DATABASE_URL)


def get_latest_template_versions():
    """Get the latest PUBLISHED version for each template."""
    print("\n=== GETTING LATEST TEMPLATE VERSIONS ===\n")
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT lt.id, lt.name, MAX(ltv.version) as latest_version
            FROM lab_templates lt
            JOIN lab_template_versions ltv ON lt.id = ltv.template_id
            WHERE ltv.status = 'PUBLISHED'
            GROUP BY lt.id, lt.name
            ORDER BY lt.name
        """))
        
        versions = {}
        for row in result:
            template_name = row[1]
            latest_version = row[2]
            # Extract test code from template name (e.g., "Lab Test - GONORRHOEA" -> "GONORRHOEA")
            test_code = template_name.replace('Lab Test - ', '').strip()
            versions[test_code] = {
                'template_id': row[0],
                'latest_version': latest_version
            }
            print(f"  {test_code:30} -> v{latest_version}")
        
        return versions


def update_lab_orders_to_latest():
    """Update all lab orders to use the latest template versions."""
    print("\n=== UPDATING LAB ORDERS TO LATEST VERSIONS ===\n")
    
    # Get mapping of test codes to latest template info
    latest_versions = get_latest_template_versions()
    
    with engine.connect() as conn:
        # Get all lab orders that have a template version set
        result = conn.execute(text("""
            SELECT DISTINCT test_code, template_version_used 
            FROM lab_orders 
            WHERE template_version_used IS NOT NULL
            ORDER BY test_code
        """))
        
        orders_to_update = []
        for row in result:
            test_code = str(row[0]) if row[0] else ''
            current_version = row[1]
            
            if test_code in latest_versions:
                latest = latest_versions[test_code]['latest_version']
                template_id = latest_versions[test_code]['template_id']
                
                if current_version < latest:
                    orders_to_update.append({
                        'test_code': test_code,
                        'current_version': current_version,
                        'latest_version': latest,
                        'template_id': template_id
                    })
        
        print(f"Found {len(orders_to_update)} orders to update\n")
        
        # Update each order
        updated_count = 0
        for order in orders_to_update:
            conn.execute(text("""
                UPDATE lab_orders 
                SET template_version_used = :latest_version,
                    template_id = :template_id
                WHERE test_code = :test_code 
                AND template_version_used < :latest_version
            """), {
                'latest_version': order['latest_version'],
                'template_id': order['template_id'],
                'test_code': order['test_code']
            })
            
            print(f"  ✓ {order['test_code']:30} v{order['current_version']} -> v{order['latest_version']}")
            updated_count += 1
        
        conn.commit()
        print(f"\nTotal orders updated: {updated_count}")


def verify_updates():
    """Verify the updates were applied correctly."""
    print("\n=== VERIFICATION ===\n")
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT test_code, template_version_used, COUNT(*) as cnt
            FROM lab_orders 
            WHERE template_version_used IS NOT NULL
            GROUP BY test_code, template_version_used
            ORDER BY test_code, template_version_used
        """))
        
        print("Template versions after update:")
        for row in result:
            test_code = str(row[0]) if row[0] else 'Unknown'
            version = str(row[1]) if row[1] else 'N/A'
            count = row[2]
            print(f"  {test_code:30} | v{version} | {count} orders")


def main():
    print("="*60)
    print("UPDATE LAB ORDERS TO LATEST TEMPLATE VERSIONS")
    print("="*60)
    
    # Show current state
    print("\n--- Current State ---")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT test_code, template_version_used, COUNT(*) as cnt
            FROM lab_orders 
            WHERE template_version_used IS NOT NULL
            GROUP BY test_code, template_version_used
            ORDER BY test_code
        """))
        print("\nBefore update:")
        for row in result:
            test_code = str(row[0]) if row[0] else 'Unknown'
            version = str(row[1]) if row[1] else 'N/A'
            print(f"  {test_code:30} v{version}")
    
    # Update
    update_lab_orders_to_latest()
    
    # Verify
    verify_updates()
    
    print("\n" + "="*60)
    print("UPDATE COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    main()
