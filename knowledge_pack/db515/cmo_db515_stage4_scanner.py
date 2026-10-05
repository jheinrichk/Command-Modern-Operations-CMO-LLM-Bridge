#!/usr/bin/env python3
"""
CMO DB3K Stage-4 Scanner
------------------------
Builds aircraft-specific loadout and weapon relationships from a Command:
Modern Operations DB3K SQLite database.

Designed for DB3K_515.db3, but it uses table names that are stable in the
schema discovered by the Stage-1 scanner and can work with compatible DB3K
revisions.

No third-party Python packages are required.
"""

import csv
import sqlite3
import sys
import traceback
from pathlib import Path

TARGET_AIRCRAFT = [
    (4935, "F-35C"),
    (4293, "E-2D"),
    (5193, "MH-60R"),
    (3326, "F-35A"),
    (5286, "MQ-9A"),
    (3853, "E-3G"),
    (5456, "F-15E"),
    (1308, "F-4E"),
    (5022, "Mohajer-6"),
]

EXPECTED_TABLES = [
    "DataAircraft",
    "DataAircraftLoadouts",
    "DataLoadout",
    "DataLoadoutWeapons",
    "DataWeaponRecord",
    "DataWeapon",
]

PLATFORM_TABLES = [
    ("Aircraft", "DataAircraft"),
    ("Ship", "DataShip"),
    ("Submarine", "DataSubmarine"),
    ("Facility", "DataFacility"),
    ("GroundUnit", "DataGroundUnit"),
    ("Satellite", "DataSatellite"),
]


def qident(name):
    return '"' + str(name).replace('"', '""') + '"'


def lua_quote(value):
    if value is None:
        return "nil"
    s = str(value)
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\r", "\\r").replace("\n", "\\n")
    return '"' + s + '"'


def lua_scalar(value):
    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return lua_quote(value)


def strip_quotes(value):
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    ).fetchone()
    return row is not None


def table_columns(conn, table):
    return [r["name"] for r in conn.execute(
        "PRAGMA table_info(%s)" % qident(table)
    ).fetchall()]


def require_tables(conn):
    missing = [t for t in EXPECTED_TABLES if not table_exists(conn, t)]
    if missing:
        raise RuntimeError(
            "Required DB3K tables are missing: " + ", ".join(missing)
        )


def export_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in fieldnames})


def fetch_platforms(conn):
    rows = []
    for platform_type, table in PLATFORM_TABLES:
        if not table_exists(conn, table):
            continue
        cols = table_columns(conn, table)
        if "ID" not in cols or "Name" not in cols:
            continue
        extra = []
        for c in ("OperatorCountry", "OperatorService",
                  "YearCommissioned", "YearDecommissioned",
                  "Hypothetical", "Deprecated"):
            if c in cols:
                extra.append(c)
        sql = "SELECT ID, Name%s FROM %s ORDER BY ID" % (
            (", " + ", ".join(qident(c) for c in extra)) if extra else "",
            qident(table)
        )
        for r in conn.execute(sql):
            d = {
                "platform_type": platform_type,
                "dbid": r["ID"],
                "name": r["Name"],
            }
            for c in extra:
                d[c.lower()] = r[c]
            rows.append(d)
    return rows


def fetch_aircraft(conn):
    cols = table_columns(conn, "DataAircraft")
    select_cols = ["ID", "Name"]
    for c in (
        "Category", "Type", "OperatorCountry", "OperatorService",
        "YearCommissioned", "YearDecommissioned", "Hypothetical", "Deprecated"
    ):
        if c in cols:
            select_cols.append(c)

    sql = "SELECT %s FROM DataAircraft ORDER BY ID" % ", ".join(
        qident(c) for c in select_cols
    )
    rows = []
    for r in conn.execute(sql):
        d = {
            "aircraft_dbid": r["ID"],
            "aircraft_name": r["Name"],
        }
        for c in select_cols[2:]:
            d[c.lower()] = r[c]
        rows.append(d)
    return rows


def enum_join(conn, table, alias, source_alias, source_column, out_alias):
    if table_exists(conn, table):
        return (
            " LEFT JOIN %s %s ON %s.ID = %s.%s " %
            (qident(table), alias, alias, source_alias, qident(source_column)),
            "%s.Description AS %s" % (alias, qident(out_alias)),
        )
    return "", "NULL AS %s" % qident(out_alias)


