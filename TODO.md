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
