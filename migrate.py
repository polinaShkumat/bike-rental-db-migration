"""Bike rental database: migration from a non-normalized design to 3NF.

Why the original bike_store_db is NOT in 3NF
--------------------------------------------
1NF: OK - no multi-valued cells.
2NF: OK - bike_id is a single-column primary key, so partial dependencies are impossible.
3NF: VIOLATED - manufacturer_country and manufacturer_website depend on
     manufacturer_name, not directly on bike_id:

         bike_id -> manufacturer_name -> manufacturer_country / manufacturer_website
         (a transitive dependency)

This repeats the manufacturer's data in every bike row and causes update,
insert and delete anomalies.

Fix: a separate Manufacturers table (manufacturer_id PK), referenced from
Bikes through the manufacturer_id foreign key.
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OLD_DB = BASE_DIR / "bike_store_db.db"
NEW_DB = BASE_DIR / "bike_store_redesign.db"
TABLES = ["Stations", "Customers", "Manufacturers", "Bikes", "Hires"]



# ------------------------------------------------------------------
# 1. Schema of the new (normalized) database
# ------------------------------------------------------------------
def create_schema(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Stations (
        station_id INTEGER PRIMARY KEY,
        station_name TEXT NOT NULL,
        area TEXT NOT NULL,
        capacity INTEGER NOT NULL
    );""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Customers (
        customer_id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE
    );""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Manufacturers (
        manufacturer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        manufacturer_name TEXT NOT NULL UNIQUE,
        manufacturer_country TEXT NOT NULL,
        manufacturer_website TEXT NOT NULL
    );""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Bikes (
        bike_id INTEGER PRIMARY KEY,
        model TEXT NOT NULL,
        bike_type TEXT NOT NULL,
        manufacturer_id INTEGER NOT NULL,
        station_id INTEGER NOT NULL,
        available INTEGER NOT NULL DEFAULT 1,
        price_per_hour INTEGER NOT NULL DEFAULT 10,
        FOREIGN KEY (manufacturer_id) REFERENCES Manufacturers(manufacturer_id),
        FOREIGN KEY (station_id) REFERENCES Stations(station_id)
    );""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS Hires (
        hire_id INTEGER PRIMARY KEY,
        customer_id INTEGER NOT NULL,
        bike_id INTEGER NOT NULL,
        start_station_id INTEGER NOT NULL,
        end_station_id INTEGER,
        start_time TEXT NOT NULL,
        end_time TEXT,
        duration_minutes INTEGER,
        FOREIGN KEY (customer_id) REFERENCES Customers(customer_id),
        FOREIGN KEY (bike_id) REFERENCES Bikes(bike_id),
        FOREIGN KEY (start_station_id) REFERENCES Stations(station_id),
        FOREIGN KEY (end_station_id) REFERENCES Stations(station_id)
    );""")


def count_rows(cur):
    """Number of rows in every table: {table: count}."""
    return {t: cur.execute(f"SELECT COUNT(*) FROM {t};").fetchone()[0] for t in TABLES}


# ------------------------------------------------------------------
# 2. Migration - safe to run again and again
# ------------------------------------------------------------------
# UPSERT = INSERT ... ON CONFLICT DO UPDATE
#   - row does not exist yet  -> it is inserted (new data in old DB)
#   - row already exists      -> it is updated (changed data in old DB)
# So running the script twice never creates duplicates and never
# loses changes. (INSERT OR IGNORE would skip changed rows,
# INSERT OR REPLACE would delete + re-insert the row.)
def migrate():
    if not OLD_DB.exists():
        print(f"{OLD_DB.name} not found. Run 'python create_sample_db.py' first.")
        return False
    src_conn = sqlite3.connect(OLD_DB)
    dst_conn = sqlite3.connect(NEW_DB)
    dst_conn.execute("PRAGMA foreign_keys = ON;")  # SQLite does not check foreign keys without this
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()

    try:
        create_schema(dst_cur)
        before = count_rows(dst_cur)

        # Stations
        stations = src_cur.execute(
            "SELECT station_id, station_name, area, capacity FROM Stations;"
        ).fetchall()
        dst_cur.executemany("""
            INSERT INTO Stations (station_id, station_name, area, capacity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(station_id) DO UPDATE SET
                station_name = excluded.station_name,
                area = excluded.area,
                capacity = excluded.capacity;
        """, stations)

        # Customers
        customers = src_cur.execute(
            "SELECT customer_id, first_name, last_name, email FROM Customers;"
        ).fetchall()
        dst_cur.executemany("""
            INSERT INTO Customers (customer_id, first_name, last_name, email)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(customer_id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                email = excluded.email;
        """, customers)

        # Manufacturers (unique by name -> existing ones keep their id)
        manufacturers = src_cur.execute("""
            SELECT DISTINCT manufacturer_name, manufacturer_country, manufacturer_website
            FROM Bikes;
        """).fetchall()
        dst_cur.executemany("""
            INSERT INTO Manufacturers (manufacturer_name, manufacturer_country, manufacturer_website)
            VALUES (?, ?, ?)
            ON CONFLICT(manufacturer_name) DO UPDATE SET
                manufacturer_country = excluded.manufacturer_country,
                manufacturer_website = excluded.manufacturer_website;
        """, manufacturers)

        # name -> id, built AFTER the insert so new manufacturers are included
        manufacturer_lookup = dict(dst_cur.execute(
            "SELECT manufacturer_name, manufacturer_id FROM Manufacturers;"
        ).fetchall())

        # Bikes (manufacturer_name is replaced by manufacturer_id)
        bikes_data = src_cur.execute("""
            SELECT bike_id, model, bike_type, manufacturer_name, station_id, available, price_per_hour
            FROM Bikes;
        """).fetchall()
        bikes_to_insert = [
            (b[0], b[1], b[2], manufacturer_lookup[b[3]], b[4], b[5], b[6])
            for b in bikes_data
        ]
        dst_cur.executemany("""
            INSERT INTO Bikes (bike_id, model, bike_type, manufacturer_id, station_id, available, price_per_hour)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(bike_id) DO UPDATE SET
                model = excluded.model,
                bike_type = excluded.bike_type,
                manufacturer_id = excluded.manufacturer_id,
                station_id = excluded.station_id,
                available = excluded.available,
                price_per_hour = excluded.price_per_hour;
        """, bikes_to_insert)

        # Hires
        hires = src_cur.execute("""
            SELECT hire_id, customer_id, bike_id, start_station_id, end_station_id,
                   start_time, end_time, duration_minutes
            FROM Hires;
        """).fetchall()
        dst_cur.executemany("""
            INSERT INTO Hires (hire_id, customer_id, bike_id, start_station_id, end_station_id,
                               start_time, end_time, duration_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(hire_id) DO UPDATE SET
                customer_id = excluded.customer_id,
                bike_id = excluded.bike_id,
                start_station_id = excluded.start_station_id,
                end_station_id = excluded.end_station_id,
                start_time = excluded.start_time,
                end_time = excluded.end_time,
                duration_minutes = excluded.duration_minutes;
        """, hires)

        dst_conn.commit()

        after = count_rows(dst_cur)
        print("Migration finished. New rows added per table:")
        for t in TABLES:
            print(f"  {t}: +{after[t] - before[t]} (total {after[t]})")

    except sqlite3.Error as e:
        dst_conn.rollback()  # all or nothing: no half-migrated database
        print("Migration FAILED, nothing was changed:", e)
    finally:
        src_conn.close()
        dst_conn.close()


