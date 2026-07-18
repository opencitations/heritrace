# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

from default_components.meta_filesystem_counter_handler import (
    MetaFilesystemCounterHandler,
)

BASE_IRI = "https://w3id.org/oc/meta"
EXPRESSION = "http://purl.org/spar/fabio/Expression"
AGENT = "http://xmlns.com/foaf/0.1/Agent"
CITATION = "http://purl.org/spar/cito/Citation"
OWL_THING = "http://www.w3.org/2002/07/owl#Thing"


def _increment_many(info_dir: str, entity_name: str, increment_count: int) -> list[int]:
    handler = MetaFilesystemCounterHandler(info_dir, "09110", BASE_IRI)
    return [handler.increment_counter(entity_name) for _index in range(increment_count)]


@pytest.fixture
def counter_handler(tmp_path: Path) -> MetaFilesystemCounterHandler:
    return MetaFilesystemCounterHandler(str(tmp_path), "09110", BASE_IRI)


def test_data_counters_use_the_configured_supplier_prefix(
    counter_handler: MetaFilesystemCounterHandler, tmp_path: Path
) -> None:
    counter_handler.set_counter(42, EXPRESSION)
    counter_handler.set_counter(7, AGENT)
    counter_handler.set_counter(3, OWL_THING)
    counter_handler.set_counter(2, CITATION)

    assert counter_handler.read_counter(EXPRESSION) == 42
    assert counter_handler.increment_counter(EXPRESSION) == 43
    assert (tmp_path / "09110" / "info_file_br.txt").read_text() == "43\n"
    assert (tmp_path / "09110" / "info_file_ra.txt").read_text() == "7\n"
    assert (tmp_path / "09110" / "info_file_en.txt").read_text() == "3\n"
    assert (tmp_path / "09110" / "info_file_ci.txt").read_text() == "2\n"


def test_provenance_counters_derive_prefix_and_line_from_the_entity(
    counter_handler: MetaFilesystemCounterHandler, tmp_path: Path
) -> None:
    first_entity = f"{BASE_IRI}/br/06103"
    second_entity = f"{BASE_IRI}/br/06902"

    counter_handler.set_counter(9, first_entity)
    counter_handler.set_counter(4, second_entity)

    assert counter_handler.read_counter(first_entity) == 9
    assert counter_handler.read_counter(second_entity) == 4
    assert (tmp_path / "0610" / "prov_file_br.txt").read_text() == "\n\n9\n"
    assert (tmp_path / "0690" / "prov_file_br.txt").read_text() == "\n4\n"


def test_zero_counter_is_stored_as_an_empty_line(
    counter_handler: MetaFilesystemCounterHandler, tmp_path: Path
) -> None:
    entity = f"{BASE_IRI}/id/06902"

    counter_handler.set_counter(0, entity)

    assert counter_handler.read_counter(entity) == 0
    assert (tmp_path / "0690" / "prov_file_id.txt").read_text() == "\n\n"


def test_citation_provenance_uses_a_counter_file_per_identifier(
    counter_handler: MetaFilesystemCounterHandler, tmp_path: Path
) -> None:
    first_citation = f"{BASE_IRI}/ci/06101-06102"
    second_citation = f"{BASE_IRI}/ci/06101-06203"

    counter_handler.set_counter(4, first_citation)
    counter_handler.set_counter(7, second_citation)

    assert counter_handler.increment_counter(first_citation) == 5
    assert counter_handler.read_counter(second_citation) == 7
    assert (tmp_path / "0610" / "prov_file_ci_1-06102.txt").read_text() == "5\n"
    assert (tmp_path / "0610" / "prov_file_ci_1-06203.txt").read_text() == "7\n"


def test_rejects_unsupported_entities(
    counter_handler: MetaFilesystemCounterHandler,
) -> None:
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Unsupported OpenCitations Meta entity: https://w3id.org/oc/meta/de/06101"
        ),
    ):
        counter_handler.read_counter(f"{BASE_IRI}/de/06101")


def test_concurrent_processes_increment_the_same_counter(tmp_path: Path) -> None:
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_increment_many, str(tmp_path), EXPRESSION, 10)
            for _index in range(4)
        ]
        values = [value for future in futures for value in future.result()]

    assert sorted(values) == list(range(1, 41))
    assert (tmp_path / "09110" / "info_file_br.txt").read_text() == "40\n"


def test_concurrent_processes_preserve_different_lines(tmp_path: Path) -> None:
    provenance_file = tmp_path / "0610" / "prov_file_br.txt"
    provenance_file.parent.mkdir()
    provenance_file.write_text("4\n8\n")
    first_entity = f"{BASE_IRI}/br/06101"
    second_entity = f"{BASE_IRI}/br/06102"

    with ProcessPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(_increment_many, str(tmp_path), first_entity, 12)
        second_future = executor.submit(
            _increment_many, str(tmp_path), second_entity, 12
        )

    assert first_future.result() == list(range(5, 17))
    assert second_future.result() == list(range(9, 21))
    assert provenance_file.read_text() == "16\n20\n"
