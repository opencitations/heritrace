<!--
SPDX-FileCopyrightText: 2024-2026 Arcangelo Massari <arcangelo.massari@unibo.it>

SPDX-License-Identifier: ISC
-->

# HERITRACE

[<img src="https://img.shields.io/badge/powered%20by-OpenCitations-%239931FC?labelColor=2D22DE" />](http://opencitations.net)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/opencitations/heritrace)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-red)](https://flask.palletsprojects.com/)
[![Tests](https://github.com/opencitations/heritrace/actions/workflows/python-tests.yml/badge.svg)](https://github.com/opencitations/heritrace/actions/workflows/python-tests.yml)
[![Coverage](https://opencitations.github.io/heritrace/coverage/coverage-badge.svg)](https://opencitations.github.io/heritrace/coverage/)
[![Pyright](https://github.com/opencitations/heritrace/actions/workflows/pyright.yml/badge.svg)](https://github.com/opencitations/heritrace/actions/workflows/pyright.yml)
[![Ruff](https://github.com/opencitations/heritrace/actions/workflows/ruff.yml/badge.svg)](https://github.com/opencitations/heritrace/actions/workflows/ruff.yml)
[![Flutter](https://github.com/opencitations/heritrace/actions/workflows/flutter.yml/badge.svg)](https://github.com/opencitations/heritrace/actions/workflows/flutter.yml)
[![License](https://img.shields.io/badge/license-ISC-green)](https://github.com/opencitations/heritrace)
[![REUSE](https://github.com/opencitations/heritrace/actions/workflows/reuse.yml/badge.svg)](https://github.com/opencitations/heritrace/actions/workflows/reuse.yml)

HERITRACE is a web-based semantic data editor. It allows users without technical background to edit and enrich RDF metadata, while keeping track of every change with full provenance.

The full documentation is at [opencitations.github.io/heritrace](https://opencitations.github.io/heritrace/).

## Quick start

You need [Docker and Docker Compose](https://docs.docker.com/get-started/get-docker/).

```bash
mkdir heritrace && cd heritrace && \
curl -o docker-compose.yml https://raw.githubusercontent.com/opencitations/heritrace/main/docker-compose.yml && \
docker compose up
```

The compose file starts the web application and two Virtuoso databases filled with sample data from OpenCitations Meta, ready for experimenting. On the first start, it copies an example configuration that describes this data into the `config` folder. Once the databases pass their health checks, the application starts at `http://localhost:8000`.

By default HERITRACE runs in demo mode (`FLASK_ENV=demo`), so you can try it without setting up ORCID authentication: every visitor is signed in as a demo user with administrator rights.

### With your own databases

Edit `docker-compose.yml`: remove the `dataset-db`, `provenance-db`, `config-seed`, and `networks` blocks, remove `depends_on` and `networks` from the `web` service, then set `DATASET_DB_URL` and `PROVENANCE_DB_URL` to your database endpoints. On the first start, HERITRACE runs in setup mode: an administrator enters the settings, then defines the resource types in the configuration editor.

```bash
docker compose up
```

### Stopping

```bash
docker compose down
```

For production setup with ORCID authentication, see [Application settings](https://opencitations.github.io/heritrace/configuration/app-settings/).

## Features

- **Provenance and change tracking** -- every edit records who changed what and when, with full version history
- **Time machine** -- browse and restore previous versions of any resource
- **SHACL validation** -- forms and constraints are generated from SHACL shapes, with real-time validation and disambiguation
- **Configuration editor** -- administrators edit the SHACL shapes and the settings in the app, and HERITRACE checks them before saving
- **Merging and recycle bin** -- merge duplicate resources and recover deleted ones
- **ORCID authentication** -- restricts editing to authorized users
- **Works with any RDF dataset** -- connects to any SPARQL-compatible triplestore, no data migration needed

See the [user guide](https://opencitations.github.io/heritrace/user-guide/browsing-catalogue/) for more details.

## Customization

HERITRACE is data model agnostic. You define your domain through SHACL shapes, which drive forms, validation and presentation:

- [Application settings](https://opencitations.github.io/heritrace/configuration/app-settings/)
- [Configuration editor](https://opencitations.github.io/heritrace/configuration/editor/)
- [SHACL schema](https://opencitations.github.io/heritrace/configuration/shacl/)

## Papers

Massari, A., Peroni, S. (2027). HERITRACE: A Domain-Agnostic Framework for SHACL-Driven RDF Curation with Provenance and Change Tracking. In: Koubarakis, M., et al. *The Semantic Web – ISWC 2026*. ISWC 2026. Lecture Notes in Computer Science, vol 17127. Springer, Cham. https://doi.org/10.1007/978-3-032-42026-8_30

Massari, A., & Peroni, S. (2025). HERITRACE: A User-Friendly Semantic Data Editor with Change Tracking and Provenance Management for Cultural Heritage Institutions. *Umanistica Digitale*, 9(20), 317--340. https://doi.org/10.6092/issn.2532-8816/21218

<!-- software-citation-action:start -->
To cite the latest version of this software (4.0.0), use this BibTeX entry:

```bibtex
@software{HERITRACE-4.0.0,
author = {Massari, Arcangelo},
title = {HERITRACE},
url = {https://archive.softwareheritage.org/swh:1:rev:b617ba1bef8278c27696c8212b3456dce50fda7d},
version = {4.0.0},
year = {2026}
}
```
<!-- software-citation-action:end -->

## Acknowledgments

HERITRACE was developed as part of the PhD thesis of [Arcangelo Massari](https://www.unibo.it/sitoweb/arcangelo.massari/en), a joint doctorate between the University of Bologna (PhD in Cultural Heritage in the Digital Ecosystem, Cycle 38) and KU Leuven (Arenberg Doctoral School, Faculty of Engineering Technology), supervised by Silvio Peroni and Anastasia Dimou.

## License

ISC. See the [LICENSE](https://github.com/opencitations/heritrace/blob/main/LICENSE) file.
