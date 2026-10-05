from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

TARGET_FILES = [
    'cmo_database_schema_reference.md',
    'cmo_dbid_lookup_platforms.csv',
    'cmo_dbid_lookup_platforms.lua',
    'cmo_dbid_lookup_facilities.csv',
    'cmo_dbid_lookup_facilities.lua',
    'cmo_dbid_lookup_weapons.csv',
    'cmo_dbid_lookup_weapons.lua',
    'cmo_dbid_lookup_sensors.csv',
    'cmo_dbid_lookup_sensors.lua',
    'cmo_dbid_lookup_mounts.csv',
    'cmo_dbid_lookup_mounts.lua',
    'cmo_loadout_lookup.csv',
    'cmo_loadout_lookup.lua',
    'cmo_extraction_summary.md',
]

def normalize(text: str) -> str:
    text = unicodedata.normalize('NFKD', str(text))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    return text or 'item'

def lua_quote(s: str) -> str:
    s = str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
    return f'"{s}"'

def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def get_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [row['name'] for row in rows]

def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    return [row['name'] for row in rows]

def write_schema_reference(conn: sqlite3.Connection, out_dir: Path) -> dict[str, list[str]]:
    table_columns = {}
    lines = ['# CMO Database Schema Reference', '', 'Generated from the supplied SQLite database file.', '', '## Tables', '']
    for table in get_tables(conn):
        cols = get_columns(conn, table)
        table_columns[table] = cols
        lines.append(f'### {table}')
        for col in cols:
            lines.append(f'- {col}')
        lines.append('')
    (out_dir / 'cmo_database_schema_reference.md').write_text('\n'.join(lines), encoding='utf-8')
    return table_columns

def choose_name_column(columns: list[str]) -> str | None:
    preferred = ['Name', 'name', 'LongName', 'Long_Name', 'ClassName', 'classname', 'Description', 'description']
    for candidate in preferred:
        if candidate in columns:
            return candidate
    for col in columns:
        c = col.lower()
        if 'name' in c or 'desc' in c:
            return col
    return None

def choose_id_column(columns: list[str]) -> str | None:
    preferred = ['DBID', 'DbID', 'dbid', 'ID', 'Id', 'id']
    for candidate in preferred:
        if candidate in columns:
            return candidate
    return None

def choose_type_column(columns: list[str]) -> str | None:
    preferred = ['Type', 'type', 'Category', 'category', 'Subtype', 'SubType', 'subtype']
    for candidate in preferred:
        if candidate in columns:
            return candidate
    return None

def score_table(table: str, columns: list[str], required_keywords: list[str], type_label: str) -> int:
    score = 0
    t = table.lower()
    cols = ' '.join(c.lower() for c in columns)
    if type_label in t:
        score += 8
    for kw in required_keywords:
        if kw in t:
            score += 4
        if kw in cols:
            score += 2
    if choose_id_column(columns):
        score += 4
    if choose_name_column(columns):
        score += 4
    if choose_type_column(columns):
        score += 1
    return score

def pick_best_table(table_columns: dict[str, list[str]], required_keywords: list[str], type_label: str) -> str | None:
    scored = []
    for table, cols in table_columns.items():
        s = score_table(table, cols, required_keywords, type_label)
        if s > 0:
            scored.append((s, table))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]

def fetch_records(conn: sqlite3.Connection, table: str, columns: list[str]) -> list[dict]:
    quoted_cols = ', '.join(f'"{c}"' for c in columns)
    rows = conn.execute(f'SELECT {quoted_cols} FROM "{table}"').fetchall()
    return [dict(row) for row in rows]

def export_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, '') for k in fieldnames})

def build_lookup_records(rows: list[dict], id_col: str | None, name_col: str | None, type_col: str | None, forced_type: str | None = None) -> list[dict]:
    out = []
    for row in rows:
        name = row.get(name_col) if name_col else None
        if name in (None, ''):
            continue
        rec_type = forced_type if forced_type else (row.get(type_col) if type_col else '')
        rec = {
            'dbid': row.get(id_col) if id_col else '',
            'name': name,
            'type': rec_type if rec_type is not None else '',
            'key': normalize(name),
        }
        out.append(rec)
    return out

