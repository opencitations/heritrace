# HERITRACE

[<img src="https://img.shields.io/badge/powered%20by-OpenCitations-%239931FC?labelColor=2D22DE" />](http://opencitations.net)
[![Tests](https://github.com/opencitations/heritrace/actions/workflows/python-tests.yml/badge.svg)](https://github.com/opencitations/heritrace/actions/workflows/python-tests.yml)
[![Coverage](https://byob.yarr.is/arcangelo7/badges/opencitations-heritrace-coverage-main)](https://opencitations.github.io/heritrace/coverage/)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/arcangelo7/heritrace)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-red)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-ISC-green)](https://github.com/arcangelo7/heritrace)

HERITRACE (Heritage Enhanced Repository Interface for Tracing, Research, Archival Curation, and Engagement) is a semantic editor designed for professionals in galleries, libraries, archives, and museums (GLAM).

This system facilitates non-technical domain experts in enriching and editing metadata in a semantically robust manner. It is developed with a focus on user-friendliness, provenance management, change tracking, customization, and integration with heterogeneous data sources.

## 📚 Documentation

Complete documentation is available at: **[https://opencitations.github.io/heritrace/](https://opencitations.github.io/heritrace/)**

## 🚀 Quick Start

**Prerequisites:** Docker and Docker Compose

Download HERITRACE configuration:
```bash
curl -o docker-compose.yml https://raw.githubusercontent.com/opencitations/heritrace/main/docker-compose.yml
```

Optionally download database management scripts for quick setup:
```bash
curl -o start-databases.sh https://raw.githubusercontent.com/opencitations/heritrace/main/start-databases.sh
```
```bash
curl -o stop-databases.sh https://raw.githubusercontent.com/opencitations/heritrace/main/stop-databases.sh
```
```bash
curl -o Start-Databases.ps1 https://raw.githubusercontent.com/opencitations/heritrace/main/Start-Databases.ps1
```
```bash
curl -o Stop-Databases.ps1 https://raw.githubusercontent.com/opencitations/heritrace/main/Stop-Databases.ps1
```
```bash
chmod +x start-databases.sh stop-databases.sh
```

**Demo Mode:** HERITRACE runs in demo mode by default (`FLASK_ENV=demo`) for immediate testing without authentication setup.

**Optional Configuration:** Edit `docker-compose.yml` to customize:
- **Database endpoints**: Update `DATASET_DB_URL` and `PROVENANCE_DB_URL` if using your own databases

**Launch Options:**

**Option A: Quick start with provided databases**

Start databases first:
```bash
./start-databases.sh
```
or on Windows:
```bash
.\Start-Databases.ps1
```

Start HERITRACE:
```bash
docker compose up
```

**Option B: Use your existing databases**

Edit docker-compose.yml with your database URLs, then start HERITRACE:
```bash
docker compose up
```


The application will be available at `http://127.0.0.1:5000`


**Stopping the application:**

Stop HERITRACE:
```bash
docker compose down
```

Stop databases (if using provided scripts):
```bash
./stop-databases.sh
```
or on Windows:
```bash
.\Stop-Databases.ps1
```

For production setup with ORCID authentication and advanced configuration, see: [**Application Settings**](https://opencitations.github.io/heritrace/configuration/app-settings/)

## 🎯 Customization

HERITRACE is data model agnostic: use SHACL to define forms and validation constraints for your domain, and YAML display rules to customize the visual presentation.

- [**Application Settings**](https://opencitations.github.io/heritrace/configuration/app-settings/)
- [**SHACL Schema Configuration**](https://opencitations.github.io/heritrace/configuration/shacl/)
- [**Display Rules Configuration**](https://opencitations.github.io/heritrace/configuration/display-rules/)

## 🔧 Development

For development setup and testing:
- [**Testing Guide**](https://opencitations.github.io/heritrace/testing/running-tests/)
- [**CI/CD Pipeline**](https://opencitations.github.io/heritrace/testing/cicd/)


## 📖 Key Features

HERITRACE bridges the gap between sophisticated semantic technologies and the practical needs of cultural heritage professionals:

- **Provenance Management and Change Tracking**: Complete change history and versioning with detailed tracking of who, when, and what changed
- **Time Machine & Time Vault**: Timeline interface for version management and recovery of past versions of the data
- **Intelligent Metadata Management**: Real-time SHACL validation, disambiguation, and dynamic field configuration
- **ORCID Integration**: Secure authentication allowing only authorized personnel to make modifications
- **Seamless RDF Integration**: Works out-of-the-box with existing RDF datasets and any triplestore

For a detailed overview of features and technical foundation, see our [**User Guide**](https://opencitations.github.io/heritrace/user-guide/overview/) for details on how to get started.

## 📄 Paper

Massari, A., & Peroni, S. (2025). HERITRACE: A User-Friendly Semantic Data Editor with Change Tracking and Provenance Management for Cultural Heritage Institutions. *Umanistica Digitale*, 9(20), 317–340. https://doi.org/10.6092/issn.2532-8816/21218

*[Arcangelo Massari](https://www.unibo.it/sitoweb/arcangelo.massari/en) is a PhD candidate in [Cultural Heritage in the digital ecosystem](https://phd.unibo.it/chede/en) at the University of Bologna.*

## 🙏 Acknowledgments

This work has been partially funded by Project PE 0000020 CHANGES - CUP B53C22003780006, NRP Mission 4 Component 2 Investment 1.3, Funded by the European Union - NextGenerationEU.

## 📄 License

This project is licensed under the ISC License. See the [LICENSE](https://github.com/opencitations/heritrace/blob/main/LICENSE) file for details.

## 🔗 Links

- [Documentation](https://opencitations.github.io/heritrace/)
- [OpenCitations](http://opencitations.net)