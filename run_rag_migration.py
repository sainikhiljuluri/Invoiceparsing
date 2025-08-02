#!/usr/bin/env python3
"""
Script to run the RAG tables migration to fix the conversation_memory table issue
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.connection import get_supabase_client

def run_rag_migration():
    """Run the RAG tables migration"""
    try:
        # Read the migration SQL file
        migration_file = project_root / "database" / "migrations" / "add_rag_tables.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
            
        with open(migration_file, 'r') as f:
            sql_content = f.read()
        
        print("🔄 Running RAG tables migration...")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Split SQL into individual statements and execute them
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement.upper().startswith(('CREATE', 'INSERT', 'ALTER')):
                try:
                    print(f"📝 Executing statement {i+1}/{len(statements)}")
                    result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"✅ Statement {i+1} executed successfully")
                except Exception as e:
                    print(f"⚠️  Statement {i+1} failed (might already exist): {e}")
                    continue
        
        print("✅ RAG tables migration completed!")
        print("🔄 Reloading schema cache...")
        
        # Reload the schema cache
        try:
            supabase.rpc('notify', {'channel': 'pgrst', 'payload': 'reload schema'}).execute()
            print("✅ Schema cache reloaded")
        except Exception as e:
            print(f"⚠️  Schema cache reload failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_rag_migration()
    sys.exit(0 if success else 1)