def fetch_aircraft_loadouts(conn):
    joins = []
    enum_selects = []

    for table, alias, column, out_alias in [
        ("EnumLoadoutRole", "er", "LoadoutRole", "role"),
        ("EnumLoadoutTimeOfDay", "et", "TimeofDay", "time_of_day"),
        ("EnumLoadoutWeather", "ew", "Weather", "weather"),
        ("EnumLoadoutMissionProfile", "em", "DefaultMissionProfile", "mission_profile"),
        ("EnumOperatorCountry", "eoc", "OperatorCountry", "operator_country"),
        ("EnumOperatorService", "eos", "OperatorService", "operator_service"),
    ]:
        source_alias = "l" if column in (
            "LoadoutRole", "TimeofDay", "Weather", "DefaultMissionProfile"
        ) else "a"
        j, s = enum_join(conn, table, alias, source_alias, column, out_alias)
        joins.append(j)
        enum_selects.append(s)

    aircraft_cols = set(table_columns(conn, "DataAircraft"))
    loadout_cols = set(table_columns(conn, "DataLoadout"))

    optional_selects = []
    for c in ("OperatorCountry", "OperatorService", "YearCommissioned",
              "YearDecommissioned", "Hypothetical", "Deprecated"):
        optional_selects.append(
            ("a.%s AS %s" % (qident(c), qident("aircraft_" + c.lower())))
            if c in aircraft_cols else
            ("NULL AS %s" % qident("aircraft_" + c.lower()))
        )

    for c in (
        "LoadoutRole", "TimeofDay", "Weather", "DefaultMissionProfile",
        "PayloadWeightDragModifier", "DefaultCombatRadius",
        "DefaultTimeOnStation", "RequiresBuddyIllumination",
        "Hypothetical", "QuickTurnaround", "WinchesterShotgun", "Deprecated"
    ):
        optional_selects.append(
            ("l.%s AS %s" % (qident(c), qident("loadout_" + c.lower())))
            if c in loadout_cols else
            ("NULL AS %s" % qident("loadout_" + c.lower()))
        )

    sql = """
    SELECT
        a.ID AS aircraft_dbid,
        a.Name AS aircraft_name,
        l.ID AS loadout_dbid,
        l.Name AS loadout_name,
        %s,
        %s
    FROM DataAircraft a
    JOIN DataAircraftLoadouts al
      ON al.ID = a.ID
    JOIN DataLoadout l
      ON l.ID = al.ComponentID
    %s
    ORDER BY a.ID, l.ID
    """ % (
        ",\n        ".join(enum_selects),
        ",\n        ".join(optional_selects),
        "\n".join(joins),
    )

    return [dict(r) for r in conn.execute(sql).fetchall()]


