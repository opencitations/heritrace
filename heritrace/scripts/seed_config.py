# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import argparse
import json
import shutil
from pathlib import Path
from uuid import uuid4

from heritrace.configuration.serialization import settings_from_json
from heritrace.configuration.settings import write_settings
from heritrace.configuration.store import SETTINGS_FILE, SHACL_FILE

EXAMPLE_SETTINGS_FILE = "settings.json"


# Files already in the folder stay as they are, so edits made in the app
# survive a restart.
def seed_config(config_dir: Path, example_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    source = example_dir / SHACL_FILE
    if source.exists() and not (config_dir / SHACL_FILE).exists():
        shutil.copyfile(source, config_dir / SHACL_FILE)
    settings_path = config_dir / SETTINGS_FILE
    if not settings_path.exists():
        data = json.loads((example_dir / EXAMPLE_SETTINGS_FILE).read_text())
        write_settings(settings_path, settings_from_json(data), uuid4().hex)


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Fill a HERITRACE configuration folder from an example."
    )
    parser.add_argument("config_dir", type=Path)
    parser.add_argument("example_dir", type=Path)
    arguments = parser.parse_args()
    seed_config(arguments.config_dir, arguments.example_dir)


if __name__ == "__main__":  # pragma: no cover
    main()
