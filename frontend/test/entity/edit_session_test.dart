// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/api/api_exception.dart';
import 'package:heritrace/entity/edit_session.dart';
import 'package:heritrace/entity/entity_models.dart';
import 'package:heritrace/entity/entity_repository.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_model.dart';
import 'package:heritrace/form/validator.dart';
import 'package:heritrace/i18n/translations.g.dart';
import 'package:heritrace/navigation/entity_store.dart';

import '../form/fixtures.dart';

const subject = 'https://w3id.org/oc/meta/br/1';

EntityView view() => EntityView.fromJson({
  'uri': subject,
  'label': 'An article',
  'type': article,
  'type_label': 'Journal Article',
  'shape': articleShape,
  'classes': [article],
  'is_deleted': false,
  'has_history': true,
  'shacl': true,
  'has_form_fields': true,
  'can_be_added': [title, documentContext],
  'can_be_deleted': [title, documentContext],
  'datatypes': {
    pubDate: [xsdDate, xsdGYearMonth, xsdGYear],
  },
  'optional_values': <String, dynamic>{},
  'groups': [
    {
      'display_name': 'Title',
      'property': title,
      'object_shape': null,
      'is_draggable': false,
      'ordered_by': null,
      'field': (articleFormFields()[1] as List<dynamic>)[1][0],
      'triples': [
        {
          'subject': subject,
          'predicate': title,
          'value': 'Old title',
          'object': 'Old title',
          'external_entity': null,
          'is_mandatory': false,
          'label': null,
        },
      ],
    },
    {
      'display_name': 'Author',
      'property': documentContext,
      'object_shape': authorShape,
      'is_draggable': true,
      'ordered_by': hasNext,
      'field': (articleFormFields()[3] as List<dynamic>)[1][0],
      'triples': [
        {
          'subject': subject,
          'predicate': documentContext,
          'value': 'Jane Doe',
          'object': 'https://w3id.org/oc/meta/ar/1',
          'external_entity': 'https://w3id.org/oc/meta/ra/1',
          'is_mandatory': false,
          'label': null,
        },
        {
          'subject': subject,
          'predicate': documentContext,
          'value': 'John Roe',
          'object': 'https://w3id.org/oc/meta/ar/2',
          'external_entity': 'https://w3id.org/oc/meta/ra/2',
          'is_mandatory': false,
          'label': null,
        },
      ],
    },
  ],
});

