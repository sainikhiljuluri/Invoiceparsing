import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check what's loaded
print("Environment Variables Check:")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
print(f"SUPABASE_ANON_KEY: {'SET' if os.getenv('SUPABASE_ANON_KEY') else 'NOT SET'}")
print(f"SUPABASE_SERVICE_KEY: {'SET' if os.getenv('SUPABASE_SERVICE_KEY') else 'NOT SET'}")
print(f"DATABASE_URL: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET'}")

# Test settings import
try:
    from config.settings import settings
    print(f"\nSettings loaded:")
    print(f"Supabase URL from settings: {settings.supabase_url}")
except Exception as e:
    print(f"\nError loading settings: {e}")
