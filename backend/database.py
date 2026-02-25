import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Database connection pool
connection_pool = None

def init_db_pool():
    """Initialize database connection pool"""
    global connection_pool
    try:
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,  # min and max connections
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'gopashu_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD')
        )
        if connection_pool:
            print("✅ Database connection pool created successfully")
            return True
        return False
    except Exception as e:
        print(f"❌ Error creating connection pool: {e}")
        return False

def get_db_connection():
    """Get a connection from the pool"""
    if connection_pool:
        return connection_pool.getconn()
    return None

def return_db_connection(connection):
    """Return connection to the pool"""
    if connection_pool and connection:
        connection_pool.putconn(connection)

def close_db_pool():
    """Close all connections in the pool"""
    if connection_pool:
        connection_pool.closeall()
        print("✅ Database connection pool closed")

def execute_query(query, params=None, fetch=False, fetch_one=False):
    """
    Execute a database query
    
    Args:
        query: SQL query string
        params: Query parameters tuple
        fetch: Whether to fetch results
        fetch_one: Whether to fetch only one result
        
    Returns:
        Query results or None
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()
        else:
            result = None
            
        connection.commit()
        return result
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"❌ Database error: {e}")
        raise e
    finally:
        if cursor:
            cursor.close()
        if connection:
            return_db_connection(connection)
