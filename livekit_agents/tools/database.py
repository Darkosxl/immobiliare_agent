import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

class Listing(BaseModel):
    name: str
    description: str
    address: str
    price: float
    agency: str
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

@contextmanager
def get_connection():
    """Context manager for database connections"""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database schema"""
    with get_connection() as conn:
        with conn.cursor() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE,
                description TEXT,
                address TEXT,
                price REAL,
                agency TEXT,
                image_url TEXT,
                latitude REAL,
                longitude REAL
            )''')
            
            # Whitelist table for phone numbers
            c.execute('''CREATE TABLE IF NOT EXISTS whitelist (
                phone_number TEXT PRIMARY KEY,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.commit()
            
            # Check if empty and add dummy data for testing
            c.execute("SELECT count(*) FROM listings")
            if c.fetchone()[0] == 0:
                dummy_listings = [
                    ("Luxury Python Villa", "A beautiful villa for snakes", "123 Python Way", 1500000, "RinovaAI", "http://example.com/1.jpg", None, None),
                    ("Cozy Coder Studio", "Small studio for devs", "404 Not Found St", 500, "RinovaAI", "http://example.com/2.jpg", None, None)
                ]
                c.executemany(
                    "INSERT INTO listings (name, description, address, price, agency, image_url, latitude, longitude) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    dummy_listings
                )
                conn.commit()
                print("Initialized database with dummy data")

def getCurrentListings(Real_Estate_Agency=None):
    """Get all listing names, optionally filtered by agency"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as c:
            try:
                if Real_Estate_Agency:
                    c.execute("SELECT name FROM listings WHERE agency = %s", (Real_Estate_Agency,))
                else:
                    c.execute("SELECT name FROM listings")
                rows = c.fetchall()
                
                if not rows:
                    return "No listings found."
                    
                return ", ".join([row['name'] for row in rows])
            except Exception as e:
                print(f"Error fetching listings: {e}")
                return "Error fetching listings"

def getListing(listing_name):
    """Get a single listing by name"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as c:
            try:
                c.execute("SELECT * FROM listings WHERE name = %s", (listing_name,))
                row = c.fetchone()
                
                if row:
                    return Listing(
                        name=row['name'],
                        description=row['description'],
                        address=row['address'],
                        price=row['price'],
                        agency=row['agency'],
                        image_url=row['image_url'],
                        latitude=row.get('latitude'),
                        longitude=row.get('longitude')
                    )
                return None
            except Exception as e:
                print(f"Error fetching listing details: {e}")
                return None

def getAllListingsWithCoords():
    """Get all listings that have latitude and longitude coordinates"""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as c:
            try:
                c.execute("SELECT * FROM listings WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
                rows = c.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                print(f"Error fetching listings with coords: {e}")
                return []

# ===== WHITELIST FUNCTIONS =====

def is_whitelisted(phone_number: str) -> bool:
    """Check if a phone number is in the whitelist"""
    # Normalize: just compare digits (strip +)
    normalized = phone_number.lstrip("+")
    with get_connection() as conn:
        with conn.cursor() as c:
            try:
                c.execute("SELECT phone_number FROM whitelist")
                for row in c.fetchall():
                    if row[0].lstrip("+") == normalized:
                        return True
                return False
            except Exception as e:
                print(f"Error checking whitelist: {e}")
                return False

def add_to_whitelist(phone_number: str) -> bool:
    """Add a phone number to the whitelist"""
    with get_connection() as conn:
        with conn.cursor() as c:
            try:
                c.execute(
                    "INSERT INTO whitelist (phone_number) VALUES (%s) ON CONFLICT DO NOTHING",
                    (phone_number,)
                )
                conn.commit()
                return True
            except Exception as e:
                print(f"Error adding to whitelist: {e}")
                return False

def remove_from_whitelist(phone_number: str) -> bool:
    """Remove a phone number from the whitelist"""
    with get_connection() as conn:
        with conn.cursor() as c:
            try:
                c.execute("DELETE FROM whitelist WHERE phone_number = %s", (phone_number,))
                conn.commit()
                return True
            except Exception as e:
                print(f"Error removing from whitelist: {e}")
                return False

def get_all_whitelisted() -> list:
    """Get all whitelisted phone numbers"""
    with get_connection() as conn:
        with conn.cursor() as c:
            try:
                c.execute("SELECT phone_number FROM whitelist")
                return [row[0] for row in c.fetchall()]
            except Exception as e:
                print(f"Error fetching whitelist: {e}")
                return []

# Initialize database on module import
try:
    init_db()
except Exception as e:
    print(f"Warning: Could not initialize database: {e}")