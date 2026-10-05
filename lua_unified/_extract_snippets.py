"""
_extract_snippets.py
Extracts every fenced Lua code block from cmo_comprehensive_unified_library_v3.md,
tags each with its nearest section heading, and writes:
  - snippets/all_recipes.lua        (every block, header-commented)
  - snippets/<topic>.lua            (grouped by top-level section topic)
  - snippets/recipe_manifest.json   (structured records for the RAG)

Stdlib only. Run once to (re)generate. Safe to re-run.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MD = HERE / "cmo_comprehensive_unified_library_v3.md"
SNIP = HERE / "snippets"
SNIP.mkdir(exist_ok=True)

TOPIC_MAP = [
    (r"sim|time|compress|pause|run|halt|scenhas|end.?scenario|blank.?scenario", "sim_control"),
    (r"unit creation|add an aircraft|add a ship|add a submarine|rename|position|heading|side", "units"),
    (r"magazine|loadout|refuel|cargo|reload|weapon.?to", "loadout_cargo"),
    (r"mission", "missions"),
    (r"doctrine|wra", "doctrine"),
    (r"reference point|zone", "refpoints_zones"),
    (r"contact", "contacts"),
    (r"weather|time|score|scenario", "scenario_state"),
    (r"event|trigger|condition|action", "events"),
    (r"side", "sides"),
    (r"minefield|explosion", "minefield"),
    (r"key ?store|key value", "keystore"),
    (r"ui|message|popup|input box|sound|bark", "ui_messages"),
    (r"import|export", "import_export"),
    (r"world|tool|bearing|range|los|elevation|circle", "world_tools"),
    (r"wrapper", "wrappers"),
    (r"recipe|scaffold|raid|cap box|spawn", "recipes"),
    (r"helper|utilit|find a unit|require", "helpers"),
]


def topic_for(heading: str) -> str:
    h = heading.lower()
    for pat, topic in TOPIC_MAP:
        if re.search(pat, h):
            return topic
    return "misc"


def main():
    text = MD.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    current_h2 = ""
    current_h3 = ""
    blocks = []            # list of dicts
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("### "):
            current_h3 = line[4:].strip()
        elif line.startswith("## "):
            current_h2 = line[3:].strip()
            current_h3 = ""
        elif line.startswith("# "):
            current_h2 = line[2:].strip()
            current_h3 = ""
        m = re.match(r"^```lua\s*$", line.strip(), re.IGNORECASE)
        if m:
            code = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            heading = current_h3 or current_h2 or "untitled"
            section = current_h2 or "untitled"
            blocks.append({
                "heading": heading,
                "section": section,
                "topic": topic_for(current_h3 + " " + current_h2),
                "code": "\n".join(code).rstrip(),
            })
        i += 1

    # all_recipes.lua
    with (SNIP / "all_recipes.lua").open("w", encoding="utf-8") as f:
        f.write("-- CMO CommandLua recipe corpus (auto-extracted from master library v3)\n")
        f.write("-- {} blocks\n\n".format(len(blocks)))
        for b in blocks:
            f.write("-- === [{}] {} ===\n".format(b["topic"], b["heading"]))
            f.write(b["code"] + "\n\n")

    # grouped topic files
    by_topic = {}
    for b in blocks:
        by_topic.setdefault(b["topic"], []).append(b)
    for topic, items in sorted(by_topic.items()):
        with (SNIP / (topic + ".lua")).open("w", encoding="utf-8") as f:
            f.write("-- CMO CommandLua recipes: topic '{}'\n\n".format(topic))
            for b in items:
                f.write("-- --- {} ---\n".format(b["heading"]))
                f.write(b["code"] + "\n\n")

    # manifest for RAG
    (SNIP / "recipe_manifest.json").write_text(
        json.dumps(blocks, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("Extracted {} Lua blocks into {} topic files".format(len(blocks), len(by_topic)))
    for topic, items in sorted(by_topic.items()):
        print("  {:18s} {:3d} blocks".format(topic, len(items)))


if __name__ == "__main__":
    main()
