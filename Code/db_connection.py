"""
PostgreSQL database connection and utilities
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import psycopg2
from psycopg2 import sql

# Load environment variables from .env file
env_path = Path('.env')
if env_path.exists():
    load_dotenv(env_path)
    print("[OK] .env file loaded")
else:
    # Try parent directory (if running from subdirectory)
    parent_env = Path('..').resolve() / '.env'
    if parent_env.exists():
        load_dotenv(parent_env)
        print(f"[OK] .env file loaded from {parent_env}")
    else:
        print("[WARNING] .env file not found - using environment variables only")

# Database credentials (Local PostgreSQL)
# Force IPv4 (127.0.0.1) to avoid IPv6 authentication issues
# IMPORTANT: All credentials must be set via .env file or environment variables
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')  # MUST be set in .env file
DB_NAME = os.getenv('DB_NAME', 'crypto_predictions')

# Validate required credentials
if not DB_PASSWORD:
    raise ValueError(
        "❌ ERROR: DB_PASSWORD not set!\n"
        "   1. Create .env file in project root (copy from .env.example)\n"
        "   2. Add: DB_PASSWORD=your_actual_password\n"
        "   3. Save and run again"
    )

# Connection string
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=disable"

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=False
)

def test_connection():
    """Test database connection"""
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def get_connection():
    """Get raw psycopg2 connection"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            sslmode='disable'
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def close_connection(conn):
    """Close database connection"""
    if conn:
        conn.close()
        print("✅ Connection closed")

def create_tables():
    """Create all tables if they don't exist"""
    conn = get_connection()
    if not conn:
        print("❌ Could not create tables - no database connection")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create prices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id SERIAL PRIMARY KEY,
                cryptocurrency VARCHAR(50) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open FLOAT NOT NULL,
                high FLOAT NOT NULL,
                low FLOAT NOT NULL,
                close FLOAT NOT NULL,
                volume FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cryptocurrency, timestamp)
            );
        """)
        
        # Create predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id SERIAL PRIMARY KEY,
                cryptocurrency VARCHAR(50) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                prediction FLOAT NOT NULL,
                confidence FLOAT,
                price_at_prediction FLOAT,
                model_version VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id SERIAL PRIMARY KEY,
                cryptocurrency VARCHAR(50) NOT NULL,
                metric_name VARCHAR(100) NOT NULL,
                metric_value FLOAT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                model_version VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                description TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON prices(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_cryptocurrency ON prices(cryptocurrency);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_crypto_time ON prices(cryptocurrency, timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_timestamp ON predictions(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_cryptocurrency ON predictions(cryptocurrency);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_cryptocurrency ON metrics(cryptocurrency);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);")
        
        conn.commit()
        print("✅ Tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        close_connection(conn)

if __name__ == "__main__":
    test_connection()
    create_tables()

if __name__ == "__main__":
    test_connection()
