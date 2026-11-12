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

## Edit the remaining SHACL terms in the configuration editor

The configuration editor shows the prefixes (`sh:declare`) but not several terms that HERITRACE supports: `sh:hasValue`, `sh:qualifiedValueShape` with its counts, `sh:in`, `sh:or` on fields and on entity types, `owl:hasKey`, `sh:inversePath`, and the label role with `sh:values` and `sh:select`. As a result, two fields with the same path look identical, such as the two `rdf:type` fields of an entity type that differ only in their fixed value. Many of these terms are RDF lists or blank nodes, which the generic form cannot edit. Decide how the editor shows each term, one term at a time. Points raised so far:

- The form could edit RDF lists and blank nodes directly, choosing the shape of a blank node from the property that links to it, or `shacl-editor.ttl` could hold typed helper resources that HERITRACE translates back into SHACL.
- `owl:hasKey` reads better as "Duplicate criteria", one box per criterion, with the properties of a criterion as plain values, without order or links.
- Removing a value from the configuration has to remove the resources that depend on it, whatever the deletion rules in the system settings say.
- A label query written in the editor has to be checked before it is saved.

## Narrow the link search by container

A search on a link can match too many entities to browse: in OpenCitations Meta, 1,501,210 of the 7,614,242 issues have the number "1". Let users choose the journal first, then the volume, then the issue, with each list limited by the previous choice. The article still stores one `frbr:partOf` link, to the final choice. Decide how the shapes express these steps, since SHACL UI has no term for a field that depends on another.

## Show names and descriptions in the language of the interface

A shape can give `sh:name` and `sh:description` in several languages, but HERITRACE shows the first one in the file, whatever language the user has chosen. The frontend does not tell the backend which language is active. Let HERITRACE pick names and descriptions in the language of the interface, on entity pages, in forms and in the configuration editor.

## Accept the shapes in any RDF format and under any file name

HERITRACE reads the shapes only from a file called `shacl.ttl`, written in Turtle. Let administrators choose the name of the file and write it in any RDF serialization that rdflib reads, such as JSON-LD, RDF/XML or N-Triples. When the app rewrites the file after a change, it keeps the name and the format the administrator chose.

## Keep the order of values created inside a new nested entity

When a form creates a nested entity together with its values, the values of an ordered property get no position: neither an `sh:order` index nor an `ht:orderedBy` chain. This holds in the dataset and in the configuration editor. Give these values their position as for values created at the first level.

## Show each nested entity shown in place in a box of its own

With `shui:DetailsViewer` or `shui:DetailsEditor`, the values of a field share one box, so the fields of different nested entities run together. Decide whether each nested entity gets a box of its own, on entity pages and in forms.
