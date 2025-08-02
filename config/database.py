"""
Database configuration for RAG system
"""

from supabase import create_client, Client
from config.settings import settings

def get_supabase_client() -> Client:
    """Get Supabase client for RAG system"""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key
    )
