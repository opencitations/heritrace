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

The configuration editor shows the prefixes (`sh:declare`) but not several terms that HERITRACE supports: `sh:or` on fields, on entity types and inside qualified values, `owl:hasKey`, and the label role with `sh:values` and `sh:select`. Many of these terms are RDF lists or blank nodes, which the generic form cannot edit. Decide how the editor shows each term, one term at a time. Points raised so far:

- The form could edit RDF lists and blank nodes directly, choosing the shape of a blank node from the property that links to it, or `shacl-editor.ttl` could hold typed helper resources that HERITRACE translates back into SHACL.
- `owl:hasKey` reads better as "Duplicate criteria", one box per criterion, with the properties of a criterion as plain values, without order or links.
- Removing a value from the configuration has to remove the resources that depend on it, whatever the deletion rules in the system settings say.
- A label query written in the editor has to be checked before it is saved.

## Show configuration errors beside the field they concern

A save can break a rule of the configuration, such as a value to count with neither occurrence count or a maximum lower than the minimum. The editor then shows an English message in a dialog, as in "shapes.8.properties.1.qualifiedMinCount: Add the minimum or maximum occurrences of the value to count". The location points into the internal model of the shapes. A field that several resource types share repeats the message once for each of them. Show each error once, in the language of the interface, beside the field to correct. Points raised so far:

- A rule that the meta-shapes can state, such as the occurrence counts of a value to count, belongs in the form: a resource-level `sh:or` with an `sh:message`, which the form and the server would both honour. The form reads a resource-level `sh:or` only for conditional patterns.
- For the other errors, the server could name the field resource and return a code that the client translates, as the system settings already do with the location of each field.

## Accept literals as fixed and allowed values

SHACL lets `sh:hasValue` and the members of `sh:in` be any RDF term. HERITRACE handles only IRIs: the shapes model turns a literal into an IRI or leaves it out, forms and saves treat the value as a plain string, and the count of qualified values compares IRIs. Support literals, with their datatype or language, wherever `sh:hasValue` and `sh:in` apply: on a field, inside a value to count and among the allowed values. Points raised so far:

- When a form sends a value equal to a literal that the shape declares, the server can restore its datatype and language from the shape, leaving the client unchanged.
- The editor needs a picker for the kind of value, like the one of the property field, declared in the meta-shapes as an `sh:or` of `sh:nodeKind sh:IRI` and some `sh:datatype`. The form would then turn each datatype into an entry of the picker and send the chosen datatype, which the server guesses from the value today.
- The picker can offer a short list (IRI, text, text with language, integer, decimal, boolean, date) or every XSD datatype that HERITRACE validates, as the picker of custom properties does.

## Narrow the link search by container

A search on a link can match too many entities to browse: in OpenCitations Meta, 1,501,210 of the 7,614,242 issues have the number "1". Let users choose the journal first, then the volume, then the issue, with each list limited by the previous choice. The article still stores one `frbr:partOf` link, to the final choice. Decide how the shapes express these steps, since SHACL UI has no term for a field that depends on another.

## Accept the shapes in any RDF format and under any file name

HERITRACE reads the shapes only from a file called `shacl.ttl`, written in Turtle. Let administrators choose the name of the file and write it in any RDF serialization that rdflib reads, such as JSON-LD, RDF/XML or N-Triples. When the app rewrites the file after a change, it keeps the name and the format the administrator chose.

## Choose widgets by score

SHACL 1.2 UI picks the editor and the viewer of each value by score. Every widget gains points from its `shui:WidgetScore` matchers, a `shui:WidgetAcceptMatcher` can rule it out, and the highest score wins. HERITRACE follows a fixed rule: the widget named by `shui:editor` or `shui:viewer`, otherwise an input chosen from the datatype. The value already present plays no part; a tagged value of a property that admits both `xsd:string` and `rdf:langString` therefore opens in a plain text field, where the specification would choose `shui:TextFieldWithLangEditor`. Implement the scoring algorithm with the scores that the specification gives to the widgets HERITRACE supports.

## Show each nested entity shown in place in a box of its own

With `shui:DetailsViewer` or `shui:DetailsEditor`, the values of a field share one box, so the fields of different nested entities run together. Decide whether each nested entity gets a box of its own, on entity pages and in forms.