def fetch_aircraft_loadout_weapons(conn):
    """
    Resolve the DB3K weapon chain correctly:

        DataLoadoutWeapons.ComponentID
            -> DataWeaponRecord.ID
        DataWeaponRecord.ComponentID
            -> DataWeapon.ID

    DataWeaponRecord is intentionally preserved in the export because it is
    a distinct DB3K component record and can carry load/ROF/multiple metadata.
    """
    joins = []
    enum_selects = []

    for table, alias, column, out_alias in [
        ("EnumLoadoutRole", "er", "LoadoutRole", "role"),
        ("EnumLoadoutTimeOfDay", "et", "TimeofDay", "time_of_day"),
        ("EnumLoadoutWeather", "ew", "Weather", "weather"),
        ("EnumLoadoutMissionProfile", "em", "DefaultMissionProfile", "mission_profile"),
    ]:
        j, s = enum_join(conn, table, alias, "l", column, out_alias)
        joins.append(j)
        enum_selects.append(s)

    lw_cols = set(table_columns(conn, "DataLoadoutWeapons"))
    wr_cols = set(table_columns(conn, "DataWeaponRecord"))

    qty_expr = "lw.ComponentNumber" if "ComponentNumber" in lw_cols else "NULL"
    opt_expr = "lw.Optional" if "Optional" in lw_cols else "NULL"
    int_expr = "lw.Internal" if "Internal" in lw_cols else "NULL"

    def wr_expr(column, alias=None):
        out = alias or column.lower()
        if column in wr_cols:
            return "wr.%s AS %s" % (qident(column), qident(out))
        return "NULL AS %s" % qident(out)

    weapon_record_selects = [
        "wr.ID AS weapon_record_id",
        wr_expr("DefaultLoad", "weapon_record_default_load"),
        wr_expr("MaxLoad", "weapon_record_max_load"),
        wr_expr("ROF", "weapon_record_rof"),
        wr_expr("Multiple", "weapon_record_multiple"),
        wr_expr("Deprecated", "weapon_record_deprecated"),
    ]

    sql = """
    SELECT
        a.ID AS aircraft_dbid,
        a.Name AS aircraft_name,
        l.ID AS loadout_dbid,
        l.Name AS loadout_name,
        %s,
        %s,
        w.ID AS weapon_dbid,
        w.Name AS weapon_name,
        %s AS component_number,
        %s AS optional,
        %s AS internal
    FROM DataAircraft a
    JOIN DataAircraftLoadouts al
      ON al.ID = a.ID
    JOIN DataLoadout l
      ON l.ID = al.ComponentID
    LEFT JOIN DataLoadoutWeapons lw
      ON lw.ID = l.ID
    LEFT JOIN DataWeaponRecord wr
      ON wr.ID = lw.ComponentID
    LEFT JOIN DataWeapon w
      ON w.ID = wr.ComponentID
    %s
    ORDER BY a.ID, l.ID,
             CASE WHEN lw.ComponentNumber IS NULL THEN 0 ELSE lw.ComponentNumber END DESC,
             wr.ID,
             w.ID
    """ % (
        ",\n        ".join(enum_selects),
        ",\n        ".join(weapon_record_selects),
        qty_expr, opt_expr, int_expr,
        "\n".join(joins),
    )

    return [dict(r) for r in conn.execute(sql).fetchall()]

def write_platform_lua(path, platforms):
    lines = [
        "-- Generated from CMO DB3K SQLite database",
        "-- Key format: <PlatformType>:<DBID>",
        "return {"
    ]
    for r in platforms:
        key = "%s:%s" % (r["platform_type"], r["dbid"])
        lines.append(
            "  [%s] = { type=%s, dbid=%s, name=%s }," %
            (lua_quote(key), lua_quote(r["platform_type"]),
             str(r["dbid"]), lua_quote(r["name"]))
        )
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_nested_loadouts(loadouts, weapon_rows):
    aircraft = {}

    for r in loadouts:
        aid = r["aircraft_dbid"]
        lid = r["loadout_dbid"]
        a = aircraft.setdefault(aid, {
            "dbid": aid,
            "name": r["aircraft_name"],
            "loadouts": {}
        })
        a["loadouts"][lid] = {
            "dbid": lid,
            "name": r["loadout_name"],
            "role": r.get("role"),
            "time_of_day": r.get("time_of_day"),
            "weather": r.get("weather"),
            "mission_profile": r.get("mission_profile"),
            "weapons": [],
        }

    for r in weapon_rows:
        aid = r["aircraft_dbid"]
        lid = r["loadout_dbid"]
        if aid not in aircraft or lid not in aircraft[aid]["loadouts"]:
            continue
        if r.get("weapon_dbid") is None:
            continue
        aircraft[aid]["loadouts"][lid]["weapons"].append({
            "record_id": r.get("weapon_record_id"),
            "dbid": r.get("weapon_dbid"),
            "name": r.get("weapon_name"),
            "component_number": r.get("component_number"),
            "optional": r.get("optional"),
            "internal": r.get("internal"),
            "default_load": r.get("weapon_record_default_load"),
            "max_load": r.get("weapon_record_max_load"),
        })
    return aircraft


