// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/entity/edit_session.dart';
import 'package:heritrace/entity/entity_models.dart';
import 'package:heritrace/entity/existing_value_widgets.dart';

import '../helpers.dart';

const field = 'https://w3id.org/heritrace/genid/field';
const path = 'http://www.w3.org/ns/shacl#path';
const inversePath = 'https://w3id.org/heritrace/genid/path';

void main() {
  testWidgets('a value matching an alternative is named above its details', (
    tester,
  ) async {
    final view = EntityView.fromJson({
      'uri': field,
      'label': 'Issues',
      'type': 'http://www.w3.org/ns/shacl#PropertyShape',
      'type_label': 'Field',
      'shape': null,
      'classes': ['http://www.w3.org/ns/shacl#PropertyShape'],
      'is_deleted': false,
      'has_history': true,
      'shacl': true,
      'has_form_fields': true,
      'can_be_added': <String>[],
      'can_be_deleted': <String>[],
      'datatypes': <String, dynamic>{},
      'optional_values': <String, dynamic>{},
      'groups': [
        {
          'display_name': 'Property',
          'property': path,
          'object_shape': null,
          'is_draggable': false,
          'ordered_by': null,
          'field': null,
          'triples': [
            {
              'subject': field,
              'predicate': path,
              'value': '^frbr:partOf',
              'object': inversePath,
              'language': null,
              'external_entity': inversePath,
              'is_mandatory': false,
              'label': null,
              'alternative': 'Inverse path',
              'details': [
                {
                  'name': 'Property',
                  'values': [
                    {'label': 'Part of', 'uri': null},
                  ],
                },
              ],
            },
          ],
        },
      ],
    });
    final group = view.groups.single;
    final value = ExistingValue(triple: group.triples.single, group: group);
    addTearDown(value.dispose);

    await pumpApp(
      tester,
      child: CupertinoApp(
        home: ExistingValueWidget(
          value: value,
          view: view,
          editing: false,
          takenLanguages: const {},
        ),
      ),
    );

    expect(find.text('Inverse path'), findsOneWidget);
    expect(find.text('Part of'), findsOneWidget);
    expect(find.text('Property'), findsNothing);
  });
}
