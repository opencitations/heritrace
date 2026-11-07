# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

import threading
from pathlib import Path

from rdflib import Dataset, Graph

_cache: dict[Path, tuple[int, int, Graph]] = {}
_lock = threading.Lock()


def _parse(path: Path) -> Graph:
    if path.suffix == ".trig":
        return Dataset(default_union=True).parse(path, format="trig")
    return Graph().parse(path, format="turtle")


# Each Gunicorn worker keeps its own copy, parsed again only after another
# process rewrites the file.
def load_rdf_file(path: Path) -> Graph:
    if not path.exists():
        return Dataset(default_union=True) if path.suffix == ".trig" else Graph()
    stat = path.stat()
    with _lock:
        if path in _cache:
            mtime, size, graph = _cache[path]
            if (mtime, size) == (stat.st_mtime_ns, stat.st_size):
                return graph
        graph = _parse(path)
        _cache[path] = (stat.st_mtime_ns, stat.st_size, graph)
        return graph