def write_aircraft_loadouts_lua(path, aircraft_map, only_ids=None):
    lines = [
        "-- Generated from CMO DB3K SQLite database",
        "-- Aircraft DBID -> aircraft-specific loadouts -> weapons",
        "return {"
    ]

    ids = sorted(aircraft_map)
    if only_ids is not None:
        wanted = set(only_ids)
        ids = [x for x in ids if x in wanted]

    for aid in ids:
        a = aircraft_map[aid]
        lines.append("  [%s] = {" % aid)
        lines.append("    dbid=%s," % aid)
        lines.append("    name=%s," % lua_quote(a["name"]))
        lines.append("    loadouts={")
        for lid in sorted(a["loadouts"]):
            l = a["loadouts"][lid]
            lines.append("      [%s] = {" % lid)
            lines.append("        dbid=%s," % lid)
            lines.append("        name=%s," % lua_quote(l["name"]))
            lines.append("        role=%s," % lua_scalar(l.get("role")))
            lines.append("        time_of_day=%s," % lua_scalar(l.get("time_of_day")))
            lines.append("        weather=%s," % lua_scalar(l.get("weather")))
            lines.append("        mission_profile=%s," % lua_scalar(l.get("mission_profile")))
            lines.append("        weapons={")
            for w in l["weapons"]:
                lines.append(
                    "          { record_id=%s, dbid=%s, name=%s, component_number=%s, optional=%s, internal=%s, default_load=%s, max_load=%s }," %
                    (
                        lua_scalar(w.get("record_id")),
                        lua_scalar(w.get("dbid")),
                        lua_scalar(w.get("name")),
                        lua_scalar(w.get("component_number")),
                        lua_scalar(w.get("optional")),
                        lua_scalar(w.get("internal")),
                        lua_scalar(w.get("default_load")),
                        lua_scalar(w.get("max_load")),
                    )
                )
            lines.append("        },")
            lines.append("      },")
        lines.append("    },")
        lines.append("  },")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def aggregate_weapon_components(rows):
    """
    Aggregate DataLoadoutWeapons component rows without losing optional/internal
    distinctions. DefaultLoad/MaxLoad are the weapon counts. ComponentNumber is
    preserved only as the DB component ordinal.
    """
    groups = {}
    for r in rows:
        if r.get("weapon_dbid") is None:
            continue
        key = (
            r.get("weapon_dbid"),
            r.get("weapon_name"),
            int(r.get("optional") or 0),
            int(r.get("internal") or 0),
        )
        g = groups.setdefault(key, {
            "weapon_dbid": r.get("weapon_dbid"),
            "weapon_name": r.get("weapon_name"),
            "optional": int(r.get("optional") or 0),
            "internal": int(r.get("internal") or 0),
            "default_load": 0,
            "max_load": 0,
            "components": [],
            "weapon_record_ids": [],
        })
        dl = r.get("weapon_record_default_load")
        ml = r.get("weapon_record_max_load")
        try:
            g["default_load"] += int(dl or 0)
        except Exception:
            pass
        try:
            g["max_load"] += int(ml or 0)
        except Exception:
            pass
        if r.get("component_number") is not None:
            g["components"].append(r.get("component_number"))
        if r.get("weapon_record_id") is not None:
            g["weapon_record_ids"].append(r.get("weapon_record_id"))
    return sorted(
        groups.values(),
        key=lambda x: (
            x["optional"],
            -x["default_load"],
            str(x["weapon_name"] or "")
        )
    )


def write_weapon_totals_csv(path, weapon_rows):
    fieldnames = [
        "aircraft_dbid", "aircraft_name",
        "loadout_dbid", "loadout_name", "role",
        "weapon_dbid", "weapon_name",
        "optional", "internal",
        "default_quantity", "max_quantity",
        "component_numbers", "weapon_record_ids"
    ]
    grouped = {}
    for r in weapon_rows:
        k = (r.get("aircraft_dbid"), r.get("loadout_dbid"))
        grouped.setdefault(k, []).append(r)

    out = []
    for k, rows in grouped.items():
        first = rows[0]
        for g in aggregate_weapon_components(rows):
            out.append({
                "aircraft_dbid": first.get("aircraft_dbid"),
                "aircraft_name": first.get("aircraft_name"),
                "loadout_dbid": first.get("loadout_dbid"),
                "loadout_name": first.get("loadout_name"),
                "role": first.get("role"),
                "weapon_dbid": g.get("weapon_dbid"),
                "weapon_name": g.get("weapon_name"),
                "optional": g.get("optional"),
                "internal": g.get("internal"),
                "default_quantity": g.get("default_load"),
                "max_quantity": g.get("max_load"),
                "component_numbers": ";".join(
                    str(x) for x in sorted(g.get("components") or [])
                ),
                "weapon_record_ids": ";".join(
                    str(x) for x in sorted(set(g.get("weapon_record_ids") or []))
                ),
            })
    export_csv(path, out, fieldnames)
    return out


