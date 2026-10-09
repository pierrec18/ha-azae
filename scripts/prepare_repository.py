"""Set real publication metadata locally; no network access or publication."""
import argparse
import json
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument("owner")
parser.add_argument("repository")
args = parser.parse_args()
for value in (args.owner, args.repository):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        parser.error("Use a GitHub owner/repository name, not a full URL")
root = Path(__file__).resolve().parents[1]
path = root / "custom_components/azae/manifest.json"
manifest = json.loads(path.read_text())
url = f"https://github.com/{args.owner}/{args.repository}"
manifest.update(documentation=url, issue_tracker=url + "/issues", codeowners=["@" + args.owner])
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
print("Repository metadata updated. Nothing published.")
