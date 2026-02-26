#!/usr/bin/env python3
"""Check the schema_json format in the database"""

import os
import sys
import json

def get_database_url():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('SQLALCHEMY_DATABASE_URL='):
                    return line.split('=', 1)[1].strip()
    return os.environ.get('SQLALCHEMY_DATABASE_URL', '')

def main():
    db_url = get_database_url()
    if not db_url:
        print("Error: Could not find database URL")
        sys.exit(1)
    
    import psycopg2
    conn = psycopg2.connect(db_url.replace('postgresql+psycopg2://', 'postgresql://'))
    cur = conn.cursor()
    
    # Get a sample template
    cur.execute("SELECT id, schema_json FROM lab_template_versions LIMIT 1")
    row = cur.fetchone()
    
    if row:
        schema = row[1]
        print("Template ID:", row[0])
        print("\nSchema type:", type(schema))
        print("\nSchema keys:", schema.keys() if isinstance(schema, dict) else "N/A")
        
        if isinstance(schema, dict):
            print("\nLayout:", schema.get("layout"))
            print("\nFields keys:", list(schema.get("fields", {}).keys())[:5] if isinstance(schema.get("fields"), dict) else "N/A")
            if isinstance(schema.get("fields"), dict):
                first_field_id = list(schema["fields"].keys())[0]
                print("\nFirst field:", schema["fields"].get(first_field_id))
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