def export_lua_lookup(path: Path, records: list[dict], record_fields: list[str]) -> None:
    by_key = defaultdict(list)
    by_name = defaultdict(list)
    by_type = defaultdict(list)
    for idx, rec in enumerate(records, start=1):
        by_key[rec['key']].append(idx)
        by_name[str(rec['name'])].append(idx)
        by_type[str(rec.get('type', ''))].append(idx)

    parts = []
    parts.append('local M = {}\n')
    parts.append('M.records = {\n')
    for rec in records:
        fields = []
        for field in record_fields:
            value = rec.get(field, '')
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                fields.append(f"{field}={json.dumps(value)}")
            else:
                fields.append(f"{field}={lua_quote(value)}")
        parts.append('  {' + ', '.join(fields) + '},\n')
    parts.append('}\n\n')

    def emit_index(name: str, mapping: dict[str, list[int]]) -> None:
        parts.append(f'M.{name} = {{\n')
        for key, idxs in sorted(mapping.items(), key=lambda x: x[0].lower()):
            if len(idxs) == 1:
                parts.append(f'  [{lua_quote(key)}] = {idxs[0]},\n')
            else:
                parts.append(f'  [{lua_quote(key)}] = {{{", ".join(map(str, idxs))}}},\n')
        parts.append('}\n\n')

    emit_index('by_name', by_name)
    emit_index('by_key', by_key)
    emit_index('by_type', by_type)

    parts.append("""function M.normalize(text)
  if text == nil then return nil end
  text = tostring(text)
  local out = text:lower()
  out = out:gsub("[^%w]+", "_")
  out = out:gsub("_+", "_")
  out = out:gsub("^_", "")
  out = out:gsub("_$", "")
  if out == "" then return nil end
  return out
end

local function expand(idx)
  if idx == nil then return nil end
  if type(idx) == "table" then
    local t = {}
    for _, i in ipairs(idx) do
      t[#t + 1] = M.records[i]
    end
    return t
  end
  return M.records[idx]
end

function M.lookup_exact(name)
  return expand(M.by_name[name])
end

function M.lookup_key(key)
  return expand(M.by_key[key])
end

function M.lookup(name)
  local exact = M.by_name[name]
  if exact ~= nil then
    return expand(exact)
  end
  local key = M.normalize(name)
  if key == nil then return nil end
  return expand(M.by_key[key])
end

function M.get_type(type_name)
  local idxs = M.by_type[type_name]
  if idxs == nil then return {} end
  local t = {}
  for _, i in ipairs(idxs) do
    t[#t + 1] = M.records[i]
  end
  return t
end

function M.count()
  return #M.records
end

return M
""")
    path.write_text(''.join(parts), encoding='utf-8')

def export_category(conn: sqlite3.Connection, out_dir: Path, table_columns: dict[str, list[str]], filename_prefix: str, required_keywords: list[str], type_label: str, forced_type: str | None = None) -> dict:
    table = pick_best_table(table_columns, required_keywords, type_label)
    result = {'table': table, 'rows': 0, 'status': 'skipped', 'reason': ''}
    if table is None:
        result['reason'] = 'No likely table found by heuristic'
        return result

    cols = table_columns[table]
    id_col = choose_id_column(cols)
    name_col = choose_name_column(cols)
    type_col = choose_type_column(cols)

    if not name_col:
        result['reason'] = f'Table {table} has no detectable name column'
        return result

    rows = fetch_records(conn, table, cols)
    records = build_lookup_records(rows, id_col, name_col, type_col, forced_type=forced_type)
    if not records:
        result['reason'] = f'Table {table} returned no usable records'
        return result

    csv_fields = ['dbid', 'name', 'type', 'key']
    export_csv(out_dir / f'{filename_prefix}.csv', records, csv_fields)
    export_lua_lookup(out_dir / f'{filename_prefix}.lua', records, ['dbid', 'name', 'type', 'key'])

    result['rows'] = len(records)
    result['status'] = 'ok'
    return result

