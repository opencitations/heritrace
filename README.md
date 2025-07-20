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

### Option 1: Using Pre-built Docker Images (Recommended)

**Prerequisites:** Docker and Docker Compose

```bash
# Download HERITRACE configuration
curl -o docker-compose.yml https://raw.githubusercontent.com/opencitations/heritrace/main/docker-compose.yml

# Optionally download database start scripts for quick setup
curl -o start-databases.sh https://raw.githubusercontent.com/opencitations/heritrace/main/start-databases.sh      # Linux/MacOS
curl -o Start-Databases.ps1 https://raw.githubusercontent.com/opencitations/heritrace/main/Start-Databases.ps1  # Windows
chmod +x start-databases.sh  # Linux/MacOS only
```

**⚠️ Required:** Edit `docker-compose.yml` to configure:

1. **ORCID authentication** (get from [ORCID Developer Tools](https://orcid.org/developer-tools)):
   - Set redirect URI to: `https://127.0.0.1:5000/auth/callback`
   - Update: `ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`, `ORCID_WHITELIST` (comma-separated ORCID IDs)

2. **Security**: Change `SECRET_KEY` to a secure random value

3. **Database endpoints** (optional for quick start):
   - Update `DATASET_DB_URL` and `PROVENANCE_DB_URL` if using your own databases

**Launch Options:**

**Option A: Quick start with provided databases**
```bash
# Start databases first
./start-databases.sh  # or .\Start-Databases.ps1 on Windows

# Start HERITRACE (edit docker-compose.yml first!)
docker compose up
```

**Option B: Use your existing databases**
```bash
# Edit docker-compose.yml with your database URLs
# Then start HERITRACE
docker compose up
```

### Option 2: Building from Source

**Prerequisites:** Docker, Docker Compose, and Python 3.10+ (for development)

### 1. Clone and Configure
```bash
git clone https://github.com/opencitations/heritrace.git
cd heritrace
cp config.example.py config.py
```

Configure ORCID authentication in `config.py` (same as Option 1 above).

### 2. Start Databases
```bash
# Unix/Linux/MacOS
./start-databases.sh

# Windows PowerShell
.\Start-Databases.ps1
```

### 3. Launch Application
```bash
# Development mode
docker compose -f docker-compose.dev.yaml up --build

# Production mode
docker compose up
```

The application will be available at `https://127.0.0.1:5000`

> **Note:** Your browser will show an SSL certificate warning in development mode - click "Advanced" and proceed to continue.

For more detailed setup instructions, see: [**Detailed Quick Start**](https://opencitations.github.io/heritrace/getting-started/quick-start/)

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