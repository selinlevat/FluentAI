"""
FluentAI Database Connection - MySQL with XAMPP
"""
import mysql.connector
from mysql.connector import pooling
from config import settings
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection pool for better performance
db_config = {
    "host": settings.DB_HOST,
    "port": settings.DB_PORT,
    "user": settings.DB_USER,
    "password": settings.DB_PASSWORD,
    "database": settings.DB_NAME,
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": False
}

# Create connection pool
try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="lingualearn_pool",
        pool_size=10,
        pool_reset_session=True,
        **db_config
    )
    logger.info("Database connection pool created successfully")
except Exception as e:
    logger.error(f"Error creating connection pool: {e}")
    connection_pool = None


@contextmanager
def get_db_connection():
    """Get a database connection from the pool"""
    connection = None
    try:
        connection = connection_pool.get_connection()
        yield connection
        connection.commit()
    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if connection:
            connection.close()


@contextmanager
def get_db_cursor(dictionary=True):
    """Get a database cursor"""
    with get_db_connection() as connection:
        cursor = connection.cursor(dictionary=dictionary)
        try:
            yield cursor
        finally:
            cursor.close()


def init_database():
    """Initialize database - create if not exists"""
    try:
        # First connect without database to create it
        conn = mysql.connector.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        conn.close()
        logger.info(f"Database '{settings.DB_NAME}' ready")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False


def execute_query(query: str, params: tuple = None, fetch: bool = True):
    """Execute a query and optionally fetch results"""
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        return cursor.lastrowid


def execute_many(query: str, params_list: list):
    """Execute many queries"""
    with get_db_cursor() as cursor:
        cursor.executemany(query, params_list)
        return cursor.rowcount
