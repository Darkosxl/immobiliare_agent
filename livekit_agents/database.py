import sqlite3
import shutil
import time
import threading
import os
import json
import dotenv
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

DB_NAME = "real_estate.db"
BACKUP_DIR = "backups"

class Listing(BaseModel):
    name: str
    description: str
    address: str
    price: float
    agency: str
    image_url: Optional[str] = None

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS listings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  description TEXT,
                  address TEXT,
                  price REAL,
                  agency TEXT,
                  image_url TEXT)''')
    
    # Pre-populate with some dummy data if empty for testing
    c.execute("SELECT count(*) FROM listings")
    if c.fetchone()[0] == 0:
        dummy_listings = [
            ("Luxury Python Villa", "A beautiful villa for snakes", "123 Python Way", 1500000, "RinovaAI", "http://example.com/1.jpg"),
            ("Cozy Coder Studio", "Small studio for devs", "404 Not Found St", 500, "RinovaAI", "http://example.com/2.jpg")
        ]
        c.executemany("INSERT INTO listings (name, description, address, price, agency, image_url) VALUES (?, ?, ?, ?, ?, ?)", dummy_listings)
        conn.commit()
        print("Initialized database with dummy data")

    conn.commit()
    conn.close()
    
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    # Start backup thread
    start_backup_service()

def backup_loop():
    print("Backup service started")
    while True:
        # Backup every 24 hours (86400 seconds)
        # For testing purposes, let's just wait and loop. 
        # In production this might be a cron job, but user asked for "constantly back itself up within the vps"
        time.sleep(86400) 
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"real_estate_backup_{timestamp}.db")
            shutil.copy2(DB_NAME, backup_path)
            print(f"Database backed up to {backup_path}")
            
            # Prune old backups? Keep last 5
            backups = sorted([os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith('.db')])
            if len(backups) > 5:
                for b in backups[:-5]:
                    os.remove(b)
                    print(f"Removed old backup: {b}")
                    
        except Exception as e:
            print(f"Backup failed: {e}")

def start_backup_service():
    # Helper to start the background thread
    t = threading.Thread(target=backup_loop, daemon=True)
    t.start()

def getCurrentListings(Real_Estate_Agency=None):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        if Real_Estate_Agency:
            c.execute("SELECT name FROM listings WHERE agency = ?", (Real_Estate_Agency,))
        else:
            c.execute("SELECT name FROM listings")
        rows = c.fetchall()
        
        if not rows:
            return "No listings found."
            
        return ", ".join([row['name'] for row in rows])
    except Exception as e:
        print(f"Error fetching listings: {e}")
        return "Error fetching listings"
    finally:
        conn.close()

def getListing(listing_name):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM listings WHERE name = ?", (listing_name,))
        row = c.fetchone()
        
        if row:
            # Return as Pydantic model so .json() works (as assumed in agent_inbound.py)
            return Listing(
                name=row['name'],
                description=row['description'],
                address=row['address'],
                price=row['price'],
                agency=row['agency'],
                image_url=row['image_url']
            )
        return None
    except Exception as e:
        print(f"Error fetching listing details: {e}")
        return None
    finally:
        conn.close()

def getAllListingsWithCoords():
    """Get all listings that have latitude and longitude coordinates"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM listings WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
        rows = c.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching listings with coords: {e}")
        return []
    finally:
        conn.close()

# Auto-init on module import to ensure table exists
init_db()