const messages = ValidationMessages(
  required: 'required',
  invalidUrl: 'invalid url',
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

void main() {
  late EditSession session;

  setUp(() {
    session = EditSession(
      view: view(),
      entityType: article,
      repository: EntityRepository(Dio(), EntityStore.dataset),
      validationMessages: messages,
      atLeastOnePropertyMessage: 'at least one',
    );
  });

  tearDown(() => session.dispose());

  EditableGroup group(String uri) =>
      session.groups.firstWhere((g) => g.group.property == uri);

  test('edit mode groups start without new items and without changes', () {
    expect(session.hasChanges, isFalse);
    expect(session.buildChanges(), isEmpty);
    expect(group(documentContext).formGroup!.items, isEmpty);
  });

  test('updates, deletions and reorders become changes', () {
    group(title).existing.single.setValue('New title');
    final authors = group(documentContext);
    authors.move(0, 1);
    authors.existing.first.markForDeletion();

    expect(session.hasChanges, isTrue);
    expect(session.buildChanges(), [
      {
        'action': 'update',
        'subject': subject,
        'predicate': title,
        'shape': null,
        'entity_type': article,
        'entity_shape': articleShape,
        'object': 'Old title',
        'newObject': 'New title',
      },
      {
        'action': 'delete',
        'subject': subject,
        'predicate': documentContext,
        'shape': authorShape,
        'entity_type': article,
        'entity_shape': articleShape,
        'object': 'https://w3id.org/oc/meta/ar/2',
        'newObject': null,
      },
      {
        'action': 'order',
        'subject': subject,
        'predicate': documentContext,
        'shape': authorShape,
        'entity_type': article,
        'entity_shape': articleShape,
        'object': ['https://w3id.org/oc/meta/ar/1'],
        'newObject': hasNext,
      },
    ]);
  });

  test('a required single value is replaced, not removed', () {
    final titles = group(title);
    expect(titles.formGroup!.canAdd, isFalse);

    titles.existing.single.markForDeletion();
    expect(titles.formGroup!.canAdd, isTrue);
    expect(session.validate(), hasLength(1));

    (titles.formGroup!.addItem() as LiteralItem).setValue('Replacement');
    expect(session.validate(), isEmpty);
    expect(session.buildChanges(), [
      {
        'action': 'delete',
        'subject': subject,
        'predicate': title,
        'shape': null,
        'entity_type': article,
        'entity_shape': articleShape,
        'object': 'Old title',
        'newObject': null,
      },
      {
        'action': 'create',
        'subject': subject,
        'data': {
          'entity_type': article,
          'properties': {
            title: ['Replacement'],
          },
        },
      },
    ]);
  });

  test('new nested items produce a create change and extend the order', () {
    final authorItem =
        group(documentContext).formGroup!.addItem() as NestedItem;
    final person = heldByItem(authorItem);
    final nameGroup = person.child.groups.firstWhere((g) => g.def.uri == name);
    (nameGroup.addItem() as LiteralItem).setValue('New Author');

    final changes = session.buildChanges();
    expect(changes.map((c) => c['action']), ['order', 'create']);
    expect(changes.first['object'], [
      'https://w3id.org/oc/meta/ar/1',
      'https://w3id.org/oc/meta/ar/2',
      authorItem.tempId,
    ]);
    final data = changes.last['data'] as Map<String, Object?>;
    expect(data['entity_type'], article);
    final created = (data['properties'] as Map)[documentContext] as List;
    expect((created.single as Map)['tempId'], authorItem.tempId);
  });

  test('a new item left empty stays out of the order', () {
    group(documentContext).formGroup!.addItem();

    expect(session.buildChanges(), isEmpty);
  });

  test('undoing a deletion restores the original state', () {
    final value = group(documentContext).existing.first;
    value.markForDeletion();
    value.undoDeletion();

    expect(session.hasChanges, isFalse);
  });

  test('only deletions of entities are checked for orphans', () {
    expect(
      EditSession.deletionChanges([
        {
          'action': 'delete',
          'subject': subject,
          'predicate': title,
          'object': 'x',
        },
        {
          'action': 'delete',
          'subject': subject,
          'predicate': documentContext,
          'object': 'https://w3id.org/oc/meta/ar/2',
        },
        {'action': 'delete', 'subject': subject},
        {'action': 'update', 'subject': subject, 'object': 'https://a.b/c'},
      ]),
      [
        {
          'action': 'delete',
          'subject': subject,
          'predicate': documentContext,
          'object': 'https://w3id.org/oc/meta/ar/2',
        },
        {'action': 'delete', 'subject': subject},
      ],
    );
  });

  test('removing the field that shows another one deletes its value', () {
    const composite = 'http://datashapes.org/dash#composite';
    const node = 'http://www.w3.org/ns/shacl#node';
    const fieldShape = 'https://example.org/field';
    Map<String, Object?> existingGroup(
      String property,
      Map<String, Object?> field,
      String value,
    ) => {
      'display_name': property,
      'property': property,
      'object_shape': null,
      'is_draggable': false,
      'ordered_by': null,
      'field': {'uri': property, 'max': 1, ...field},
      'triples': [
        {
          'subject': fieldShape,
          'predicate': property,
          'value': value,
          'object': value,
          'external_entity': null,
          'is_mandatory': false,
          'label': null,
        },
      ],
    };
    final fieldSession = EditSession(
      view: EntityView.fromJson({
        'uri': fieldShape,
        'label': 'A field',
        'type': 'http://www.w3.org/ns/shacl#PropertyShape',
        'type_label': 'Field',
        'shape': null,
        'classes': <String>[],
        'is_deleted': false,
        'has_history': true,
        'shacl': true,
        'has_form_fields': true,
        'can_be_added': <String>[],
        'can_be_deleted': [composite, node],
        'datatypes': <String, dynamic>{},
        'optional_values': <String, dynamic>{},
        'groups': [
          existingGroup(composite, {
            'inputType': 'checkbox',
            'shownWith': [node],
          }, 'true'),
          existingGroup(node, {}, 'https://example.org/nested'),
        ],
      }),
      entityType: 'http://www.w3.org/ns/shacl#PropertyShape',
      repository: EntityRepository(Dio(), EntityStore.dataset),
      validationMessages: messages,
      atLeastOnePropertyMessage: 'at least one',
    );
    addTearDown(fieldSession.dispose);

    fieldSession.groups.last.existing.single.markForDeletion();

    expect(
      fieldSession.buildChanges().map(
        (change) => (change['predicate'], change['action'], change['object']),
      ),
      [
        (composite, 'delete', 'true'),
        (node, 'delete', 'https://example.org/nested'),
      ],
    );
  });

  test('a changed saved value is checked against its field and the others', () {
    const scheme = 'http://purl.org/spar/datacite/usesIdentifierScheme';
    const literal =
        'http://www.essepuntato.it/2010/06/literalreification/'
        'hasLiteralValue';
    const doi = 'http://purl.org/spar/datacite/doi';
    const count = 'https://example.org/count';
    const identifier = 'https://w3id.org/oc/meta/id/1';
    Map<String, Object?> savedGroup(
      String property,
      Map<String, Object?> field,
      String value,
    ) => {
      'display_name': property,
      'property': property,
      'object_shape': null,
      'is_draggable': false,
      'ordered_by': null,
      'field': {'uri': property, 'displayName': property, 'max': 1, ...field},
      'triples': [
        {
          'subject': identifier,
          'predicate': property,
          'value': value,
          'object': value,
          'external_entity': null,
          'is_mandatory': false,
          'label': null,
        },
      ],
    };
    final identifierSession = EditSession(
      view: EntityView.fromJson({
        'uri': identifier,
        'label': 'doi:10.1/x',
        'type': 'http://purl.org/spar/datacite/Identifier',
        'type_label': 'Identifier',
        'shape': null,
        'classes': <String>[],
        'is_deleted': false,
        'has_history': true,
        'shacl': true,
        'has_form_fields': true,
        'can_be_added': <String>[],
        'can_be_deleted': <String>[],
        'datatypes': <String, dynamic>{},
        'optional_values': <String, dynamic>{},
        'groups': [
          savedGroup(scheme, {}, doi),
          savedGroup(literal, {
            'patterns': [
              {
                'condition': {'path': scheme, 'value': doi},
                'pattern': r'^10\.',
                'message': 'not a DOI',
              },
            ],
          }, '10.1/x'),
          savedGroup(count, {
            'datatypes': ['http://www.w3.org/2001/XMLSchema#integer'],
            'min': 1,
          }, '1'),
        ],
      }),
      entityType: 'http://purl.org/spar/datacite/Identifier',
      repository: EntityRepository(Dio(), EntityStore.dataset),
      validationMessages: messages,
      atLeastOnePropertyMessage: 'at least one',
    );
    addTearDown(identifierSession.dispose);
    final [_, value, number] = [
      for (final group in identifierSession.groups) group.existing.single,
    ];

    value.setValue('x');
    number.setValue('one');
    expect(
      [
        for (final error in identifierSession.validate())
          (error.message, error.value),
      ],
      [('not a DOI', value), ('whole number', number)],
    );

    number.setValue('');
    expect(
      [
        for (final error in identifierSession.validate())
          (error.message, error.value),
      ],
      [('not a DOI', value), ('required', number)],
    );
  });

  test('lowering a saved maximum flags the saved minimum it falls below', () {
    const minimum = 'http://www.w3.org/ns/shacl#minCount';
    const maximum = 'http://www.w3.org/ns/shacl#maxCount';
    const field = 'https://w3id.org/heritrace/genid/field';
    Map<String, Object?> savedGroup(
      String property,
      Map<String, Object?> definition,
      String value,
    ) => {
      'display_name': property,
      'property': property,
      'object_shape': null,
      'is_draggable': false,
      'ordered_by': null,
      'field': {
        'uri': property,
        'displayName': property,
        'max': 1,
        ...definition,
      },
      'triples': [
        {
          'subject': field,
          'predicate': property,
          'value': value,
          'object': value,
          'external_entity': null,
          'is_mandatory': false,
          'label': null,
        },
      ],
    };
    final fieldSession = EditSession(
      view: EntityView.fromJson({
        'uri': field,
        'label': 'A field',
        'type': 'http://www.w3.org/ns/shacl#PropertyShape',
        'type_label': 'Field',
        'shape': null,
        'classes': <String>[],
        'is_deleted': false,
        'has_history': true,
        'shacl': true,
        'has_form_fields': true,
        'can_be_added': <String>[],
        'can_be_deleted': <String>[],
        'datatypes': <String, dynamic>{},
        'optional_values': <String, dynamic>{},
        'groups': [
          savedGroup(minimum, {
            'lessThanOrEquals': [
              {'path': maximum, 'name': 'Maximum'},
            ],
          }, '2'),
          savedGroup(maximum, {}, '3'),
        ],
      }),
      entityType: 'http://www.w3.org/ns/shacl#PropertyShape',
      repository: EntityRepository(Dio(), EntityStore.configuration),
      validationMessages: messages,
      atLeastOnePropertyMessage: 'at least one',
    );
    addTearDown(fieldSession.dispose);
    final [low, high] = [
      for (final group in fieldSession.groups) group.existing.single,
    ];

    expect(fieldSession.validate(), isEmpty);

    high.setValue('1');
    expect(
      [
        for (final error in fieldSession.validate())
          (error.message, error.value),
      ],
      [('exceeds Maximum', low)],
    );
  });

  test('a rejected save puts each error beside its value or field', () {
    final t = AppLocale.it.buildSync();
    final role = group(documentContext).formGroup!.addItem() as NestedItem;
    final author = heldByItem(role);
    final nameItem =
        author.child.groups.firstWhere((g) => g.def.uri == name).addItem()
              as LiteralItem
          ..setValue('Jane');

    final errors = session.serverErrors(t, [
      const ServerFieldError(
        code: 'exceeds',
        subject: subject,
        predicate: title,
        params: {'other': 'Subtitle', 'input': 'Old title'},
      ),
      ServerFieldError(
        code: 'invalidInput',
        subject: author.tempId,
        predicate: name,
        params: const {'expected': 'IRI', 'input': 'Jane'},
      ),
      const ServerFieldError(
        code: 'fileChanged',
        subject: null,
        predicate: null,
        params: {},
      ),
    ]);

    expect(
      [
        for (final error in errors)
          (error.message, error.path.join(' › '), error.item, error.value),
      ],
      [
        (
          'Il valore non può superare quello di "Subtitle".',
          'Journal Article',
          null,
          group(title).existing.single,
        ),
        (
          'Valore non valido. Atteso IRI.',
          [
            'Journal Article',
            group(documentContext).formGroup!.def.displayName,
            role.child.groups
                .firstWhere((g) => g.def.uri == heldBy)
                .def
                .displayName,
          ].join(' › '),
          nameItem,
          null,
        ),
        (
          'shacl.ttl è cambiato sul disco. Ricarica la pagina per vederne il '
              'contenuto.',
          'Journal Article',
          null,
          null,
        ),
      ],
    );
  });

  test('stopping the edit session resets every group', () async {
    group(title).existing.single.setValue('Changed');
    group(documentContext).formGroup!.addItem();

    await session.stopEditing(release: false);

    expect(session.hasChanges, isFalse);
    expect(group(title).existing.single.newValue, 'Old title');
    expect(group(documentContext).formGroup!.items, isEmpty);
  });
}

String _exceeds(String other) => 'exceeds $other';
