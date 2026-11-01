// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/form/collector.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_model.dart';

import 'fixtures.dart';

void main() {
  late EntityNode root;

  setUp(() {
    root = EntityNode(
      entityType: article,
      entityShape: articleShape,
      fields: articleFields(),
      depth: 0,
    );
  });

  tearDown(() => root.dispose());

  FieldGroup group(EntityNode node, String uri) =>
      node.groups.firstWhere((g) => g.def.uri == uri);

  test('required groups start with their minimum number of items', () {
    expect(group(root, rdfType).items, hasLength(1));
    expect(group(root, title).items, hasLength(1));
    expect(group(root, pubDate).items, isEmpty);
    expect(group(root, documentContext).items, isEmpty);
  });

  test('empty forms produce only the mandatory value', () {
    expect(collectProperties(root), {
      rdfType: [article],
    });
  });

  test('literals, dates and nested intermediate entities are collected', () {
    (group(root, title).items.single as LiteralItem).setValue('A title');
    final date = group(root, pubDate).addItem() as DateItem;
    date.setValue('2023-05-01');
    date.setDateType(DateType.year);

    final authorItem = group(root, documentContext).addItem() as NestedItem;
    expect(authorItem.tempId, 'temp-1');
    final nameGroup = group(authorItem.child, name);
    (nameGroup.addItem() as LiteralItem).setValue('Jane Doe');
    final identifierItem =
        group(authorItem.child, identifier).addItem() as NestedItem;
    (group(identifierItem.child, literalValue).items.single as LiteralItem)
        .setValue('0000-0001-2345-6789');

    expect(collectProperties(root), {
      rdfType: [article],
      title: ['A title'],
      pubDate: ['2023'],
      documentContext: [
        {
          'entity_type': roleInTime,
          'entity_shape': authorShape,
          'properties': {
            heldBy: {
              'entity_type': agent,
              'entity_shape': agentShape,
              'properties': {
                name: ['Jane Doe'],
                identifier: [
                  {
                    'entity_type': identifierClass,
                    'entity_shape': identifierShape,
                    'properties': {
                      literalValue: ['0000-0001-2345-6789'],
                    },
                  },
                ],
              },
            },
            withRole: author,
          },
          'targetEntityType': agent,
          'targetShape': agentShape,
          'orderedBy': hasNext,
          'tempId': 'temp-1',
        },
      ],
    });
  });

  test('untouched nested entities are skipped', () {
    group(root, documentContext).addItem();

    expect(collectProperties(root), {
      rdfType: [article],
    });
  });

  test('an existing entity replaces the nested form', () {
    final authorItem = group(root, documentContext).addItem() as NestedItem;
    authorItem.selectExisting('https://w3id.org/oc/meta/ra/1', 'Jane Doe');

    final collected = collectProperties(root)[documentContext]!.single;
    expect(collected, {
      'entity_type': roleInTime,
      'entity_shape': authorShape,
      'properties': {
        heldBy: [
          {
            'is_existing_entity': true,
            'entity_uri': 'https://w3id.org/oc/meta/ra/1',
          },
        ],
        withRole: author,
      },
      'targetEntityType': agent,
      'targetShape': agentShape,
      'orderedBy': hasNext,
      'tempId': authorItem.tempId,
    });
  });

  test('editing the nested form discards the selected entity', () {
    final authorItem = group(root, documentContext).addItem() as NestedItem;
    final nameItem = group(authorItem.child, name).addItem() as LiteralItem;
    nameItem.setValue('Jane');
    authorItem.selectExisting('https://w3id.org/oc/meta/ra/1', 'Jane Doe');

    nameItem.setValue('Jane Roe');

    expect(authorItem.isExisting, false);
    final collected =
        collectProperties(root)[documentContext]!.single
            as Map<String, Object?>;
    expect((collected['properties']! as Map)[heldBy], {
      'entity_type': agent,
      'entity_shape': agentShape,
      'properties': {
        name: ['Jane Roe'],
      },
    });
  });

  test('a draft label inside the nested form keeps the selected entity', () {
    final authorItem = group(root, documentContext).addItem() as NestedItem;
    final identifierItem =
        group(authorItem.child, identifier).addItem() as NestedItem;
    authorItem.selectExisting('https://w3id.org/oc/meta/ra/1', 'Jane Doe');

    identifierItem.draftLabel.value = (label: 'ORCID', failed: false);

    expect(authorItem.isExisting, true);
  });

  test('the draft entity mirrors the collected nested value', () {
    final authorItem = group(root, documentContext).addItem() as NestedItem;
    (group(authorItem.child, name).addItem() as LiteralItem).setValue('Jane');

    expect(
      draftEntity(authorItem),
      collectProperties(root)[documentContext]!.single,
    );
  });

  test('custom properties build the creation payload without SHACL', () {
    final properties = [
      CustomProperty()..update(
        predicate: rdfType,
        value: 'http://example.org/Thing',
        type: 'uri',
      ),
      CustomProperty()..update(
        predicate: 'http://example.org/label',
        value: 'A label',
        type: 'literal',
        datatype: xsdString,
      ),
      CustomProperty()..update(predicate: 'http://example.org/empty'),
    ];

    expect(customCreationPayload(properties), {
      'entity_type': 'http://example.org/Thing',
      'properties': {
        'http://example.org/label': [
          {
            'is_custom_property': true,
            'value': 'A label',
            'type': 'literal',
            'datatype': xsdString,
          },
        ],
      },
    });
    expect(customCreationPayload(properties.sublist(1)), {
      'entity_type': owlThing,
      'properties': {
        'http://example.org/label': [
          {
            'is_custom_property': true,
            'value': 'A label',
            'type': 'literal',
            'datatype': xsdString,
          },
        ],
      },
    });
  });

  test('date conversion keeps the date meaningful across types', () {
    expect(convertDate('2023', DateType.date), '2023-01-01');
    expect(convertDate('2023-05', DateType.date), '2023-05-01');
    expect(convertDate('2023-05-17', DateType.month), '2023-05');
    expect(convertDate('2023-05-17', DateType.year), '2023');
    expect(convertDate('not a date', DateType.year), 'not a date');
  });
}