# ------------------------------------------------------------------
# 3. Search functions: same query on the old and the new database
# ------------------------------------------------------------------
def run_query(db_name, sql, params):
    """Run a query; return rows, or None if the query does not work."""
    try:
        conn = sqlite3.connect(db_name)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"  [{Path(db_name).name}] query does NOT work: {e}")
        return None


def compare(title, sql, params):
    """Run the same search on the old and the new database and compare."""
    print(f"\n=== {title} ===")
    old = run_query(OLD_DB, sql, params)
    new = run_query(NEW_DB, sql, params)

    print("Old database:", old)
    print("New database:", new)

    if old is None or new is None:
        print("Result: search FAILED on at least one database.")
    elif not old and not new:
        print("Result: works on both, but nothing was found.")
    elif sorted(old) == sorted(new):
        print("Result: works on both databases, results MATCH.")
    else:
        print("Result: works, but results DIFFER - run the migration again.")


def search_model(model):
    """Bike model + number of times it was rented out."""
    sql = """
        SELECT b.model, COUNT(h.hire_id) AS times_rented
        FROM Bikes b
        LEFT JOIN Hires h ON h.bike_id = b.bike_id
        WHERE b.model LIKE ?
        GROUP BY b.model;
    """
    compare(f"Model '{model}'", sql, (f"%{model}%",))


def search_customer(name):
    """Customer name + total amount spent (minutes / 60 * price per hour)."""
    sql = """
        SELECT c.first_name, c.last_name,
               ROUND(COALESCE(SUM(h.duration_minutes / 60.0 * b.price_per_hour), 0), 2) AS total_spent
        FROM Customers c
        LEFT JOIN Hires h ON h.customer_id = c.customer_id
        LEFT JOIN Bikes b ON b.bike_id = h.bike_id
        WHERE c.first_name || ' ' || c.last_name LIKE ?
        GROUP BY c.customer_id;
    """
    compare(f"Customer '{name}'", sql, (f"%{name}%",))


def search_bike(bike_id):
    """One specific bike and all customers who rented it."""
    sql = """
        SELECT DISTINCT b.bike_id, b.model, c.first_name, c.last_name
        FROM Hires h
        JOIN Bikes b ON b.bike_id = h.bike_id
        JOIN Customers c ON c.customer_id = h.customer_id
        WHERE b.bike_id = ?
        ORDER BY c.last_name;
    """
    compare(f"Bike #{bike_id}", sql, (bike_id,))


# ------------------------------------------------------------------
# 4. Menu (never crashes on wrong input)
# ------------------------------------------------------------------
def main():
    if migrate() is False:
        return

    while True:
        print("\n1) Search bike model  2) Search customer  3) Search bike by id  "
              "4) Run migration again  5) Quit")
        choice = input("Choice: ").strip()

        if choice == "1":
            search_model(input("Model (or part of it): ").strip())
        elif choice == "2":
            search_customer(input("Customer name (or part of it): ").strip())
        elif choice == "3":
            answer = input("Bike id: ").strip()
            if answer.isdigit():
                search_bike(int(answer))
            else:
                print("Bike id must be a whole number.")
        elif choice == "4":
            migrate()
        elif choice == "5":
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
