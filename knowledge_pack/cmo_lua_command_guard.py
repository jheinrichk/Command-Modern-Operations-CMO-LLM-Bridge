import json
import re
import sys
from pathlib import Path

API_PATTERN = re.compile(
    r"\b(?:ScenEdit_[A-Za-z0-9_]+|VP_[A-Za-z0-9_]+|Tool_[A-Za-z0-9_]+|"
    r"UI_[A-Za-z0-9_]+|World_[A-Za-z0-9_]+|Command_[A-Za-z0-9_]+|"
    r"Exporter_[A-Za-z0-9_]+|GetScenarioTitle|SetScenarioTitle|GetBuildNumber)\b"
)

def main():
    if len(sys.argv) < 3:
        print("Usage: py cmo_lua_command_guard.py cmo_known_api_index.json script.lua")
        return 2

    index = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    known = set(index["symbols"])
    text = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")

    used = sorted(set(API_PATTERN.findall(text)))
    unknown = [x for x in used if x not in known]

    print("CMO API symbols used:", len(used))
    print("Unknown CMO-like symbols:", len(unknown))

    if unknown:
        for symbol in unknown:
            print("UNKNOWN:", symbol)
        print("FAIL: verify unknown symbols before execution.")
        return 1

    print("PASS: no unknown CMO-like API symbols found.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
