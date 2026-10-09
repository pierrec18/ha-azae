"""Build reproducible, allowlisted manual-install and repository ZIP files."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)
version = json.loads((root / "custom_components/azae/manifest.json").read_text())["version"]

def allowed(path):
    return (path.is_file() and not any(part in {"__pycache__", ".pytest_cache", ".venv", ".git"} for part in path.parts)
            and path.suffix in {".py", ".json", ".md", ".toml", ".txt", ".yml", ".png", ".svg"})

integration = sorted(p for p in (root / "custom_components/azae").rglob("*") if allowed(p))
repository = list(integration)
for directory in ("tests", "scripts", ".github", "assets"):
    repository.extend(p for p in (root / directory).rglob("*") if allowed(p))
repository.extend(root / filename for filename in ("README.md", "VALIDATION.md", "LICENSE", ".gitignore", "hacs.json", "pyproject.toml", "requirements-test.txt"))

hashes = []
for kind, files in (("install", integration + [root / "README.md", root / "LICENSE"]), ("source", repository)):
    target = args.output_dir / f"azae-{kind}-{version}.zip"
    with ZipFile(target, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            info = ZipInfo(path.relative_to(root).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    with ZipFile(target) as archive:
        assert archive.testzip() is None
        assert "custom_components/azae/manifest.json" in archive.namelist()
    hashes.append(f"{hashlib.sha256(target.read_bytes()).hexdigest()}  {target.name}")
    print(target.name)
(args.output_dir / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n")
