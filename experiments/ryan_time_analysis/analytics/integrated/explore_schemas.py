#!/usr/bin/env python3
"""
Schema exploration script to understand the structure of both databases
"""

import duckdb
from pathlib import Path

def explore_database_schema(db_path, db_name):
    """Explore and document the schema of a database."""
    print(f"\n{'='*50}")
    print(f"🔍 Exploring {db_name} Database Schema")
    print(f"📄 Path: {db_path}")
    print(f"{'='*50}")
    
    conn = duckdb.connect(str(db_path))
    
    try:
        # Get all tables using DuckDB information schema
        tables = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
        print(f"📊 Found {len(tables)} tables:")
        
        for table in tables:
            table_name = table[0] if isinstance(table, tuple) else table
            print(f"\n📋 Table: {table_name}")
            
            # Get table columns using DuckDB information schema
            try:
                info = conn.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    ORDER BY ordinal_position
                """).fetchall()
                print("   Columns:")
                for col in info:
                    col_name = col[0]
                    col_type = col[1]
                    print(f"     - {col_name}: {col_type}")
                
                # Get sample data
                try:
                    sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
                    print(f"   Sample data ({len(sample)} rows):")
                    for row in sample[:2]:  # Show only 2 rows
                        print(f"     {row}")
                        
                    # Get row count
                    count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                    print(f"   Total rows: {count}")
                    
                except Exception as e:
                    print(f"     ⚠️ Could not fetch sample data: {e}")
                    
            except Exception as e:
                print(f"     ❌ Could not get table info: {e}")
        
        # Get views if any
        try:
            views = conn.execute("SELECT table_name FROM information_schema.views WHERE table_schema = 'main'").fetchall()
            if views:
                print(f"\n👁️ Found {len(views)} views:")
                for view in views:
                    view_name = view[0]
                    print(f"   - {view_name}")
        except Exception as e:
            print(f"   ⚠️ Could not fetch views: {e}")
            
    except Exception as e:
        print(f"❌ Error exploring database: {e}")
    
    finally:
        conn.close()

def main():
    base_path = Path("/Users/david.campos/VibeCode/AICoS-Lab/experiments/ryan_time_analysis")
    calendar_db = base_path / "data/processed/duckdb/calendar_analytics.db"
    slack_db = base_path / "data/processed/duckdb/slack_analytics.db"
    
    print("🚀 Database Schema Exploration")
    print("="*50)
    
    # Explore calendar database
    if calendar_db.exists():
        explore_database_schema(calendar_db, "Calendar")
    else:
        print(f"❌ Calendar database not found at {calendar_db}")
    
    # Explore slack database
    if slack_db.exists():
        explore_database_schema(slack_db, "Slack")
    else:
        print(f"❌ Slack database not found at {slack_db}")

if __name__ == "__main__":
    main()