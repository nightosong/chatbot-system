#!/usr/bin/env python3
"""
Database migration script to add metadata column to messages table
This allows storing tool calls and other structured data
"""
import sqlite3
import os
import sys


def migrate_database(db_path: str = "data/conversations.db"):
    """Add metadata column to messages table if it doesn't exist"""

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("No migration needed - database will be created with new schema on first use")
        return True

    print(f"Migrating database at {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if metadata column already exists
        cursor.execute("PRAGMA table_info(messages)")
        columns = [row[1] for row in cursor.fetchall()]

        if "metadata" in columns:
            print("✓ Database already has metadata column - no migration needed")
            conn.close()
            return True

        # Add metadata column
        print("Adding metadata column to messages table...")
        cursor.execute("ALTER TABLE messages ADD COLUMN metadata TEXT")

        conn.commit()
        conn.close()

        print("✓ Migration completed successfully")
        return True

    except Exception as e:
        print(f"✗ Migration failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Allow custom database path as command line argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/conversations.db"

    # Change to backend directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(backend_dir)

    print("=" * 60)
    print("DATABASE MIGRATION SCRIPT")
    print("=" * 60)
    print(f"Database path: {db_path}")
    print()

    success = migrate_database(db_path)

    print()
    print("=" * 60)
    if success:
        print("Migration completed successfully!")
    else:
        print("Migration failed!")
        sys.exit(1)
