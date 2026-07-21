<!--
SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>

SPDX-License-Identifier: ISC
-->

# Ask the Curator: ISWC 2026 demo

This package reproduces the curation walkthrough described in the demo paper
“Ask the Curator: Supporting Expert Judgment in RDF Data Curation with
HERITRACE.” It builds HERITRACE from the enclosing checkout and starts separate
Virtuoso stores for the dataset and its provenance.

The initial graph reconstructs three source descriptions of two articles. Its
retained Nilsson resource uses the current OpenCitations Meta identifier
`omid:br/06601213255`. OpenCitations Meta currently returns that resource for
both PMID `15370649` and PMID `15849057`, although its bibliographic fields
describe the Nilsson article. The package does not modify the public dataset.

## Start the environment

Docker with Docker Compose is required. From this directory, run:

```bash
docker compose up --build
```

After the services become healthy, open <http://localhost:5000>. Demo mode logs
the user in automatically. Select **Journal Article** in the catalogue and open
the Nilsson entity whose URI is:

```text
https://w3id.org/oc/meta/br/06601213255
```

To discard all curation operations and reload the initial graph, stop the
environment and remove only this Compose project's volumes:

```bash
docker compose down -v
docker compose up --build
```

## Walkthrough

1. Open the retained Nilsson entity. The similar-resources panel lists the
   PubMed Nilsson description and the PubMed Maltezou description.
2. Merge `https://w3id.org/oc/meta/demo/br/pubmed-15849057` into the retained
   entity. Accept the configured PubMed ESummary response as the primary source.
3. Merge `https://w3id.org/oc/meta/demo/br/pubmed-15370649` into the retained
   entity without consulting the external records.
4. Open the retained entity's Time Machine and restore the snapshot immediately
   preceding the Maltezou merge.
5. Compare the evidence from
   [Crossref](https://api.crossref.org/works/10.1080%2F00365540410020884) and the
   [publisher](https://www.tandfonline.com/doi/10.1080/00365540410020884) with
   [PubMed PMID 15370649](https://pubmed.ncbi.nlm.nih.gov/15370649/) and
   [PubMed PMID 15849057](https://pubmed.ncbi.nlm.nih.gov/15849057/).
6. Open the restored Maltezou entity, edit it, and unlink
   `doi:10.1080/00365540410020884`. Use the Crossref response as the primary
   source for the correction.
7. Inspect the Maltezou entity's Time Machine. It records the removal of the DOI
   link while retaining PMID `15370649`.

The final graph contains one Nilsson article with the DOI and PMID `15849057`,
and one Maltezou article with PMID `15370649` alone.

## Screenshot checkpoints

Capture the following interface states for the two composite figures in the
paper:

- retained Nilsson entity with both duplicate suggestions;
- comparison between the retained and PubMed Nilsson descriptions;
- Time Machine entry for the Maltezou merge with the restore control;
- Maltezou edit form while the shared DOI is unlinked;
- Time Machine entry and provenance for the DOI correction.

## Data sources

- [OpenCitations Meta record for the conflated entity](https://api.opencitations.net/meta/v1/metadata/omid:br/06601213255)
- [Combined PubMed ESummary response](https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=15370649,15849057&retmode=json)
- [Crossref DOI record](https://api.crossref.org/works/10.1080%2F00365540410020884)
- [Publisher article page](https://www.tandfonline.com/doi/10.1080/00365540410020884)
