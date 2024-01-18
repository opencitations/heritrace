# HERITRACE

HERITRACE (Heritage Enhanced Repository Interface for Tracing, Research, Archival Curation, and Engagement) is a semantic content management system designed for professionals in galleries, libraries, archives, and museums (GLAM).

This system facilitates non-technical domain experts in enriching and editing metadata in a semantically robust manner. It is developed with a focus on user-friendliness, provenance management, change tracking, customization, and integration with heterogeneous data sources.

## Configuration

Before using HERITRACE, configure the application by editing the `config.py` file. The configuration settings are as follows:

```python
class Config(object):
    SECRET_KEY = 'aesoiuhaoiuafe'
    DATASET_ENDPOINT = 'http://127.0.0.1:9999/blazegraph/sparql'
    PROVENANCE_ENDPOINT = 'http://127.0.0.1:19999/blazegraph/sparql'
    DATASET_GENERATION_TIME = '2023-09-20T10:23:11+02:00'
    COUNTER_HANDLER = SqliteCounterHandler(os.path.join(BASE_DIR, 'meta_counter_handler.db'))
    LANGUAGES = ['en', 'it']
    BABEL_TRANSLATION_DIRECTORIES = os.path.join(BASE_DIR, 'babel', 'translations')
    CHANGE_TRACKING_CONFIG = os.path.join(BASE_DIR, 'change_tracking.json')
    RESPONSIBLE_AGENT = URIRef('https://orcid.org/0000-0002-8420-0696')
    PRIMARY_SOURCE = None
    SHACL_PATH = os.path.join(BASE_DIR, 'resources', 'shacl.ttl')
    DISPLAY_RULES_PATH = os.path.join(BASE_DIR, 'display_rules.yaml')
```

