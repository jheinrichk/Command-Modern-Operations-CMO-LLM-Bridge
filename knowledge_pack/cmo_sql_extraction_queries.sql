-- CMO SQLite extraction starter queries
-- Run these in DB Browser for SQLite or another SQLite client.

SELECT name
FROM sqlite_master
WHERE type = 'table'
ORDER BY name;

SELECT name, tbl_name
FROM sqlite_master
WHERE type = 'index'
ORDER BY tbl_name, name;

PRAGMA table_info('TableName');

SELECT *
FROM TableName
LIMIT 25;

SELECT *
FROM TableName
WHERE Name IN (
    'Structure Naval Dock',
    'Single-Unit Airfield 1x 2001-2600m Runway',
    'Single-Unit Port',
    'Structure Military Base',
    'Structure Oil Refinery',
    'Structure Forward Operating Base'
);

SELECT *
FROM TableName
WHERE Name LIKE '%Naval Dock%'
   OR Name LIKE '%Airfield%'
   OR Name LIKE '%Port%'
   OR Name LIKE '%Military Base%'
   OR Name LIKE '%Oil Refinery%'
   OR Name LIKE '%Forward Operating Base%';

SELECT *
FROM TableName
ORDER BY Name;

SELECT *
FROM AircraftTable
ORDER BY Name;

SELECT *
FROM LoadoutTable
ORDER BY Name;

SELECT
    a.*,
    l.*
FROM AircraftTable a
LEFT JOIN LoadoutTable l
    ON a.DBID = l.PlatformDBID
ORDER BY a.Name, l.Name;
