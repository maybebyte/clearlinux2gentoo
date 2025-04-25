import json
import portage

# Collect all packages
packages = {}
for cp in portage.db[portage.root]["porttree"].dbapi.cp_all():
    category, pkg = cp.split("/")
    if category not in packages:
        packages[category] = []
    packages[category].append(pkg)

# Save to JSON file
with open("data/gentoo_packages.json", "w", encoding="utf-8") as f:
    json.dump(packages, f, indent=2)