def export_loadouts(conn: sqlite3.Connection, out_dir: Path, table_columns: dict[str, list[str]]) -> dict:
    table = pick_best_table(table_columns, ['loadout', 'role', 'weather', 'time'], 'loadout')
    result = {'table': table, 'rows': 0, 'status': 'skipped', 'reason': ''}
    if table is None:
        result['reason'] = 'No likely loadout table found by heuristic'
        return result

    cols = table_columns[table]
    id_col = choose_id_column(cols)
    name_col = choose_name_column(cols)
    if not name_col:
        result['reason'] = f'Table {table} has no detectable name column'
        return result

    rows = fetch_records(conn, table, cols)
    records = build_lookup_records(rows, id_col, name_col, choose_type_column(cols), forced_type='Loadout')
    if not records:
        result['reason'] = f'Table {table} returned no usable rows'
        return result

    export_csv(out_dir / 'cmo_loadout_lookup.csv', records, ['dbid', 'name', 'type', 'key'])
    export_lua_lookup(out_dir / 'cmo_loadout_lookup.lua', records, ['dbid', 'name', 'type', 'key'])

    result['rows'] = len(records)
    result['status'] = 'ok'
    return result

def write_summary(out_dir: Path, db_path: Path, category_results: dict[str, dict]) -> None:
    lines = ['# CMO Extraction Summary', '', f'- Source DB: `{db_path}`', '']
    for key, info in category_results.items():
        lines.append(f'## {key}')
        lines.append(f'- table: `{info.get("table")}`')
        lines.append(f'- status: `{info.get("status")}`')
        lines.append(f'- rows: `{info.get("rows")}`')
        reason = info.get('reason')
        if reason:
            lines.append(f'- reason: {reason}')
        lines.append('')
    lines.extend([
        '## Notes',
        '- Results depend on actual SQLite schema.',
        '- Review the generated schema reference if a category was skipped.',
        '- Adjust table and column heuristics in the Python script if needed.',
    ])
    (out_dir / 'cmo_extraction_summary.md').write_text('\n'.join(lines), encoding='utf-8')

def main() -> int:
    if len(sys.argv) < 3:
        print('Usage:')
        print('  py build_cmo_dbid_lookups.py "C:\\Path\\To\\DB3K_512.db3" "C:\\Path\\To\\OutputFolder"')
        return 1

    db_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])

    if not db_path.exists():
        print(f'Database file not found: {db_path}')
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    conn = connect(db_path)
    try:
        table_columns = write_schema_reference(conn, out_dir)
        results = {}
        results['platforms'] = export_category(conn, out_dir, table_columns, 'cmo_dbid_lookup_platforms', ['ship', 'submarine', 'aircraft', 'facility', 'platform', 'unit'], 'platform', forced_type='Platform')
        results['facilities'] = export_category(conn, out_dir, table_columns, 'cmo_dbid_lookup_facilities', ['facility', 'base', 'airfield', 'port'], 'facility', forced_type='Facility')
        results['weapons'] = export_category(conn, out_dir, table_columns, 'cmo_dbid_lookup_weapons', ['weapon', 'warhead', 'missile', 'bomb', 'torpedo'], 'weapon', forced_type='Weapon')
        results['sensors'] = export_category(conn, out_dir, table_columns, 'cmo_dbid_lookup_sensors', ['sensor', 'radar', 'sonar', 'ecm', 'esm'], 'sensor', forced_type='Sensor')
        results['mounts'] = export_category(conn, out_dir, table_columns, 'cmo_dbid_lookup_mounts', ['mount', 'turret', 'launcher'], 'mount', forced_type='Mount')
        results['loadouts'] = export_loadouts(conn, out_dir, table_columns)
        write_summary(out_dir, db_path, results)

        print('Extraction complete.')
        for name in TARGET_FILES:
            p = out_dir / name
            if p.exists():
                print(f'  wrote {p.name}')
        return 0
    finally:
        conn.close()

if __name__ == '__main__':
    raise SystemExit(main())
