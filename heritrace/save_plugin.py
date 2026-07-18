# SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
#
# SPDX-License-Identifier: ISC

from typing import Protocol

from rdflib_ocdm.ocdm_graph import OCDMGraphCommons


class SavePlugin(Protocol):
    def persist(self, graph_set: OCDMGraphCommons) -> None: ...