def write_target_variant_audit(path, loadouts):
    target_ids = {x[0]: x[1] for x in TARGET_AIRCRAFT}
    seen = {}
    for r in loadouts:
        aid = r.get("aircraft_dbid")
        if aid in target_ids and aid not in seen:
            seen[aid] = r

    fields = [
        "aircraft_dbid", "requested_label", "database_name",
        "operator_country", "operator_service",
        "year_commissioned", "year_decommissioned"
    ]
    rows = []
    for aid, label in TARGET_AIRCRAFT:
        r = seen.get(aid, {})
        rows.append({
            "aircraft_dbid": aid,
            "requested_label": label,
            "database_name": r.get("aircraft_name"),
            "operator_country": r.get("operator_country"),
            "operator_service": r.get("operator_service"),
            "year_commissioned": r.get("aircraft_yearcommissioned"),
            "year_decommissioned": r.get("aircraft_yeardecommissioned"),
        })
    export_csv(path, rows, fields)
    return rows


def write_target_report(path, loadouts, weapon_rows):
    target_ids = {x[0] for x in TARGET_AIRCRAFT}
    by_aircraft = {}
    for r in loadouts:
        if r["aircraft_dbid"] in target_ids:
            by_aircraft.setdefault(r["aircraft_dbid"], []).append(r)

    weapons_by_pair = {}
    for r in weapon_rows:
        if r["aircraft_dbid"] in target_ids:
            weapons_by_pair.setdefault(
                (r["aircraft_dbid"], r["loadout_dbid"]), []
            ).append(r)

    lines = [
        "# Target Aircraft Loadout Report",
        "",
        "Weapon quantities use `DataWeaponRecord.DefaultLoad`; "
        "`DataLoadoutWeapons.ComponentNumber` is treated as a component ordinal, not a quantity.",
        "",
    ]

    for aid, fallback_name in TARGET_AIRCRAFT:
        rows = by_aircraft.get(aid, [])
        actual_name = rows[0]["aircraft_name"] if rows else fallback_name
        lines.append("## %s — DBID %s" % (actual_name, aid))
        lines.append("")
        if rows:
            first = rows[0]
            lines.append(
                "Operator: **%s / %s**" %
                (first.get("operator_country") or "Unknown",
                 first.get("operator_service") or "Unknown")
            )
            lines.append("")
        if not rows:
            lines.append("No aircraft-specific loadouts found.")
            lines.append("")
            continue

        lines.append("Loadouts found: %s" % len(rows))
        lines.append("")
        for r in rows:
            role = r.get("role") or "Unspecified"
            lines.append(
                "- **%s** — Loadout DBID `%s` — %s" %
                (r["loadout_name"], r["loadout_dbid"], role)
            )
            raw = weapons_by_pair.get((aid, r["loadout_dbid"]), [])
            for g in aggregate_weapon_components(raw):
                flags = []
                flags.append("optional" if g["optional"] else "mandatory")
                flags.append("internal" if g["internal"] else "external")
                q = g["default_load"]
                max_q = g["max_load"]
                qtext = "%s" % q
                if max_q != q:
                    qtext += " default / %s max" % max_q
                lines.append(
                    "  - %s × %s — Weapon DBID `%s` — %s" %
                    (
                        qtext,
                        g.get("weapon_name") or "(unnamed weapon)",
                        g.get("weapon_dbid"),
                        ", ".join(flags),
                    )
                )
        lines.append("")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def find_db_candidates(filename="DB3K_515.db3"):
    roots = [
        Path.cwd(),
        Path.home(),
        Path(r"C:\Program Files (x86)\Steam\steamapps\common"),
        Path(r"C:\Program Files\Steam\steamapps\common"),
        Path(r"C:\Matrix Games"),
        Path(r"C:\Program Files (x86)\Matrix Games"),
        Path(r"C:\Program Files\Matrix Games"),
    ]
    found = []
    seen = set()

    for root in roots:
        try:
            p = root / filename
            if p.is_file():
                key = str(p.resolve()).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(p.resolve())
        except Exception:
            pass

    for root in roots[2:]:
        if not root.exists():
            continue
        try:
            for p in root.rglob(filename):
                key = str(p.resolve()).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(p.resolve())
        except Exception:
            pass
    return found


