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

  test('a selected entity is sent as a reference', () {
    final item = group(documentContext).addItem() as NestedItem;
    item.selectExisting('https://example.org/ra/1', 'A person');

    expect(draftSimilarityValues(root), {
      documentContext: [
        {'uri': 'https://example.org/ra/1'},
      ],
    });
  });

  test('a nested draft is sent through its entered fields', () {
    final item = group(documentContext).addItem() as NestedItem;
    final nameItem = item.child.groups
        .firstWhere((g) => g.def.uri == name)
        .addItem();
    (nameItem as LiteralItem).setValue('Ada');

    expect(draftSimilarityValues(root), {
      documentContext: [
        {
          'fields': [
            {'predicate': name, 'value': 'Ada', 'datatype': xsdString},
          ],
        },
      ],
    });
  });
}
