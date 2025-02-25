# HERITRACE

HERITRACE (Heritage Enhanced Repository Interface for Tracing, Research, Archival Curation, and Engagement) is a semantic content management system designed for professionals in galleries, libraries, archives, and museums (GLAM).

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
  displayName: "Journal Article"
  displayProperties:
    - property: "http://purl.org/dc/terms/title"
      values:
        - displayName: "Title"
          shouldBeDisplayed: true
          inputType: "text"
          required: true

    - property: "http://purl.org/spar/fabio/hasSubtitle"
      values:
        - displayName: "Subtitle"
          shouldBeDisplayed: true
          inputType: "text"

    - property: "http://purl.org/dc/terms/description"
      values:
        - displayName: "Abstract"
          shouldBeDisplayed: true
          inputType: "textarea"

    - property: "http://purl.org/spar/datacite/hasIdentifier"
      values:
        - displayName: "Identifier"
          shouldBeDisplayed: true
          fetchValueFromQuery: |
            PREFIX datacite: <http://purl.org/spar/datacite/>
            PREFIX literal: <http://www.essepuntato.it/2010/06/literalreification/>
            SELECT (CONCAT(STRAFTER(STR(?scheme), "http://purl.org/spar/datacite/"), ":", ?literal) AS ?id)
            WHERE {
                [[subject]] datacite:hasIdentifier ?identifier.
                ?identifier datacite:usesIdentifierScheme ?scheme;
                          literal:hasLiteralValue ?literal.
            }

    - property: "http://purl.org/spar/pro/isDocumentContextFor"
      orderedBy: "https://w3id.org/oc/ontology/hasNext"
      values:
        - displayName: "Author"
          shouldBeDisplayed: true
          fetchValueFromQuery: |
            PREFIX pro: <http://purl.org/spar/pro/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT DISTINCT ?formattedName ?ra
            WHERE {
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

    - property: "http://prismstandard.org/namespaces/basic/2.0/publicationDate"
      values:
        - displayName: "Publication Date"
          shouldBeDisplayed: true
          inputType: "date"

    - property: "http://purl.org/vocab/frbr/core#partOf"
      values:
        - displayName: "Journal"
          shouldBeDisplayed: true
          fetchValueFromQuery: |
            PREFIX fabio: <http://purl.org/spar/fabio/>
            PREFIX frbr: <http://purl.org/vocab/frbr/core#>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            SELECT ?journalName ?journal
            WHERE {
                [[subject]] frbr:partOf+ ?journal.
                ?journal a fabio:Journal;
                    dcterms:title ?journalName.
            }

        - displayName: "Volume"
          shouldBeDisplayed: true
          fetchValueFromQuery: |
            PREFIX fabio: <http://purl.org/spar/fabio/>
            PREFIX frbr: <http://purl.org/vocab/frbr/core#>
            SELECT ?volumeNumber ?volume
            WHERE {
                [[subject]] frbr:partOf+ ?volume.
                ?volume a fabio:JournalVolume;
                    fabio:hasSequenceIdentifier ?volumeNumber.
            }

        - displayName: "Issue"
          shouldBeDisplayed: true
          fetchValueFromQuery: |
            PREFIX fabio: <http://purl.org/spar/fabio/>
            PREFIX frbr: <http://purl.org/vocab/frbr/core#>
            SELECT ?issueNumber ?issue
            WHERE {
                [[subject]] frbr:partOf ?issue.
                ?issue a fabio:JournalIssue;
                    fabio:hasSequenceIdentifier ?issueNumber.
            }

    - property: "http://purl.org/vocab/frbr/core#embodiment"
      values:
        - displayName: "Page Range"
          shouldBeDisplayed: true
          fetchValueFromQuery: |
            PREFIX frbr: <http://purl.org/vocab/frbr/core#>
            PREFIX prism: <http://prismstandard.org/namespaces/basic/2.0/>
            SELECT 
                (IF(BOUND(?startingPage) && BOUND(?endingPage), 
                    CONCAT(STR(?startingPage), "-", STR(?endingPage)), 
                    IF(BOUND(?startingPage), STR(?startingPage), 
                    IF(BOUND(?endingPage), STR(?endingPage), ""))) AS ?page) 
                ?re
            WHERE {
                [[subject]] frbr:embodiment ?re.
                OPTIONAL { ?re prism:startingPage ?startingPage. }
                OPTIONAL { ?re prism:endingPage ?endingPage. }
            }
```

Key configuration elements:

* `class`: The RDF class being configured (e.g., fabio:JournalArticle)
* `displayName`: Human-readable name for the class
* `displayProperties`: List of properties to display for this class
  * `property`: The RDF property URI
  * `values`: Configuration for how to display/handle the property values
    * `displayName`: Label shown in the interface
    * `shouldBeDisplayed`: Whether to show the property
    * `inputType`: Type of input field ("text", "textarea", "date", etc.)
    * `required`: Whether the property is required
    * `fetchValueFromQuery`: SPARQL query for retrieving values
  * `orderedBy`: Property used for ordering multiple values (e.g., author order)

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
