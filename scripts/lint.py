#!/usr/bin/env python3
"""Repo lint: frontmatter completeness, hook syntax, README link integrity."""
import re, sys, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
fails = []

for sk in sorted((ROOT/"skills").iterdir()):
    md = sk/"SKILL.md"
    if not md.exists():
        fails.append(f"{sk.name}: missing SKILL.md"); continue
    t = md.read_text(errors="replace")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", t, re.DOTALL)
    if not m:
        fails.append(f"{sk.name}: no frontmatter"); continue
    fm = m.group(1)
    for field in ("name", "description"):
        if not re.search(rf"^{field}:", fm, re.M):
            fails.append(f"{sk.name}: frontmatter missing '{field}:'")

for h in sorted((ROOT/"hooks").iterdir()):
    if h.suffix == ".py":
        r = subprocess.run([sys.executable, "-m", "py_compile", str(h)], capture_output=True)
        if r.returncode: fails.append(f"hooks/{h.name}: py_compile failed")
    elif h.suffix == ".sh":
        r = subprocess.run(["bash", "-n", str(h)], capture_output=True)
        if r.returncode: fails.append(f"hooks/{h.name}: bash -n failed")

readme = (ROOT/"README.md").read_text()
for link in re.findall(r"\]\((?!http)([^)#]+)\)", readme):
    if not (ROOT/link).exists():
        fails.append(f"README: broken link {link}")

if fails:
    print("LINT FAIL:"); [print(" -", f) for f in fails]; sys.exit(1)
print(f"LINT OK — {len(list((ROOT/'skills').iterdir()))} skills, "
      f"{len(list((ROOT/'hooks').iterdir()))} hooks, README links resolve")
