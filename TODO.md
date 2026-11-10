<!--
SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>

SPDX-License-Identifier: ISC
-->

# To do

## Override settings with environment variables

Let an environment variable override a setting stored in the configuration file, so one deployment can change a value without editing the file.

- The configuration editor shows each overridden field as locked and names the variable that sets it.
- The documentation says which source wins.

## Describe the configuration with known vocabularies

The system settings live in SQLite because no vocabulary for them has been chosen. Before moving them back to RDF, look for existing vocabularies that describe the configuration of an application like HERITRACE. Do not define a vocabulary of our own.

## Decide how to delete parts of the configuration

The configuration pages do not offer to delete the configuration, an entity type or a field. Decide what deleting means for each of them: whether removing an entity type also removes its fields, what happens to the data that uses it, and how a deleted part is restored, since the configuration has no recycle bin.

## Remove `display_rules.yaml`

Keep the whole configuration in RDF, in the same document as the shapes. `orderedBy` and `sortableBy` still live in the YAML file. Choose the term that expresses each one.

## Edit RDF lists in the configuration editor

The configuration editor builds its pages from the meta-shapes and cannot edit RDF lists. The duplicate keys of an entity type (`owl:hasKey`) are lists, which means that they can be changed only in `shacl.ttl` by hand. The same holds for `sh:in` and `sh:or`. Let the editor show and change these lists.

## Narrow the link search by container

A search on a link can match too many entities to browse: in OpenCitations Meta, 1,501,210 of the 7,614,242 issues have the number "1". Let users choose the journal first, then the volume, then the issue, with each list limited by the previous choice. The article still stores one `frbr:partOf` link, to the final choice. Decide how the shapes express these steps, since SHACL UI has no term for a field that depends on another.
