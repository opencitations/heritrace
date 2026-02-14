# HERITRACE

[<img src="https://img.shields.io/badge/powered%20by-OpenCitations-%239931FC?labelColor=2D22DE" />](http://opencitations.net)
[![Tests](https://github.com/opencitations/heritrace/actions/workflows/python-tests.yml/badge.svg)](https://github.com/opencitations/heritrace/actions/workflows/python-tests.yml)
[![Coverage](https://byob.yarr.is/arcangelo7/badges/opencitations-heritrace-coverage-main)](https://opencitations.github.io/heritrace/coverage/)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/arcangelo7/heritrace)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-red)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-ISC-green)](https://github.com/arcangelo7/heritrace)

HERITRACE is a Web-based semantic editor for galleries, libraries, archives, and museums (GLAM). It allows domain experts without technical background to edit and enrich RDF metadata, while keeping track of every change with full provenance.

The full documentation is at [opencitations.github.io/heritrace](https://opencitations.github.io/heritrace/).

## Quick start

You need Docker and Docker Compose.

Download the compose file:
```bash
curl -o docker-compose.yml https://raw.githubusercontent.com/opencitations/heritrace/main/docker-compose.yml
```

Optionally, download the database management scripts:

**Unix/Linux/macOS:**
```bash
curl -o start-databases.sh https://raw.githubusercontent.com/opencitations/heritrace/main/start-databases.sh
curl -o stop-databases.sh https://raw.githubusercontent.com/opencitations/heritrace/main/stop-databases.sh
chmod +x start-databases.sh stop-databases.sh
```

**Windows:**
```bash
curl -o Start-Databases.ps1 https://raw.githubusercontent.com/opencitations/heritrace/main/Start-Databases.ps1
curl -o Stop-Databases.ps1 https://raw.githubusercontent.com/opencitations/heritrace/main/Stop-Databases.ps1
```

By default HERITRACE starts in demo mode (`FLASK_ENV=demo`), so you can try it without setting up ORCID authentication.

### With the provided databases

```bash
./start-databases.sh   # .\Start-Databases.ps1 on Windows
docker compose up
```

### With your own databases

Edit `docker-compose.yml` to set `DATASET_DB_URL` and `PROVENANCE_DB_URL`, then:
```bash
docker compose up
```

The application will be available at `http://localhost:5000`.

### Stopping

```bash
docker compose down
./stop-databases.sh    # if you used the provided databases
```

For production setup with ORCID authentication, see [Application settings](https://opencitations.github.io/heritrace/configuration/app-settings/).

## Features

- **Provenance and change tracking** -- every edit records who changed what and when, with full version history
- **Time machine** -- browse and restore previous versions of any entity
- **SHACL validation** -- forms and constraints are generated from SHACL shapes, with real-time validation and disambiguation
- **ORCID authentication** -- restricts editing to authorized users
- **Works with any RDF dataset** -- connects to any SPARQL-compatible triplestore, no data migration needed

See the [user guide](https://opencitations.github.io/heritrace/user-guide/overview/) for more details.

## Customization

HERITRACE is data model agnostic. You define your domain through SHACL shapes (for forms and validation) and YAML display rules (for presentation):

- [Application settings](https://opencitations.github.io/heritrace/configuration/app-settings/)
- [SHACL schema](https://opencitations.github.io/heritrace/configuration/shacl/)
- [Display rules](https://opencitations.github.io/heritrace/configuration/display-rules/)

## Development

- [Testing guide](https://opencitations.github.io/heritrace/testing/running-tests/)
- [CI/CD pipeline](https://opencitations.github.io/heritrace/testing/cicd/)

## Paper

Massari, A., & Peroni, S. (2025). HERITRACE: A User-Friendly Semantic Data Editor with Change Tracking and Provenance Management for Cultural Heritage Institutions. *Umanistica Digitale*, 9(20), 317--340. https://doi.org/10.6092/issn.2532-8816/21218

## Acknowledgments

HERITRACE was developed as part of the PhD thesis of [Arcangelo Massari](https://www.unibo.it/sitoweb/arcangelo.massari/en), a joint doctorate between the University of Bologna (PhD in Cultural Heritage in the Digital Ecosystem, Cycle 38) and KU Leuven (Arenberg Doctoral School, Faculty of Engineering Technology), supervised by Silvio Peroni and Anastasia Dimou.

## License

ISC. See the [LICENSE](https://github.com/opencitations/heritrace/blob/main/LICENSE) file.