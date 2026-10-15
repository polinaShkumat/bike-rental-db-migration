"""Create bike_store_db.db: the ORIGINAL, non-normalized database with sample data.

In this design the Bikes table stores the manufacturer's country and website in
every bike row. migrate.py moves this data into a normalized (3NF) database.
"""
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parent / "bike_store_db.db"

STATIONS = [(1, "Central Station", "Centrum", 30), (2, "Erasmus Bridge", "Kop van Zuid", 20),
            (3, "Markthal", "Centrum", 25), (4, "Kralingse Plas", "Kralingen", 15),
            (5, "Euromast", "Delfshaven", 18)]
MANUFACTURERS = [("Gazelle", "Netherlands", "https://www.gazelle.com"),
                 ("Batavus", "Netherlands", "https://www.batavus.com"),
                 ("Cube", "Germany", "https://www.cube.eu"),
                 ("Trek", "USA", "https://www.trekbikes.com"),
                 ("VanMoof", "Netherlands", "https://www.vanmoof.com")]
MODELS = {"Gazelle": [("Orange C7", "city"), ("Ultimate T10", "e-bike")],
          "Batavus": [("Finez", "city"), ("Dinsdag", "e-bike")],
          "Cube": [("Attain GTC", "road"), ("Aim Pro", "mountain")],
          "Trek": [("FX 2", "hybrid"), ("Marlin 5", "mountain")],
          "VanMoof": [("S5", "e-bike"), ("A5", "e-bike")]}
FIRST = ["Anna", "Daan", "Sofia", "Lucas", "Olena", "Sem", "Emma", "Noah", "Mila", "Finn", "Iris", "Max"]
LAST = ["de Vries", "Jansen", "Bakker", "Kovalenko", "Visser", "Smit", "Meijer", "Bos"]


def main():
    random.seed(7)
    DB.unlink(missing_ok=True)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE Stations (station_id INTEGER PRIMARY KEY, station_name TEXT, area TEXT, capacity INTEGER);
    CREATE TABLE Customers (customer_id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT);
    CREATE TABLE Bikes (
        bike_id INTEGER PRIMARY KEY, model TEXT, bike_type TEXT,
        manufacturer_name TEXT, manufacturer_country TEXT, manufacturer_website TEXT,
        station_id INTEGER, available INTEGER, price_per_hour INTEGER);
    CREATE TABLE Hires (
        hire_id INTEGER PRIMARY KEY, customer_id INTEGER, bike_id INTEGER,
        start_station_id INTEGER, end_station_id INTEGER,
        start_time TEXT, end_time TEXT, duration_minutes INTEGER);
    """)
    cur.executemany("INSERT INTO Stations VALUES (?, ?, ?, ?);", STATIONS)

    customers = []
    for i in range(1, 41):
        first, last = random.choice(FIRST), random.choice(LAST)
        customers.append((i, first, last, f"{first.lower()}.{last.lower().replace(' ', '')}{i}@example.com"))
    cur.executemany("INSERT INTO Customers VALUES (?, ?, ?, ?);", customers)

    bikes = []
    for i in range(1, 31):
        name, country, website = random.choice(MANUFACTURERS)
        model, bike_type = random.choice(MODELS[name])
        price = 15 if bike_type == "e-bike" else random.choice([8, 10, 12])
        bikes.append((i, model, bike_type, name, country, website,
                      random.randint(1, len(STATIONS)), 1, price))
    cur.executemany("INSERT INTO Bikes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", bikes)

    hires = []
    start = datetime(2026, 5, 1, 8, 0)
    for i in range(1, 151):
        t = start + timedelta(days=random.randint(0, 120), minutes=random.randint(0, 600))
        minutes = random.randint(10, 240)
        hires.append((i, random.randint(1, 40), random.randint(1, 30),
                      random.randint(1, 5), random.randint(1, 5),
                      t.strftime("%Y-%m-%d %H:%M"),
                      (t + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M"), minutes))
    cur.executemany("INSERT INTO Hires VALUES (?, ?, ?, ?, ?, ?, ?, ?);", hires)

    conn.commit()
    conn.close()
    print(f"Created {DB.name}: {len(STATIONS)} stations, {len(customers)} customers, "
          f"{len(bikes)} bikes, {len(hires)} hires.")


if __name__ == "__main__":
    main()
