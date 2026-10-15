-- Queries for the normalized database (bike_store_redesign.db)

-- 1. Total number of stations
SELECT COUNT(*) AS total_stations
FROM Stations;

-- 2. Average hourly rental price
SELECT ROUND(AVG(price_per_hour)) AS avg_renting_price
FROM Bikes;

-- 3. Customers ranked by number of rentals
SELECT
  c.customer_id,
  c.first_name,
  c.last_name,
  c.email,
  COUNT(h.hire_id) AS rental_count
FROM Customers c
JOIN Hires h ON c.customer_id = h.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name, c.email
ORDER BY rental_count DESC;

-- 4. Proof that nothing was lost: rebuild the old flat Bikes table with a JOIN
SELECT b.bike_id, b.model, b.bike_type,
       m.manufacturer_name, m.manufacturer_country, m.manufacturer_website,
       b.station_id, b.available, b.price_per_hour
FROM Bikes b
JOIN Manufacturers m ON m.manufacturer_id = b.manufacturer_id
ORDER BY b.bike_id;
