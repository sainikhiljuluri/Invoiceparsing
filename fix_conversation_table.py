#!/usr/bin/env python3
"""
Quick fix for conversation_memory table issue
"""

import os
import sys
from pathlib import Path
from supabase import create_client

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def fix_conversation_table():
    """Create the conversation_memory table if it doesn't exist"""
    try:
        # Get Supabase credentials from environment
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ Missing Supabase credentials in environment")
            return False
        
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        print("🔄 Creating conversation_memory table...")
        
        # SQL to create the conversation_memory table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS conversation_memory (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255),
            user_query TEXT NOT NULL,
            assistant_response TEXT NOT NULL,
            intent VARCHAR(100),
            entities JSONB,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_conversation_memory_session_id ON conversation_memory(session_id);
        CREATE INDEX IF NOT EXISTS idx_conversation_memory_timestamp ON conversation_memory(timestamp);
        """
        
        # Execute the SQL using Supabase RPC
        try:
            # Try to create the table using a simple insert/select approach
            # First check if table exists by trying to select from it
            result = supabase.table('conversation_memory').select('id').limit(1).execute()
            print("✅ conversation_memory table already exists and is accessible")
            return True
        except Exception as e:
            print(f"⚠️  Table doesn't exist or isn't accessible: {e}")
            print("🔄 Attempting to create table via SQL...")
            
            # Try using the SQL editor endpoint
            try:
                # Use the PostgREST admin API to execute raw SQL
                import requests
                
                headers = {
                    'Authorization': f'Bearer {supabase_key}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=minimal'
                }
                
                # Execute SQL via PostgREST
                sql_url = f"{supabase_url}/rest/v1/rpc/exec_sql"
                response = requests.post(sql_url, 
                    json={'sql': create_table_sql}, 
                    headers=headers
                )
                
                if response.status_code == 200:
                    print("✅ conversation_memory table created successfully!")
                    return True
                else:
                    print(f"❌ Failed to create table: {response.status_code} - {response.text}")
                    return False
                    
            except Exception as sql_error:
                print(f"❌ SQL execution failed: {sql_error}")
                return False
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        return False

if __name__ == "__main__":
    success = fix_conversation_table()
    if success:
        print("🎉 Conversation memory table is ready!")
        print("🔄 Please refresh your browser to try the chat again.")
    else:
        print("❌ Unable to fix the conversation table automatically.")
        print("💡 You may need to manually create the table in your Supabase dashboard.")
    
    sys.exit(0 if success else 1)