def interactive_paths():
    print("")
    print("CMO DB3K STAGE-4 SCANNER")
    print("========================")
    print("Extracts aircraft -> loadout -> weapon-record -> weapon relationships.")
    print("")

    detected = find_db_candidates()
    if detected:
        print("Detected DB3K_515.db3:")
        for i, p in enumerate(detected, 1):
            print("  %d. %s" % (i, p))
        print("")

    raw = input(
        "Database path%s: " %
        (" [Enter = detected #1]" if detected else "")
    ).strip()

    if not raw and detected:
        db_path = detected[0]
    else:
        db_path = Path(strip_quotes(raw))

    if not db_path.is_file():
        raise FileNotFoundError("Database file not found: %s" % db_path)

    default_out = db_path.parent / "CMO_DB_515_STAGE4"
    raw_out = input(
        'Output folder [Enter = "%s"]: ' % default_out
    ).strip()
    out_dir = Path(strip_quotes(raw_out)) if raw_out else default_out
    return db_path, out_dir


def run(db_path, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        require_tables(conn)

        print("Reading platform tables...")
        platforms = fetch_platforms(conn)

        print("Reading aircraft table...")
        aircraft = fetch_aircraft(conn)

        print("Resolving aircraft-specific loadouts...")
        loadouts = fetch_aircraft_loadouts(conn)

        print("Resolving loadout weapon contents...")
        weapon_rows = fetch_aircraft_loadout_weapons(conn)

        nested = build_nested_loadouts(loadouts, weapon_rows)
        target_ids = [x[0] for x in TARGET_AIRCRAFT]

        platform_fields = [
            "platform_type", "dbid", "name",
            "operatorcountry", "operatorservice",
            "yearcommissioned", "yeardecommissioned",
            "hypothetical", "deprecated"
        ]
        export_csv(out_dir / "cmo_platform_lookup_corrected.csv",
                   platforms, platform_fields)
        write_platform_lua(out_dir / "cmo_platform_lookup_corrected.lua",
                           platforms)

        aircraft_fields = [
            "aircraft_dbid", "aircraft_name", "category", "type",
            "operatorcountry", "operatorservice",
            "yearcommissioned", "yeardecommissioned",
            "hypothetical", "deprecated"
        ]
        export_csv(out_dir / "cmo_aircraft_lookup.csv",
                   aircraft, aircraft_fields)

        loadout_fields = [
            "aircraft_dbid", "aircraft_name",
            "loadout_dbid", "loadout_name",
            "role", "time_of_day", "weather", "mission_profile",
            "operator_country", "operator_service",
            "aircraft_operatorcountry", "aircraft_operatorservice",
            "aircraft_yearcommissioned", "aircraft_yeardecommissioned",
            "aircraft_hypothetical", "aircraft_deprecated",
            "loadout_loadoutrole", "loadout_timeofday",
            "loadout_weather", "loadout_defaultmissionprofile",
            "loadout_payloadweightdragmodifier",
            "loadout_defaultcombatradius",
            "loadout_defaulttimeonstation",
            "loadout_requiresbuddyillumination",
            "loadout_hypothetical",
            "loadout_quickturnaround",
            "loadout_winchestershotgun",
            "loadout_deprecated",
        ]
        export_csv(out_dir / "cmo_aircraft_loadouts.csv",
                   loadouts, loadout_fields)

        weapon_fields = [
            "aircraft_dbid", "aircraft_name",
            "loadout_dbid", "loadout_name",
            "role", "time_of_day", "weather", "mission_profile",
            "weapon_record_id",
            "weapon_record_default_load", "weapon_record_max_load",
            "weapon_record_rof", "weapon_record_multiple",
            "weapon_record_deprecated",
            "weapon_dbid", "weapon_name",
            "component_number", "optional", "internal"
        ]
        export_csv(out_dir / "cmo_aircraft_loadout_weapons.csv",
                   weapon_rows, weapon_fields)

        weapon_totals = write_weapon_totals_csv(
            out_dir / "cmo_aircraft_loadout_weapon_totals.csv",
            weapon_rows
        )
        target_variant_audit = write_target_variant_audit(
            out_dir / "cmo_target_aircraft_variant_audit.csv",
            loadouts
        )

        write_aircraft_loadouts_lua(
            out_dir / "cmo_aircraft_loadouts.lua",
            nested
        )
        write_aircraft_loadouts_lua(
            out_dir / "cmo_target_aircraft_loadouts.lua",
            nested,
            only_ids=target_ids
        )

        target_loadouts = [
            r for r in loadouts if r["aircraft_dbid"] in set(target_ids)
        ]
        target_weapons = [
            r for r in weapon_rows if r["aircraft_dbid"] in set(target_ids)
        ]
        export_csv(
            out_dir / "cmo_target_aircraft_loadouts.csv",
            target_loadouts, loadout_fields
        )
        export_csv(
            out_dir / "cmo_target_aircraft_loadout_weapons.csv",
            target_weapons, weapon_fields
        )

        write_weapon_totals_csv(
            out_dir / "cmo_target_aircraft_loadout_weapon_totals.csv",
            target_weapons
        )
        write_target_report(
            out_dir / "cmo_target_aircraft_loadout_report.md",
            loadouts, weapon_rows
        )

        summary = [
            "# CMO DB3K Stage-4 Extraction Summary",
            "",
            "- Source DB: `%s`" % db_path,
            "- Corrected platform records: `%s`" % len(platforms),
            "- Aircraft records: `%s`" % len(aircraft),
            "- Aircraft/loadout relationships: `%s`" % len(loadouts),
            "- Aircraft/loadout/weapon rows: `%s`" % len(weapon_rows),
            "- Aircraft with at least one loadout: `%s`" % len(nested),
            "",
            "## Key outputs",
            "",
            "- `cmo_aircraft_loadouts.csv` — authoritative aircraft DBID -> loadout DBID relationship",
            "- `cmo_aircraft_loadout_weapons.csv` — raw aircraft -> loadout -> weapon-record component rows",
            "- `cmo_aircraft_loadout_weapon_totals.csv` — corrected weapon counts using DataWeaponRecord.DefaultLoad",
            "- `cmo_target_aircraft_variant_audit.csv` — confirms the country/service actually attached to each target DBID",
            "- `cmo_aircraft_loadouts.lua` — nested Lua lookup table",
            "- `cmo_target_aircraft_loadout_report.md` — readable report for the nine aircraft used in the Hormuz 2026 work",
            "- `cmo_platform_lookup_corrected.csv` — corrected platform catalog built from DataAircraft/DataShip/DataSubmarine/DataFacility/DataGroundUnit/DataSatellite",
            "",
            "## Stage-1 correction",
            "",
            "Stage 1 selected `EnumAircraftFacilityType` instead of the real platform tables. Stage 2 corrected the platform and aircraft/loadout relationship but skipped `DataWeaponRecord`. Stage 3 corrected the table chain. Stage 4 also corrects the field semantics: `DataLoadoutWeapons.ComponentNumber` is preserved as the component ordinal while `DataWeaponRecord.DefaultLoad` and `MaxLoad` are used as the weapon quantities.",
            "",
        ]
        (out_dir / "cmo_stage2_summary.md").write_text(
            "\n".join(summary), encoding="utf-8"
        )

        print("")
        print("COMPLETE")
        print("  Platforms:                  %s" % len(platforms))
        print("  Aircraft:                   %s" % len(aircraft))
        print("  Aircraft/loadout links:     %s" % len(loadouts))
        print("  Loadout/weapon rows:        %s" % len(weapon_rows))
        print("  Output:                     %s" % out_dir)
        return 0
    finally:
        conn.close()


def main():
    interactive = len(sys.argv) < 3
    if interactive:
        db_path, out_dir = interactive_paths()
    else:
        db_path = Path(strip_quotes(sys.argv[1]))
        out_dir = Path(strip_quotes(sys.argv[2]))

    if not db_path.is_file():
        raise FileNotFoundError("Database file not found: %s" % db_path)

    return run(db_path, out_dir)


if __name__ == "__main__":
    rc = 99
    try:
        rc = main()
    except Exception:
        print("")
        print("ERROR")
        print("=====")
        traceback.print_exc()
        rc = 99
    finally:
        if len(sys.argv) < 3:
            print("")
            try:
                input("Press Enter to close...")
            except Exception:
                pass
    raise SystemExit(rc)
