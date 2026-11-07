# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

STRATEGIES = ("ASK", "DELETE", "KEEP")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    app_title TEXT NOT NULL,
    app_subtitle TEXT NOT NULL,
    count_limit INTEGER NOT NULL,
    catalogue_default_per_page INTEGER NOT NULL,
    dataset_generation_time TEXT,
    primary_source TEXT NOT NULL,
    orphan_handling TEXT NOT NULL,
    proxy_handling TEXT NOT NULL,
    revision TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS allowed_orcids (
    position INTEGER PRIMARY KEY,
    orcid TEXT NOT NULL
);
"""


@dataclass(kw_only=True)
class Settings:
    primary_source: str
    dataset_generation_time: datetime | None = None
    app_title: str = "HERITRACE"
    app_subtitle: str = "Edit your knowledge graph with provenance"
    count_limit: int = 10000
    catalogue_default_per_page: int = 50
    orcid_safelist: list[str] = field(default_factory=list)
    orphan_handling: str = "ASK"
    proxy_handling: str = "ASK"


@dataclass(frozen=True)
class StoredSettings:
    settings: Settings
    revision: str


def read_settings(path: Path) -> StoredSettings | None:
    if not path.exists():
        return None
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(_SCHEMA)
        row = connection.execute(
            "SELECT app_title, app_subtitle, count_limit, catalogue_default_per_page,"
            " dataset_generation_time, primary_source, orphan_handling,"
            " proxy_handling, revision FROM settings"
        ).fetchone()
        if row is None:
            return None
        orcids = [
            orcid
            for (orcid,) in connection.execute(
                "SELECT orcid FROM allowed_orcids ORDER BY position"
            )
        ]
    (
        app_title,
        app_subtitle,
        count_limit,
        per_page,
        generation_time,
        primary_source,
        orphan_handling,
        proxy_handling,
        revision,
    ) = row
    return StoredSettings(
        Settings(
            app_title=app_title,
            app_subtitle=app_subtitle,
            count_limit=count_limit,
            catalogue_default_per_page=per_page,
            dataset_generation_time=datetime.fromisoformat(generation_time)
            if generation_time is not None
            else None,
            primary_source=primary_source,
            orcid_safelist=orcids,
            orphan_handling=orphan_handling,
            proxy_handling=proxy_handling,
        ),
        revision,
    )


def write_settings(path: Path, settings: Settings, revision: str) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.executescript(_SCHEMA)
        with connection:
            connection.execute(
                "INSERT OR REPLACE INTO settings VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    settings.app_title,
                    settings.app_subtitle,
                    settings.count_limit,
                    settings.catalogue_default_per_page,
                    settings.dataset_generation_time.isoformat()
                    if settings.dataset_generation_time is not None
                    else None,
                    settings.primary_source,
                    settings.orphan_handling,
                    settings.proxy_handling,
                    revision,
                ),
            )
            connection.execute("DELETE FROM allowed_orcids")
            connection.executemany(
                "INSERT INTO allowed_orcids VALUES (?, ?)",
                enumerate(settings.orcid_safelist),
            )
