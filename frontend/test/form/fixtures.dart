// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:convert';

import 'package:heritrace/form/field_def.dart';

const article = 'http://purl.org/spar/fabio/JournalArticle';
const articleShape = 'http://schema.org/JournalArticleShape';
const title = 'http://purl.org/dc/terms/title';
const pubDate = 'http://prismstandard.org/namespaces/basic/2.0/publicationDate';
const documentContext = 'http://purl.org/spar/pro/isDocumentContextFor';
const roleInTime = 'http://purl.org/spar/pro/RoleInTime';
const authorShape = 'http://schema.org/AuthorShape';
const withRole = 'http://purl.org/spar/pro/withRole';
const author = 'http://purl.org/spar/pro/author';
const heldBy = 'http://purl.org/spar/pro/isHeldBy';
const agent = 'http://xmlns.com/foaf/0.1/Agent';
const agentShape = 'http://schema.org/ResponsibleAgentShape';
const name = 'http://xmlns.com/foaf/0.1/name';
const hasNext = 'https://w3id.org/oc/ontology/hasNext';
const identifier = 'http://purl.org/spar/datacite/hasIdentifier';
const identifierClass = 'http://purl.org/spar/datacite/Identifier';
const identifierShape = 'http://schema.org/IdentifierShape';
const literalValue =
    'http://www.essepuntato.it/2010/06/literalreification/hasLiteralValue';

/// A trimmed version of `/api/form-fields` for a journal article with its
/// title, publication date, an ordered author list (an intermediate relation
/// to agents) and identifiers.
List<dynamic> articleFormFields() =>
    jsonDecode(jsonEncode(_rawArticleFormFields)) as List<dynamic>;

const List<Object> _rawArticleFormFields = [
  [
    rdfType,
    [
      {
        'uri': rdfType,
        'displayName': 'Type',
        'entityType': article,
        'subjectShape': articleShape,
        'hasValue': article,
        'hasValueLabel': 'Journal Article',
        'min': 1,
        'max': 1,
      },
    ],
  ],
  [
    title,
    [
      {
        'uri': title,
        'displayName': 'Title',
        'entityType': article,
        'subjectShape': articleShape,
        'datatypes': [xsdString],
        'min': 1,
        'max': 1,
        'supportsSearch': true,
        'minCharsForSearch': 4,
      },
    ],
  ],
  [
    pubDate,
    [
      {
        'uri': pubDate,
        'displayName': 'Publication Date',
        'entityType': article,
        'subjectShape': articleShape,
        'datatypes': [xsdDate, xsdGYearMonth, xsdGYear],
        'min': 0,
        'max': 1,
      },
    ],
  ],
  [
    documentContext,
    [
      {
        'uri': documentContext,
        'displayName': 'Author',
        'entityType': article,
        'subjectShape': articleShape,
        'nodeShape': authorShape,
        'objectClass': roleInTime,
        'min': 0,
        'orderedBy': hasNext,
        'intermediateRelation': {
          'class': roleInTime,
          'targetEntityType': agent,
          'targetShape': agentShape,
          'connectingProperty': heldBy,
          'properties': {
            name: [
              {
                'uri': name,
                'displayName': 'Name',
                'entityType': agent,
                'subjectShape': agentShape,
                'datatypes': [xsdString],
                'min': 0,
                'max': 1,
                'supportsSearch': true,
              },
            ],
            identifier: [
              {
                'uri': identifier,
                'displayName': 'Identifier',
                'entityType': agent,
                'subjectShape': agentShape,
                'nodeShape': identifierShape,
                'objectClass': identifierClass,
                'min': 0,
                'nestedShape': [
                  {
                    'uri': literalValue,
                    'displayName': 'Value',
                    'entityType': identifierClass,
                    'subjectShape': identifierShape,
                    'datatypes': [xsdString],
                    'min': 1,
                    'max': 1,
                    'supportsSearch': true,
                    'searchTarget': 'parent',
                  },
                ],
              },
            ],
          },
        },
        'additionalProperties': {withRole: author},
      },
    ],
  ],
];

List<FieldDef> articleFields() => parseFormFields(articleFormFields());
