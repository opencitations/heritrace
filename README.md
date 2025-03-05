# HERITRACE

[<img src="https://img.shields.io/badge/powered%20by-OpenCitations-%239931FC?labelColor=2D22DE" />](http://opencitations.net)
[![Tests](https://github.com/opencitations/heritrace/actions/workflows/python-tests.yml/badge.svg)](https://github.com/opencitations/heritrace/actions/workflows/python-tests.yml)
[![Coverage](https://byob.yarr.is/arcangelo7/badges/opencitations-heritrace-coverage-main)](https://opencitations.github.io/heritrace/)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/arcangelo7/heritrace)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-red)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-ISC-green)](https://github.com/arcangelo7/heritrace)

HERITRACE (Heritage Enhanced Repository Interface for Tracing, Research, Archival Curation, and Engagement) is a semantic editor designed for professionals in galleries, libraries, archives, and museums (GLAM).

This system facilitates non-technical domain experts in enriching and editing metadata in a semantically robust manner. It is developed with a focus on user-friendliness, provenance management, change tracking, customization, and integration with heterogeneous data sources.

## Configuration

A template configuration file is provided as `config.example.py`. To get started:
1. Copy `config.example.py` to `config.py`
2. Update the configuration values according to your needs
3. Make sure to change sensitive values like `SECRET_KEY` and ORCID credentials

Before using HERITRACE, configure the application by editing the `config.py` file. The configuration settings are as follows:

```python
class Config(object):
    APP_TITLE = 'Your App Title'
    APP_SUBTITLE = 'Your App Subtitle'
    
    SECRET_KEY = 'your-secret-key-here'  # Change this to a secure random string
    CACHE_FILE = 'cache.json'
    CACHE_VALIDITY_DAYS = 7

    DATASET_DB_TRIPLESTORE = 'virtuoso'  # virtuoso or blazegraph
    DATASET_DB_TEXT_INDEX_ENABLED = True
    PROVENANCE_DB_TRIPLESTORE = 'virtuoso'  # virtuoso or blazegraph
    
    DATASET_DB_URL = 'http://localhost:8999/sparql'
    PROVENANCE_DB_URL = 'http://localhost:8998/sparql'
    
    DATASET_IS_QUADSTORE = True
    PROVENANCE_IS_QUADSTORE = True
    
    DATASET_GENERATION_TIME = '2024-09-16T00:00:00+02:00'
    URI_GENERATOR = meta_uri_generator
    COUNTER_HANDLER = counter_handler
    LANGUAGES = ['en', 'it']
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_HERITRACE_DIR, 'babel', 'translations')
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_HERITRACE_DIR, 'change_tracking.json')
    PRIMARY_SOURCE = 'https://doi.org/your-doi'
    SHACL_PATH = shacl_path
    DISPLAY_RULES_PATH = display_rules_path

    # ORCID Integration Settings
    ORCID_CLIENT_ID = 'your-client-id'
    ORCID_CLIENT_SECRET = 'your-client-secret'
    ORCID_AUTHORIZE_URL = 'https://orcid.org/oauth/authorize'
    ORCID_TOKEN_URL = 'https://orcid.org/oauth/token'
    ORCID_API_URL = 'https://pub.orcid.org/v2.1'
    ORCID_SCOPE = '/authenticate'
    ORCID_WHITELIST = [
        'your-allowed-orcid-1',
        'your-allowed-orcid-2'
    ]

    ORPHAN_HANDLING_STRATEGY = OrphanHandlingStrategy.ASK
    PROXY_HANDLING_STRATEGY = ProxyHandlingStrategy.DELETE
```

* APP_TITLE: The title of the application shown in the interface.
* APP_SUBTITLE: The subtitle of the application shown in the interface.
* SECRET_KEY: A secret key for the application security.
* CACHE_FILE: The name of the file used for caching.
* CACHE_VALIDITY_DAYS: Number of days the cache remains valid.
* DATASET_DB_TRIPLESTORE: The type of triplestore used for the dataset ('virtuoso' or 'blazegraph').
* DATASET_DB_TEXT_INDEX_ENABLED: Whether text indexing is enabled for the dataset.
* PROVENANCE_DB_TRIPLESTORE: The type of triplestore used for provenance data.
* DATASET_DB_URL: SPARQL endpoint URL for the dataset.
* PROVENANCE_DB_URL: SPARQL endpoint URL for provenance data.
* DATASET_IS_QUADSTORE: Whether the dataset uses a quadstore.
* PROVENANCE_IS_QUADSTORE: Whether the provenance data uses a quadstore.
* DATASET_GENERATION_TIME: Timestamp for dataset generation.
* URI_GENERATOR: The generator for URIs (configured as meta_uri_generator).
* COUNTER_HANDLER: Handles counters using SQLite.
* LANGUAGES: Supported languages.
* BABEL_TRANSLATION_DIRECTORIES: Translation directories for Babel.
* CHANGE_TRACKING_CONFIG: Path to the change tracking configuration file.
* PRIMARY_SOURCE: Primary source of data (DOI reference).
* SHACL_PATH: Path to the SHACL file for data model customization.
* DISPLAY_RULES_PATH: Path to the YAML file for interface customization.
* ORCID_*: ORCID integration settings for authentication.
* ORPHAN_HANDLING_STRATEGY: Strategy for handling orphaned entities (ASK = prompt user).
* PROXY_HANDLING_STRATEGY: Strategy for handling proxy entities (DELETE = automatic removal).

Both ORPHAN_HANDLING_STRATEGY and PROXY_HANDLING_STRATEGY can be set to one of three values:
  - DELETE: Automatically delete the entities without asking
  - ASK: Prompt the user before deleting
  - KEEP: Keep the entities (do nothing)

Orphaned entities are resources that would no longer be connected to any other resource in the dataset after a deletion.
Proxy entities are intermediate relationships that connect resources together.

## SHACL File

The SHACL (Shapes Constraint Language) file is crucial for defining the data model in HERITRACE. It specifies classes, properties, and constraints for each property in the RDF graph. For instance, the provided SHACL example outlines a `BibliographicResourceShape`, targeting the class `fabio:Expression` and defining properties like `datacite:hasIdentifier`, `dcterms:title`, and relationships such as `frbr:partOf`. These specifications ensure that the metadata adheres to the defined structure and constraints.

```ttl
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <http://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

@prefix datacite: <http://purl.org/spar/datacite/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix doco: <http://purl.org/spar/doco/> .
@prefix fabio: <http://purl.org/spar/fabio/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix frbr: <http://purl.org/vocab/frbr/core#> .
@prefix literal: <http://www.essepuntato.it/2010/06/literalreification/> .
@prefix oco: <https://w3id.org/oc/ontology/> .
@prefix prism: <http://prismstandard.org/namespaces/basic/2.0/> .
@prefix pro: <http://purl.org/spar/pro/> .

# BibliographicResource
schema:BibliographicResourceShape
	a sh:NodeShape ;
  sh:targetClass fabio:Expression ;
  sh:property
  [
    sh:path datacite:hasIdentifier ;
    sh:class datacite:Identifier ;
  ] ;
  sh:property
  [
    sh:path rdf:type ;
    sh:hasValue fabio:Expression ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
  ] ;
  sh:property
	[
    sh:path rdf:type ;
    sh:in (fabio:ArchivalDocument
      fabio:Book
      fabio:BookChapter
      doco:Part
      fabio:ExpressionCollection
      fabio:BookSeries
      fabio:BookSet
      fabio:DataFile
      fabio:Thesis
      fabio:JournalArticle
      fabio:JournalIssue
      fabio:JournalVolume
      fabio:Journal
      fabio:ProceedingsPaper
      fabio:AcademicProceedings
      fabio:ReferenceBook
      fabio:ReferenceEntry
      fabio:ReportDocument
      fabio:Series
      fabio:SpecificationDocument) ;
    sh:minCount 0 ;
    sh:maxCount 1 ;
  ] ;
  sh:property
  [
    sh:path dcterms:title ;
    sh:datatype xsd:string ;
    sh:minCount 0 ;
    sh:maxCount 1 ;
  ] ;
  sh:property
  [
    sh:path fabio:hasSubtitle ;
    sh:datatype xsd:string ;
    sh:minCount 0 ;
    sh:maxCount 1 ;
  ] ;
  sh:property
  [
    sh:path frbr:partOf ;
    sh:class fabio:Expression ;
    sh:minCount 0 ;
    sh:maxCount 1 ;
  ] ;
  sh:property
  [
    sh:path prism:publicationDate ;
    sh:or (
      [ sh:datatype xsd:date ]
      [ sh:datatype xsd:gYearMonth ]
      [ sh:datatype xsd:gYear ]
    ) ;
    sh:minCount 0 ;
    sh:maxCount 1 ;
  ] ;
  sh:property
  [
    sh:path frbr:embodiment ;
    sh:class fabio:Manifestation ;
    sh:minCount 0 ;
    sh:maxCount 1 ;
  ] ;
  sh:property
  [
    sh:path fabio:hasSequenceIdentifier ;
    sh:datatype xsd:string ;
    sh:minCount 0 ;
    sh:maxCount 1 ;
  ] ;
  sh:property
  [
    sh:path pro:isDocumentContextFor ;
    sh:class pro:RoleInTime ;
  ] ;
  sh:property
  [
    sh:path [sh:inversePath frbr:partOf] ;
    sh:class fabio:Expression ;
  ] 
.
```

## YAML Display Rules File

The YAML file for display rules allows for presentation customizations of the data model. It defines how properties should be displayed and handled in the user interface. Here's an example configuration for a Journal Article:

```yaml
- class: "http://purl.org/spar/fabio/JournalArticle"
  priority: 1
  shouldBeDisplayed: true
  displayName: "Journal Article"
  fetchUriDisplay: |
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX fabio: <http://purl.org/spar/fabio/>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX pro: <http://purl.org/spar/pro/>
    PREFIX prism: <http://prismstandard.org/namespaces/basic/2.0/>
    PREFIX frbr: <http://purl.org/vocab/frbr/core#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?display
    WHERE {
      # SPARQL query to generate a display string for this entity
      # This creates a formatted citation-like display in the UI
    }
  displayProperties:
    - property: "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
      displayName: "Type"
      shouldBeDisplayed: true
      supportsSearch: false
      
    - property: "http://purl.org/spar/datacite/hasIdentifier"
      displayName: "Identifier"
      shouldBeDisplayed: true
      fetchValueFromQuery: |
        PREFIX datacite: <http://purl.org/spar/datacite/>
        PREFIX literal: <http://www.essepuntato.it/2010/06/literalreification/>
        SELECT (CONCAT(STRAFTER(STR(?scheme), "http://purl.org/spar/datacite/"), ":", ?literal) AS ?id) ?identifier
        WHERE {
            [[subject]] datacite:hasIdentifier ?identifier.
            VALUES (?identifier) {([[value]])}
            ?identifier datacite:usesIdentifierScheme ?scheme;
                      literal:hasLiteralValue ?literal.
        }
      supportsSearch: true
      
    - property: "http://purl.org/dc/terms/title"
      displayName: "Title"
      shouldBeDisplayed: true
      inputType: "textarea"
      supportsSearch: true
      
    - property: "http://purl.org/dc/terms/description"
      displayName: "Description"
      shouldBeDisplayed: true
      inputType: "textarea"
      supportsSearch: true
      
    - property: "http://purl.org/dc/terms/abstract"
      displayName: "Abstract"
      shouldBeDisplayed: true
      inputType: "textarea"
      supportsSearch: true
      
    - property: "http://prismstandard.org/namespaces/basic/2.0/keyword"
      displayName: "Keyword"
      shouldBeDisplayed: true
      inputType: "tag"
      supportsSearch: true
      
    - property: "http://purl.org/spar/pro/isDocumentContextFor"
      orderedBy: "https://w3id.org/oc/ontology/hasNext"
      supportsSearch: true
      intermediateRelation:
        class: "http://purl.org/spar/pro/RoleInTime"
        targetEntityType: "http://xmlns.com/foaf/0.1/Agent"
      displayRules:
        - shape: "http://schema.org/AuthorShape"
          displayName: "Author"
          fetchValueFromQuery: |
            PREFIX pro: <http://purl.org/spar/pro/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX datacite: <http://purl.org/spar/datacite/>
            PREFIX literal: <http://www.essepuntato.it/2010/06/literalreification/>
            SELECT DISTINCT ?formattedName ?ra WHERE {
              [[value]] pro:isHeldBy ?ra;
                  pro:withRole pro:author.
              OPTIONAL { ?ra foaf:name ?name. }
              OPTIONAL { ?ra foaf:familyName ?familyName. }
              OPTIONAL { ?ra foaf:givenName ?givenName. }
              BIND(
                  IF(BOUND(?name), ?name,
                      IF(BOUND(?familyName) && BOUND(?givenName), 
                          CONCAT(?familyName, ", ", ?givenName),
                          IF(BOUND(?familyName), ?familyName, ?givenName)
                      )
                  ) AS ?formattedName
              )
            }
        - shape: "http://schema.org/EditorShape"
          displayName: "Editor"
          fetchValueFromQuery: |
            # Similar query for editors
        - shape: "http://schema.org/PublisherShape"
          displayName: "Publisher"
          fetchValueFromQuery: |
            # Similar query for publishers
      
    - property: "http://prismstandard.org/namespaces/basic/2.0/publicationDate"
      displayName: "Publication Date"
      shouldBeDisplayed: true
      supportsSearch: true
      
    - property: "http://purl.org/vocab/frbr/core#embodiment"
      displayName: "Page"
      shouldBeDisplayed: true
      fetchValueFromQuery: |
        PREFIX frbr: <http://purl.org/vocab/frbr/core#>
        PREFIX prism: <http://prismstandard.org/namespaces/basic/2.0/>
        SELECT ?pageInfo ?re
        WHERE {
            [[subject]] frbr:embodiment ?re.
            OPTIONAL { ?re prism:startingPage ?startingPage. }
            OPTIONAL { ?re prism:endingPage ?endingPage. }
            BIND(
              IF(BOUND(?startingPage) && BOUND(?endingPage), 
                CONCAT(?startingPage, "-", ?endingPage),
                IF(BOUND(?startingPage), 
                    ?startingPage,
                    IF(BOUND(?endingPage), 
                      ?endingPage,
                      "Unknown page")))
              AS ?pageInfo)
        }
      supportsSearch: false
      
    - property: "http://purl.org/vocab/frbr/core#partOf"
      displayName: "Container"
      fetchValueFromQuery: |
        PREFIX frbr: <http://purl.org/vocab/frbr/core#>
        PREFIX fabio: <http://purl.org/spar/fabio/>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX prism: <http://prismstandard.org/namespaces/basic/2.0/>
        PREFIX datacite: <http://purl.org/spar/datacite/>
        PREFIX literal: <http://www.essepuntato.it/2010/06/literalreification/>
        SELECT ?display ?container
        WHERE {
          # Complex query that finds the most specific container
          # (Issue > Volume > Journal) and formats it for display
        }
      supportsSearch: true
  sortableBy:
    - property: "http://purl.org/dc/terms/title"
      sortOrder: ["asc", "desc"]
    - property: "http://prismstandard.org/namespaces/basic/2.0/publicationDate" 
      sortOrder: ["desc", "asc"]
```

Key configuration elements:

* `class`: The RDF class being configured (e.g., fabio:JournalArticle)
* `priority`: Numeric priority value for this class (lower values take precedence)
* `shouldBeDisplayed`: Whether this class should be shown in the interface
* `displayName`: Human-readable name for the class
* `fetchUriDisplay`: SPARQL query to generate a display string for entities of this class
* `displayProperties`: List of properties to display for this class
  * `property`: The RDF property URI
  * `displayName`: Label shown in the interface
  * `shouldBeDisplayed`: Whether to show the property
  * `inputType`: Type of input field ("text", "textarea", "date", "tag", etc.)
  * `supportsSearch`: Whether this field should enable search functionality
  * `fetchValueFromQuery`: SPARQL query for retrieving and formatting values
  * `intermediateRelation`: For properties that use intermediate nodes (like RoleInTime)
    * `class`: The class of the intermediate node
    * `targetEntityType`: The type of entity to display
  * `displayRules`: For properties with multiple possible values
    * `shape`: The shape (type) of value to display
    * `displayName`: Label for this type of value
    * `fetchValueFromQuery`: SPARQL query specific to this type
  * `orderedBy`: Property used for ordering multiple values (e.g., author order)
* `sortableBy`: Properties that can be used for sorting in the interface
  * `property`: The property to sort by
  * `sortOrder`: Available sort directions (ascending/descending)

> 💡 **Pro Tip**: YAML supports anchors and references to reduce duplication in your configuration file. Since display_rules.yaml can contain many classes with repeated elements, you can define queries and common properties in a single place and reuse them throughout the file:
> 
> ```yaml
> # Define reusable queries at the top
> queries:
>   identifier_query: &identifier_query |
>     PREFIX datacite: <http://purl.org/spar/datacite/>
>     PREFIX literal: <http://www.essepuntato.it/2010/06/literalreification/>
>     SELECT (CONCAT(STRAFTER(STR(?scheme), "http://purl.org/spar/datacite/"), ":", ?literal) AS ?id) ?identifier
>     WHERE {
>         [[subject]] datacite:hasIdentifier ?identifier.
>         ?identifier datacite:usesIdentifierScheme ?scheme;
>                   literal:hasLiteralValue ?literal.
>     }
> 
> # Define common properties
> common_properties:
>   title_property: &title_property
>     property: "http://purl.org/dc/terms/title"
>     displayName: "Title"
>     shouldBeDisplayed: true
>     inputType: "textarea"
>     supportsSearch: true
> 
> # Use references in class definitions
> classes:
>   - class: "http://purl.org/spar/fabio/JournalArticle"
>     displayProperties:
>       - *title_property  # Reference to the common title property
>       - property: "http://purl.org/spar/datacite/hasIdentifier"
>         fetchValueFromQuery: *identifier_query  # Reference to the common query
> ```
> 
> This approach significantly reduces the file size and makes maintenance easier by centralizing common definitions.

## Database Setup

HERITRACE requires two databases: one for the dataset and one for provenance data. You have two options:

1. **Use existing databases**: Configure the endpoints in `config.py`:
   ```python
   DATASET_DB_URL = 'http://localhost:8999/sparql'    # Your dataset endpoint
   PROVENANCE_DB_URL = 'http://localhost:8998/sparql' # Your provenance endpoint
   ```

2. **Start fresh databases using Docker**: 
   - Ensure Docker is installed on your system
   - For Unix/Linux/MacOS, use the provided scripts:
     ```bash
     ./start-databases.sh  # Start the databases
     ./stop-databases.sh   # Stop the databases when done
     ```
   - For Windows, use the PowerShell scripts:
     ```powershell
     .\Start-Databases.ps1  # Start the databases
     .\Stop-Databases.ps1   # Stop the databases when done
     ```
   
   This will start two Virtuoso instances:
   - Dataset database on port 8999
   - Provenance database on port 8998

## Launching the Application

HERITRACE can be launched using Docker Compose:

1. **Development mode**:
   ```bash
   docker compose -f docker-compose.dev.yaml up
   ```

2. **Production mode**:
   ```bash
   docker compose up
   ```

The application will be available at `https://localhost:5000`

## Testing and CI/CD

HERITRACE uses pytest for testing and GitHub Actions for continuous integration.

### Running Tests Locally

To run the tests locally:

1. **Start the test databases**:
   
   The tests require dedicated test databases running on different ports than the main application:
   - Test Dataset database on port 9999
   - Test Provenance database on port 9998

   For Unix/Linux/MacOS:
   ```bash
   # Make the script executable if needed
   chmod +x ./tests/start-test-databases.sh
   
   # Start the test databases
   ./tests/start-test-databases.sh
   ```

   For Windows (PowerShell):
   ```powershell
   # Start the test databases
   .\tests\Start-TestDatabases.ps1
   ```

2. **Run the tests**:
   ```bash
   # Install dependencies including dev dependencies
   poetry install --with dev

   # Run tests
   poetry run pytest

   # Run tests with coverage
   poetry run pytest --cov=heritrace
   ```

3. **Stop the test databases** when done:
   
   For Unix/Linux/MacOS:
   ```bash
   # Make the script executable if needed
   chmod +x ./tests/stop-test-databases.sh
   
   # Stop the test databases
   ./tests/stop-test-databases.sh
   ```

   For Windows (PowerShell):
   ```powershell
   # Stop the test databases
   .\tests\Stop-TestDatabases.ps1
   ```

For more detailed information about testing, including test structure, guidelines, and examples, see [tests/README.md](tests/README.md).

### CI/CD Pipeline

The project is configured with GitHub Actions to automatically run tests on every push to any branch. The CI pipeline:

- Tests against multiple Python versions (3.10, 3.11, 3.12, 3.13)
- Automatically starts and stops the test databases
- Generates test reports and coverage data
- Creates HTML coverage reports
- Uploads coverage reports as artifacts for all branches
- Generates a coverage badge for each branch

For more details on the CI/CD setup, see [CI/CD Setup Documentation](.github/CI_CD_SETUP.md).
