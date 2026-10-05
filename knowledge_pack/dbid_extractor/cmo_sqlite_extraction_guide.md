# CMO SQLite Extraction Guide

This package is the next step after the v3 library gap audit.

It does **not** contain already extracted DBIDs because no CMO SQLite database file was uploaded into this chat. Instead, it gives you the extractor tooling needed to generate the missing files from your owned CMO database file.

## Why this package exists

Your current unified library still lacks:
- platform DBIDs
- facility DBIDs
- weapon DBIDs
- sensor DBIDs
- mount DBIDs
- aircraft loadout IDs
- database schema reference

The v3 gap audit explicitly identified those missing items and called for:
- `cmo_dbid_lookup_platforms.lua`
- `cmo_dbid_lookup_facilities.lua`
- `cmo_loadout_lookup.lua`
- `cmo_database_schema_reference.md`
- `cmo_sql_extraction_queries.sql`

This package is designed to generate those from the actual SQLite database file used by your CMO installation.

## What you need

- your actual CMO database file, for example `DB3K_512.db3`
- Python 3 on Windows
- permission to read the DB file and write exports to an output folder

## Suggested Windows command

```powershell
py build_cmo_dbid_lookups.py "C:\Path\To\DB3K_512.db3" "C:\Path\To\OutputFolder"
```

## Why this route matches your environment

Your runtime dump shows:
- CMO runtime build `v1.09 - Build 1825.15`
- scenario DB in use `DB3K_512.db3`
- `io = nil` in the CMO Lua environment

That means external extraction from the SQLite DB is the right place to build authoritative DBID lookup files rather than trying to write them from inside CMO Lua.
