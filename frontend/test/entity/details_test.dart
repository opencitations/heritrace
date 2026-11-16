// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/design/controls.dart';
import 'package:heritrace/entity/edit_session.dart';
import 'package:heritrace/entity/entity_models.dart';
import 'package:heritrace/entity/entity_repository.dart';
import 'package:heritrace/entity/existing_value_widgets.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_scope.dart';
import 'package:heritrace/form/validator.dart';
import 'package:heritrace/navigation/entity_store.dart';

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
                  'property': 'http://www.w3.org/ns/shacl#inversePath',
                  'values': [
                    {
                      'label': 'Part of',
                      'uri': null,
                      'value': 'http://purl.org/vocab/frbr/core#partOf',
                      'language': null,
                    },
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

  testWidgets('a value shown in place is edited in place', (tester) async {
    const values = 'http://www.w3.org/ns/shacl#values';
    const select = 'http://www.w3.org/ns/shacl#select';
    const query = 'https://w3id.org/heritrace/genid/query';
    const queryType = 'https://w3id.org/heritrace#SelectExpression';
    const queryShape = 'https://w3id.org/heritrace/meta/SelectExpressionShape';
    final view = EntityView.fromJson({
      'uri': field,
      'label': 'Display label',
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
          'display_name': 'Label query',
          'property': values,
          'object_shape': queryShape,
          'is_draggable': false,
          'ordered_by': null,
          'field': {
            'uri': values,
            'displayName': 'Label query',
            'editor': resourceDialogEditor,
            'nodeShape': queryShape,
            'nestedShape': [
              {
                'uri': select,
                'displayName': 'SPARQL query',
                'entityType': queryType,
                'subjectShape': queryShape,
                'editor': shuiTextAreaEditor,
              },
            ],
          },
          'triples': [
            {
              'subject': field,
              'predicate': values,
              'value': query,
              'object': query,
              'language': null,
              'external_entity': query,
              'is_mandatory': false,
              'label': null,
              'alternative': null,
              'details_shape': queryShape,
              'details': [
                {
                  'name': 'SPARQL query',
                  'property': select,
                  'values': [
                    {
                      'label': 'SELECT ?a WHERE {}',
                      'uri': null,
                      'value': 'SELECT ?a WHERE {}',
                      'language': null,
                    },
                  ],
                },
              ],
            },
          ],
        },
      ],
    });
    final session = EditSession(
      view: view,
      entityType: 'http://www.w3.org/ns/shacl#PropertyShape',
      repository: EntityRepository(Dio(), EntityStore.configuration),
      validationMessages: _messages,
      atLeastOnePropertyMessage: 'at least one',
    );
    addTearDown(session.dispose);
    final scope = FormScopeController(rootLabel: 'Field');
    addTearDown(scope.dispose);

    await pumpApp(
      tester,
      child: CupertinoApp(
        home: CupertinoPageScaffold(
          child: FormScope(
            notifier: scope,
            child: ExistingValueWidget(
              value: session.groups.single.existing.single,
              view: view,
              editing: true,
              takenLanguages: const {},
            ),
          ),
        ),
      ),
    );
    await tester.enterText(
      find.byType(CupertinoTextField),
      'SELECT ?b WHERE {}',
    );

    expect(session.buildChanges(), [
      {
        'action': 'update',
        'subject': query,
        'predicate': select,
        'entity_type': queryType,
        'entity_shape': queryShape,
        'object': 'SELECT ?a WHERE {}',
        'newObject': 'SELECT ?b WHERE {}',
      },
    ]);

    final edit =
        session.groups.single.existing.single.detailEdits.values.single;
    scope.setErrors([
      ValidationError(
        message: 'Not a query',
        path: const ['Field'],
        value: edit,
      ),
    ]);
    await tester.pump();

    expect(find.text('Not a query'), findsOneWidget);
  });

  testWidgets('a value chosen from a list shows the error beside it', (
    tester,
  ) async {
    const editor = 'http://www.w3.org/ns/shacl#editor';
    const textArea = 'http://datashapes.org/dash#TextAreaEditor';
    final view = EntityView.fromJson({
      'uri': field,
      'label': 'Abstract',
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
      'optional_values': {
        editor: [
          {'value': textArea, 'label': 'Text area'},
        ],
      },
      'groups': [
        {
          'display_name': 'Editor',
          'property': editor,
          'object_shape': null,
          'is_draggable': false,
          'ordered_by': null,
          'field': null,
          'triples': [
            {
              'subject': field,
              'predicate': editor,
              'value': textArea,
              'object': textArea,
              'language': null,
              'external_entity': null,
              'is_mandatory': false,
              'label': 'Text area',
              'alternative': null,
            },
          ],
        },
      ],
    });
    final group = view.groups.single;
    final value = ExistingValue(triple: group.triples.single, group: group);
    addTearDown(value.dispose);
    final scope = FormScopeController(rootLabel: 'Field');
    addTearDown(scope.dispose);

    await pumpApp(
      tester,
      child: CupertinoApp(
        home: CupertinoPageScaffold(
          child: FormScope(
            notifier: scope,
            child: ExistingValueWidget(
              value: value,
              view: view,
              editing: true,
              takenLanguages: const {},
            ),
          ),
        ),
      ),
    );
    scope.setErrors([
      ValidationError(
        message: 'Not an editor',
        path: const ['Field'],
        value: value,
      ),
    ]);
    await tester.pump();

    expect(find.text('Not an editor'), findsOneWidget);
  });

  testWidgets('a value shown in place gains and loses values of a field', (
    tester,
  ) async {
    const counted = 'http://www.w3.org/ns/shacl#qualifiedValueShape';
    const hasValue = 'http://www.w3.org/ns/shacl#hasValue';
    const condition = 'https://w3id.org/heritrace/genid/condition';
    const conditionType = 'https://w3id.org/heritrace#QualifiedValueShape';
    const conditionShape =
        'https://w3id.org/heritrace/meta/QualifiedValueShapeShape';
    const fabio = 'http://purl.org/spar/fabio/';
    Map<String, Object?> detailValue(String name) => {
      'label': 'fabio:$name',
      'uri': null,
      'value': '$fabio$name',
      'language': null,
    };
    final view = EntityView.fromJson({
      'uri': field,
      'label': 'Type',
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
          'display_name': 'Values to count',
          'property': counted,
          'object_shape': conditionShape,
          'is_draggable': false,
          'ordered_by': null,
          'field': {
            'uri': counted,
            'displayName': 'Values to count',
            'editor': resourceDialogEditor,
            'nodeShape': conditionShape,
            'max': 1,
            'nestedShape': [
              {
                'uri': hasValue,
                'displayName': 'Values',
                'editor': textFieldEditor,
                'entityType': conditionType,
                'subjectShape': conditionShape,
                'min': 1,
              },
            ],
          },
          'triples': [
            {
              'subject': field,
              'predicate': counted,
              'value': 'fabio:Book, fabio:Thesis',
              'object': condition,
              'language': null,
              'external_entity': condition,
              'is_mandatory': false,
              'label': null,
              'alternative': null,
              'details_shape': conditionShape,
              'details': [
                {
                  'name': 'Values',
                  'property': hasValue,
                  'values': [detailValue('Book'), detailValue('Thesis')],
                },
              ],
            },
          ],
        },
      ],
    });
    final session = EditSession(
      view: view,
      entityType: 'http://www.w3.org/ns/shacl#PropertyShape',
      repository: EntityRepository(Dio(), EntityStore.configuration),
      validationMessages: _messages,
      atLeastOnePropertyMessage: 'at least one',
    );
    addTearDown(session.dispose);

    await pumpApp(
      tester,
      child: CupertinoApp(
        home: CupertinoPageScaffold(
          child: FormScope(
            notifier: FormScopeController(rootLabel: 'Type'),
            child: ExistingValueWidget(
              value: session.groups.single.existing.single,
              view: view,
              editing: true,
              takenLanguages: const {},
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.byType(RemoveButton).first);
    await tester.pump();

    expect(find.byType(RemoveButton), findsNothing);

    await tester.tap(find.text('Add Values'));
    await tester.pump();
    await tester.enterText(
      find.byType(CupertinoTextField).last,
      '${fabio}Journal',
    );

    expect(find.text('fabio:Book'), findsOneWidget);
    expect(session.buildChanges(), [
      {
        'action': 'delete',
        'subject': condition,
        'predicate': hasValue,
        'entity_type': conditionType,
        'entity_shape': conditionShape,
        'object': '${fabio}Book',
        'newObject': null,
      },
      {
        'action': 'create',
        'subject': condition,
        'data': {
          'entity_type': conditionType,
          'properties': {
            hasValue: ['${fabio}Journal'],
          },
        },
      },
    ]);
  });
}

const _messages = ValidationMessages(
  required: '',
  invalidUrl: '',
  invalidIri: 'invalid iri',
  exceeds: _exceeds,
  invalidInput: _echo,
  tooMany: _ignore,
  tooFew: _ignore,
  atLeast: _ignoreBound,
  atMost: _ignoreBound,
  greaterThan: _ignoreBound,
  lessThan: _ignoreBound,
);

String _ignoreBound(num bound) => '';

String _echo(String expected) => expected;

String _ignore(String name, int count, int limit) => '';

String _exceeds(String other) => 'exceeds $other';