* SECRET_KEY: A secret key for the application security.
* DATASET_ENDPOINT: SPARQL endpoint URL for the dataset.
* PROVENANCE_ENDPOINT: SPARQL endpoint URL for provenance data.
* DATASET_GENERATION_TIME: Timestamp for dataset generation.
* COUNTER_HANDLER: Handles counters using SQLite. Can be left as default.
* LANGUAGES: Supported languages. Can be left as default.
* BABEL_TRANSLATION_DIRECTORIES: Translation directories for Babel. Can be left as default.
* CHANGE_TRACKING_CONFIG: Path to the change tracking configuration file.
* RESPONSIBLE_AGENT: URIRef for the responsible agent (e.g., a curator's ORCID).
* PRIMARY_SOURCE: Primary source of data, if applicable.
* SHACL_PATH: Path to the SHACL file for data model customization.
* DISPLAY_RULES_PATH: Path to the YAML file for interface customization.

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

The YAML file for display rules allows for presentation customizations of the data model. It defines user-friendly names for classes and properties and specifies how properties should be displayed. This includes configuring SPARQL queries for fetching specific values and setting the order of properties. The provided example demonstrates how different properties of a bibliographic resource, like title, subtitle, and author, are configured for display in the user interface.

```yaml
- class: "http://purl.org/spar/fabio/Expression"
  displayName: "Bibliographic Resource"
  displayProperties:
    - property: "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
      values:
      - displayName: "Type"
        shouldBeDisplayed: true
        fetchValueFromQuery: null
      orderedBy: null
    - property: "http://purl.org/spar/datacite/hasIdentifier"
      values:
      - displayName: "Identifier"
        shouldBeDisplayed: true
        fetchValueFromQuery: |
            PREFIX datacite: <http://purl.org/spar/datacite/>
            PREFIX literal: <http://www.essepuntato.it/2010/06/literalreification/>
            SELECT (CONCAT(STRAFTER(STR(?scheme), "http://purl.org/spar/datacite/"), ":", ?literal) AS ?id) ?identifier
            WHERE {
                [[subject]] datacite:hasIdentifier ?identifier.
                ?identifier datacite:usesIdentifierScheme ?scheme;
                            literal:hasLiteralValue ?literal.
            }
      orderedBy: null
    - property: "http://purl.org/dc/terms/title"
      values:
      - displayName: "Title"
        shouldBeDisplayed: true
        fetchValueFromQuery: null
      orderedBy: null
    - property: "http://purl.org/spar/fabio/hasSubtitle"
      values:
      - displayName: "Subtitle"
        shouldBeDisplayed: true
        fetchValueFromQuery: null
      orderedBy: null
    - property: "http://purl.org/spar/pro/isDocumentContextFor"
      values:
      - displayName: "Author"
        shouldBeDisplayed: true
        fetchValueFromQuery: |
            PREFIX pro: <http://purl.org/spar/pro/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT DISTINCT ?formattedName ?ra WHERE {
                [[value]] pro:isHeldBy ?ra;
                    pro:withRole pro:author.
                OPTIONAL { ?ra foaf:name ?name. }
                OPTIONAL { ?ra foaf:familyName ?familyName. }
                OPTIONAL { ?ra foaf:givenName ?givenName. }
                BIND(
                    IF(BOUND(?name), ?name,
                        IF(BOUND(?familyName) && BOUND(?givenName), CONCAT(?familyName, ", ", ?givenName),
                            IF(BOUND(?familyName), CONCAT(?familyName, ","), 
                                IF(BOUND(?givenName), CONCAT(",", ?givenName), "")
                            )
                        )
                    ) AS ?formattedName
                )
            }
      - displayName: "Publisher"
        shouldBeDisplayed: true
        fetchValueFromQuery: |
            PREFIX pro: <http://purl.org/spar/pro/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT DISTINCT ?formattedName ?ra WHERE {
                [[value]] pro:isHeldBy ?ra;
                    pro:withRole pro:publisher.
                OPTIONAL { ?ra foaf:name ?name. }
                OPTIONAL { ?ra foaf:familyName ?familyName. }
                OPTIONAL { ?ra foaf:givenName ?givenName. }
                BIND(
                    IF(BOUND(?name), ?name,
                        IF(BOUND(?familyName) && BOUND(?givenName), CONCAT(?familyName, ", ", ?givenName),
                            IF(BOUND(?familyName), CONCAT(?familyName, ","), 
                                IF(BOUND(?givenName), CONCAT(",", ?givenName), "")
                            )
                        )
                    ) AS ?formattedName
                )
            }
      - displayName: "Editor"
        shouldBeDisplayed: true
        fetchValueFromQuery: |
            PREFIX pro: <http://purl.org/spar/pro/>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT DISTINCT ?formattedName ?ra WHERE {
                [[value]] pro:isHeldBy ?ra;
                    pro:withRole pro:editor.
                OPTIONAL { ?ra foaf:name ?name. }
                OPTIONAL { ?ra foaf:familyName ?familyName. }
                OPTIONAL { ?ra foaf:givenName ?givenName. }
                BIND(
                    IF(BOUND(?name), ?name,
                        IF(BOUND(?familyName) && BOUND(?givenName), CONCAT(?familyName, ", ", ?givenName),
                            IF(BOUND(?familyName), CONCAT(?familyName, ","), 
                                IF(BOUND(?givenName), CONCAT(",", ?givenName), "")
                            )
                        )
                    ) AS ?formattedName
                )
            }
      orderedBy: "https://w3id.org/oc/ontology/hasNext"
    - property: "http://prismstandard.org/namespaces/basic/2.0/publicationDate"
      values:
      - displayName: "Publication Date"
        shouldBeDisplayed: true
        fetchValueFromQuery: null
      orderedBy: null
    - property: "http://purl.org/vocab/frbr/core#embodiment"
      values:
      - displayName: "Page"
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
      orderedBy: null
    - property: "http://purl.org/vocab/frbr/core#partOf"
      values:
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
      orderedBy: null
    - property: "http://purl.org/vocab/frbr/core#partOf"
      values:
      - displayName: "Volume"
        shouldBeDisplayed: true
        fetchValueFromQuery: |
            PREFIX fabio: <http://purl.org/spar/fabio/>
            PREFIX frbr: <http://purl.org/vocab/frbr/core#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            SELECT ?volumeNumber ?volume
            WHERE {
                [[subject]] frbr:partOf+ ?volume.
                ?volume a fabio:JournalVolume;
                    fabio:hasSequenceIdentifier ?volumeNumber.
            }
      orderedBy: null
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
      orderedBy: null
```

## Launching the Application

To launch HERITRACE, use the following commands depending on your operating system:

On Windows: `python app.py`
On Linux and MacOS: `python3 app.py`

This command starts the Flask application, making HERITRACE accessible for use.
