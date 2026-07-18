# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
from dataclasses import dataclass
from pathlib import Path

from filelock import FileLock
from oc_ocdm.support import get_count, get_prefix, get_resource_number, get_short_name
from rdflib_ocdm.counter_handler.counter_handler import SupplierAwareCounterHandler

from default_components.meta_entities import (
    META_SHORT_NAMES,
    META_URI_ENTITY_TYPE_ABBR,
)


@dataclass(frozen=True)
class CounterLocation:
    path: Path
    line_number: int


class MetaFilesystemCounterHandler(SupplierAwareCounterHandler):
    def __init__(self, info_dir: str, supplier_prefix: str, base_iri: str) -> None:
        self.info_dir = Path(info_dir)
        self.supplier_prefix = supplier_prefix
        self.base_iri = base_iri.rstrip("/")

    def should_initialize_from_triplestore(self) -> bool:
        return False

    def set_counter(self, new_value: int, entity_name: str) -> None:
        if new_value < 0:
            msg = "new_value must be a non-negative integer"
            raise ValueError(msg)

        self._update_counter(self._resolve_location(entity_name), new_value)

    def read_counter(self, entity_name: str) -> int:
        location = self._resolve_location(entity_name)
        return self._read_counter(location)

    def increment_counter(self, entity_name: str) -> int:
        return self._update_counter(self._resolve_location(entity_name), None)

    def _resolve_location(self, entity_name: str) -> CounterLocation:
        entity_name_string = str(entity_name)
        if entity_name_string in META_URI_ENTITY_TYPE_ABBR:
            abbreviation = META_URI_ENTITY_TYPE_ABBR[entity_name_string]
            return CounterLocation(
                self.info_dir / self.supplier_prefix / f"info_file_{abbreviation}.txt",
                1,
            )

        short_name = get_short_name(entity_name_string)
        if short_name not in META_SHORT_NAMES:
            msg = f"Unsupported OpenCitations Meta entity: {entity_name_string}"
            raise ValueError(msg)

        supplier_prefix = get_prefix(entity_name_string)
        resource_identifier = get_count(entity_name_string)
        canonical_uri = (
            f"{self.base_iri}/{short_name}/{supplier_prefix}{resource_identifier}"
        )
        if (
            not supplier_prefix
            or not resource_identifier
            or entity_name_string != canonical_uri
        ):
            msg = f"Unsupported OpenCitations Meta entity: {entity_name_string}"
            raise ValueError(msg)

        if short_name == "ci":
            return CounterLocation(
                self.info_dir
                / supplier_prefix
                / f"prov_file_{short_name}_{resource_identifier}.txt",
                1,
            )

        return CounterLocation(
            self.info_dir / supplier_prefix / f"prov_file_{short_name}.txt",
            get_resource_number(entity_name_string),
        )

    def _read_counter(self, location: CounterLocation) -> int:
        if not location.path.exists():
            return 0

        with location.path.open(encoding="utf-8") as counter_file:
            for line_number, line in enumerate(counter_file, start=1):
                if line_number == location.line_number:
                    value = line.strip()
                    return int(value) if value else 0
        return 0

    def _update_counter(self, location: CounterLocation, new_value: int | None) -> int:
        location.path.parent.mkdir(parents=True, exist_ok=True)
        lock = FileLock(f"{location.path}.lock")
        with lock:
            value = self._read_counter(location) + 1 if new_value is None else new_value
            self._replace_counter_file(location, value)
        return value

    def _replace_counter_file(self, location: CounterLocation, new_value: int) -> None:
        temporary_path = location.path.with_name(f".{location.path.name}.tmp")
        target_written = False
        existing_lines = 0
        last_line_terminated = True
        with temporary_path.open("w", encoding="utf-8") as temporary_file:
            if location.path.exists():
                with location.path.open(encoding="utf-8") as counter_file:
                    for line_number, line in enumerate(counter_file, start=1):
                        existing_lines = line_number
                        last_line_terminated = line.endswith("\n")
                        if line_number == location.line_number:
                            temporary_file.write(self._serialize_counter(new_value))
                            target_written = True
                        else:
                            temporary_file.write(line)

            if not target_written:
                if existing_lines and not last_line_terminated:
                    temporary_file.write("\n")
                temporary_file.write("\n" * (location.line_number - existing_lines - 1))
                temporary_file.write(self._serialize_counter(new_value))

            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        temporary_path.replace(location.path)

    @staticmethod
    def _serialize_counter(value: int) -> str:
        return "\n" if value == 0 else f"{value}\n"
