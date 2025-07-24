"""
Database configuration and connection management.
"""
import os
from dotenv import load_dotenv
from supabase import AsyncClient, acreate_client, Client, create_client


# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

async def get_supabase_client() -> AsyncClient:
    """
    Get a configured Supabase async client.
    
    Returns:
        AsyncClient: A configured Supabase async client instance
    
    Raises:
        ValueError: If required environment variables are not set
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Missing required environment variables. "
            "Please ensure SUPABASE_URL and SUPABASE_KEY are set in your .env file."
        )
    
    return await acreate_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase_sync_client() -> Client:
    """
    Get a configured Supabase sync client.
    
    Returns:
        Client: A configured Supabase sync client instance
    
    Raises:
        ValueError: If required environment variables are not set
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Missing required environment variables. "
            "Please ensure SUPABASE_URL and SUPABASE_KEY are set in your .env file."
        )
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Database connection string for migrations
DATABASE_URL = os.getenv('DATABASE_URL') 