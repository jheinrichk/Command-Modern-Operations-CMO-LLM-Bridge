# Complete DB515 lookup library

`CMO_DB515_FINAL_LOOKUP_LIBRARY.zip` is the complete user-supplied archive,
preserved byte for byte. It contains 15 files (230,173,490 uncompressed bytes),
including full aircraft/loadout/weapon CSV and Lua tables and target-aircraft
reports. Keeping the full dataset compressed avoids committing duplicate large
text tables.

The three files shared with `knowledge_pack/db515/` are byte-identical:
`cmo_aircraft_loadouts.csv`, `cmo_platform_lookup_corrected.csv` and
`README_FINAL.md`. The repository keeps the platform catalog unpacked and reads the identical
aircraft-loadout CSV directly from this archive when no local CSV is present.
No manual extraction is required for bridge retrieval. Extract this archive
separately to use the additional lookup tables.

SHA-256: `6f379b878e1cfdb537e65f56bc07e3e718a2fede3ac7acbd004c3bdb00bf270d`
