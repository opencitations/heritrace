# HERITRACE Testing Materials

## Overview

Testing versions of HERITRACE's SHACL schema and display rules for controlled user testing using "backward testing" - technicians add back missing properties to a simplified system.

## Files

### `test_shacl.ttl`
Basic SHACL schema with:
- Journal Articles (`fabio:JournalArticle`) - basic properties only
- Journals (`fabio:Journal`) - title and identifiers only  
- Authors (`foaf:Agent`) - basic name information
- Identifiers (`datacite:Identifier`) - DOI and ISSN support only

**Missing properties** (technicians add): `dcterms:abstract`, `prism:keyword`, `frbr:embodiment`, `dcterms:description`

### `test_display_rules.yaml`
Basic display configuration missing abstract, keyword, and page displays.

### `test_data.nq.gz`
Sample articles and journals with missing properties for testing.

- **`test_data.nq.gz`**: Compressed N-Quads format used by the testing infrastructure with Virtuoso Utilities bulk loader for optimal performance

The infrastructure automatically uses `test_data.nq.gz` for data loading via Virtuoso Utilities bulk loader.

## Testing Tasks

1. **Add Abstract Support** (20 min) - Add `dcterms:abstract` property and validation
2. **Add Keywords Support** (15 min) - Add `prism:keyword` property for multiple keywords  
3. **Add Display Rules** (20 min) - Configure abstract and keyword display
4. **Add Page Information** (5 min) - Add `frbr:embodiment` support

## Advantages

- **Controlled outcomes** - known correct solutions exist
- **Realistic scenarios** - based on actual HERITRACE features
- **Incremental complexity** - tasks build logically
- **Immediate testing** - technicians see results of changes
- **Optimized data loading** - N-Quads format with Virtuoso Utilities bulk loader

## Usage

1. **Setup** test HERITRACE instance with these materials using Virtuoso Utilities
2. **Automatic loading** of test_data.nq.gz via bulk loader during environment startup
3. **Guide** technicians through sequential tasks
4. **Compare** solutions against reference implementations
5. **Evaluate** syntax, functionality, and completeness

## Expected Solutions

```turtle
# Abstract property
sh:property [
    sh:path dcterms:abstract ;
    sh:datatype xsd:string ;
    sh:minCount 0 ;
    sh:maxCount 1 ;
] ;
```

```yaml
# Display rule
abstract_property:
  property: "http://purl.org/dc/terms/abstract"
  displayName: "Abstract"
  inputType: "textarea"
  supportsSearch: true
```

Integrates with main technician testing protocol (`../02_technician_testing.md`) and infrastructure (`../infrastructure/`). 