// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_model.dart';
import 'package:heritrace/form/widgets/similar_entities_notice.dart';

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

  FieldGroup group(String uri) =>
      root.groups.firstWhere((g) => g.def.uri == uri);

  test('an untouched draft has no values', () {
    expect(draftSimilarityValues(root), isEmpty);
  });

  test('a text value carries its datatype', () {
    (group(title).items.single as LiteralItem).setValue('  A title ');

    expect(draftSimilarityValues(root), {
      title: [
        {'value': 'A title', 'datatype': xsdString},
      ],
    });
  });

  NestedItem addIssue() {
    final container = group(partOf).addItem() as OrItem;
    container.select(container.def.or!.first);
    return container.selectedItem! as NestedItem;
  }

  test('a selected entity is sent as a reference', () {
    addIssue().selectExisting('https://example.org/br/1', 'An issue');

    expect(draftSimilarityValues(root), {
      partOf: [
        {'uri': 'https://example.org/br/1'},
      ],
    });
  });

  test('a nested draft is sent through its entered fields', () {
    final numberItem = addIssue().child.groups
        .firstWhere((g) => g.def.uri == sequenceIdentifier)
        .addItem();
    (numberItem as LiteralItem).setValue('4');

    expect(draftSimilarityValues(root), {
      partOf: [
        {
          'fields': [
            {
              'predicate': sequenceIdentifier,
              'value': '4',
              'datatype': xsdString,
            },
          ],
        },
      ],
    });
  });
}
