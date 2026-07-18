# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import os
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

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


@dataclass(frozen=True)
class CounterFileState:
    value: int
    offset: int
    line: bytes | None
    existing_lines: int
    last_line_terminated: bool


@dataclass
class CounterFileIndex:
    signature: tuple[int, int, int, int]
    checkpoints: dict[int, int]
    states: dict[int, CounterFileState]


class MetaFilesystemCounterHandler(SupplierAwareCounterHandler):
    checkpoint_interval = 100_000

    def __init__(self, info_dir: str, supplier_prefix: str, base_iri: str) -> None:
        self.info_dir = Path(info_dir)
        self.supplier_prefix = supplier_prefix
        self.base_iri = base_iri.rstrip("/")
        self._indexes: dict[Path, CounterFileIndex] = {}
        self._pending_values: dict[CounterLocation, int] = {}
        self._transaction_active = False

    def should_initialize_from_triplestore(self) -> bool:
        return False

    def begin_counter_transaction(self) -> None:
        if self._transaction_active:
            self.rollback_counter_transaction()
        self._transaction_active = True

    def commit_counter_transaction(self) -> None:
        if not self._transaction_active:
            msg = "No counter transaction is active"
            raise RuntimeError(msg)

        updates_by_path: defaultdict[Path, dict[int, int]] = defaultdict(dict)
        for location, value in self._pending_values.items():
            updates_by_path[location.path][location.line_number] = value

        for path, updates in sorted(updates_by_path.items(), key=lambda item: item[0]):
            path.parent.mkdir(parents=True, exist_ok=True)
            with FileLock(f"{path}.lock"):
                states = {
                    line_number: self._read_counter_state(
                        CounterLocation(path, line_number)
                    )
                    for line_number in sorted(updates)
                }
                self._write_counter_values(path, updates, states)

        self._pending_values.clear()
        self._transaction_active = False

    def rollback_counter_transaction(self) -> None:
        self._pending_values.clear()
        self._transaction_active = False

    def set_counter(self, new_value: int, entity_name: str) -> None:
        if new_value < 0:
            msg = "new_value must be a non-negative integer"
            raise ValueError(msg)

        location = self._resolve_location(entity_name)
        if self._transaction_active:
            self._pending_values[location] = new_value
        else:
            self._update_counter(location, new_value)

    def read_counter(self, entity_name: str) -> int:
        location = self._resolve_location(entity_name)
        if location in self._pending_values:
            return self._pending_values[location]
        return self._read_counter(location)

    def increment_counter(self, entity_name: str) -> int:
        location = self._resolve_location(entity_name)
        if self._transaction_active:
            current_value = self._pending_values.get(location)
            if current_value is None:
                current_value = self._read_counter(location)
            value = current_value + 1
            self._pending_values[location] = value
            return value
        return self._update_counter(location, None)

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

        return CounterLocation(
            self.info_dir / supplier_prefix / f"prov_file_{short_name}.txt",
            get_resource_number(entity_name_string),
        )

    def _read_counter(self, location: CounterLocation) -> int:
        return self._read_counter_state(location).value

    def _read_counter_state(self, location: CounterLocation) -> CounterFileState:
        if not location.path.exists():
            return CounterFileState(
                value=0,
                offset=0,
                line=None,
                existing_lines=0,
                last_line_terminated=True,
            )

        index = self._get_file_index(location.path)
        cached_state = index.states.get(location.line_number)
        if cached_state is not None:
            return cached_state

        scan_from_line = max(
            line_number
            for line_number in index.checkpoints
            if line_number <= location.line_number
        )
        offset = index.checkpoints[scan_from_line]
        existing_lines = scan_from_line - 1
        last_line_terminated = True
        with location.path.open("rb") as counter_file:
            counter_file.seek(offset)
            for line_number, line in enumerate(counter_file, start=scan_from_line):
                if (line_number - 1) % self.checkpoint_interval == 0:
                    index.checkpoints[line_number] = offset
                existing_lines = line_number
                last_line_terminated = line.endswith(b"\n")
                if line_number == location.line_number:
                    value = line.strip()
                    state = CounterFileState(
                        value=int(value) if value else 0,
                        offset=offset,
                        line=line,
                        existing_lines=existing_lines,
                        last_line_terminated=last_line_terminated,
                    )
                    index.states[line_number] = state
                    return state
                offset += len(line)

        state = CounterFileState(
            value=0,
            offset=offset,
            line=None,
            existing_lines=existing_lines,
            last_line_terminated=last_line_terminated,
        )
        index.states[location.line_number] = state
        return state

    def _get_file_index(self, path: Path) -> CounterFileIndex:
        signature = self._file_signature(path)
        index = self._indexes.get(path)
        if index is None or index.signature != signature:
            index = CounterFileIndex(signature, {1: 0}, {})
            self._indexes[path] = index
        return index

    @staticmethod
    def _file_signature(path: Path) -> tuple[int, int, int, int]:
        stat = path.stat()
        return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns

    def _update_counter(
        self,
        location: CounterLocation,
        new_value: int | None,
    ) -> int:
        location.path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(f"{location.path}.lock"):
            state = self._read_counter_state(location)
            value = state.value + 1 if new_value is None else new_value
            self._write_counter_values(
                location.path,
                {location.line_number: value},
                {location.line_number: state},
            )
        return value

    def _write_counter_values(
        self,
        path: Path,
        updates: dict[int, int],
        states: dict[int, CounterFileState],
    ) -> None:
        temporary_path = path.with_name(f".{path.name}.tmp")
        serialized_updates = {
            line_number: self._serialize_counter(value)
            for line_number, value in updates.items()
        }
        same_width = path.exists() and all(
            self._counter_width_unchanged(
                states[line_number], serialized_updates[line_number]
            )
            for line_number in updates
        )

        if same_width:
            shutil.copyfile(path, temporary_path)
            with temporary_path.open("r+b") as temporary_file:
                for line_number in sorted(updates):
                    temporary_file.seek(states[line_number].offset)
                    temporary_file.write(serialized_updates[line_number])
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
        else:
            self._rebuild_counter_file(
                path,
                serialized_updates,
                states,
                temporary_path,
            )

        temporary_path.replace(path)
        if same_width:
            self._refresh_patched_index(path, updates, serialized_updates, states)
        else:
            self._indexes.pop(path, None)

    @staticmethod
    def _counter_width_unchanged(
        state: CounterFileState, serialized_counter: bytes
    ) -> bool:
        return state.line is not None and len(state.line) == len(serialized_counter)

    def _refresh_patched_index(
        self,
        path: Path,
        updates: dict[int, int],
        serialized_updates: dict[int, bytes],
        states: dict[int, CounterFileState],
    ) -> None:
        index = self._indexes.get(path)
        if index is None:
            return
        index.signature = self._file_signature(path)
        for line_number, serialized_counter in serialized_updates.items():
            state = states[line_number]
            index.states[line_number] = CounterFileState(
                value=updates[line_number],
                offset=state.offset,
                line=serialized_counter,
                existing_lines=state.existing_lines,
                last_line_terminated=True,
            )

    def _rebuild_counter_file(
        self,
        path: Path,
        serialized_updates: dict[int, bytes],
        states: dict[int, CounterFileState],
        temporary_path: Path,
    ) -> None:
        with temporary_path.open("wb") as temporary_file:
            existing_updates = []
            for line_number in serialized_updates:
                state = states[line_number]
                if state.line is not None:
                    existing_updates.append((state.offset, line_number, state.line))
            existing_updates.sort()
            missing_lines = sorted(
                line_number
                for line_number in serialized_updates
                if states[line_number].line is None
            )
            if path.exists():
                with path.open("rb") as counter_file:
                    source_offset = 0
                    for offset, line_number, line in existing_updates:
                        counter_file.seek(source_offset)
                        self._copy_bytes(
                            counter_file,
                            temporary_file,
                            offset - source_offset,
                        )
                        temporary_file.write(serialized_updates[line_number])
                        source_offset = offset + len(line)
                    counter_file.seek(source_offset)
                    shutil.copyfileobj(counter_file, temporary_file)

            if missing_lines:
                first_missing_state = states[missing_lines[0]]
                current_line = first_missing_state.existing_lines
                if current_line and not first_missing_state.last_line_terminated:
                    temporary_file.write(b"\n")
                for line_number in missing_lines:
                    temporary_file.write(b"\n" * (line_number - current_line - 1))
                    temporary_file.write(serialized_updates[line_number])
                    current_line = line_number
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

    @staticmethod
    def _copy_bytes(source: BinaryIO, destination: BinaryIO, byte_count: int) -> None:
        remaining = byte_count
        while remaining:
            chunk = source.read(min(remaining, 1024 * 1024))
            if not chunk:
                raise EOFError
            destination.write(chunk)
            remaining -= len(chunk)

    @staticmethod
    def _serialize_counter(value: int) -> bytes:
        return b"\n" if value == 0 else f"{value}\n".encode()
