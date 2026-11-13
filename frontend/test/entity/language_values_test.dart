// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/entity/edit_session.dart';
import 'package:heritrace/entity/entity_models.dart';
import 'package:heritrace/entity/entity_repository.dart';
import 'package:heritrace/form/collector.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_model.dart';
import 'package:heritrace/form/validator.dart';
import 'package:heritrace/form/widgets/language_picker.dart';
import 'package:heritrace/i18n/translations.g.dart';
import 'package:heritrace/navigation/entity_store.dart';

const name = 'http://www.w3.org/ns/shacl#name';
const shape = 'https://example.org/shape';

final fieldJson = {'uri': name, 'withLanguage': true};

const messages = ValidationMessages(
  required: 'required',
  invalidUrl: 'invalid url',
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

EditSession session() => EditSession(
  view: EntityView.fromJson({
    'uri': shape,
    'label': 'Journal',
    'type': 'http://www.w3.org/ns/shacl#NodeShape',
    'type_label': 'Resource type',
    'shape': null,
    'classes': ['http://www.w3.org/ns/shacl#NodeShape'],
    'is_deleted': false,
    'has_history': true,
    'shacl': true,
    'has_form_fields': true,
    'can_be_added': [name],
    'can_be_deleted': [name],
    'datatypes': <String, dynamic>{},
    'optional_values': <String, dynamic>{},
    'groups': [
      {
        'display_name': 'Name',
        'property': name,
        'object_shape': null,
        'is_draggable': false,
        'ordered_by': null,
        'field': fieldJson,
        'triples': [
          {
            'subject': shape,
            'predicate': name,
            'value': 'Rivista',
            'object': 'Rivista',
            'language': 'it',
            'external_entity': null,
            'is_mandatory': false,
            'label': null,
          },
        ],
      },
    ],
  }),
  entityType: 'http://www.w3.org/ns/shacl#NodeShape',
  repository: EntityRepository(Dio(), EntityStore.configuration),
  validationMessages: messages,
  atLeastOnePropertyMessage: 'at least one',
);

void main() {
  setUp(() => LocaleSettings.setLocaleSync(AppLocale.it));

  test(
    'a new value starts in the language of the interface while it is free',
    () {
      final node = EntityNode(
        entityType: shape,
        entityShape: null,
        fields: [FieldDef.fromJson(fieldJson)],
        depth: 0,
      );
      addTearDown(node.dispose);
      final group = node.groups.single;

      final first = group.addItem() as LiteralItem;
      final second = group.addItem() as LiteralItem;
      expect([first.language, second.language], ['it', null]);

      first.setValue('Rivista');
      second
        ..setValue('Revue')
        ..setLanguage('fr');
      expect(collectProperties(node), {
        name: [
          {'value': 'Rivista', 'language': 'it'},
          {'value': 'Revue', 'language': 'fr'},
        ],
      });
    },
  );

  test('a saved value changes language and the update names it', () {
    final edit = session();
    addTearDown(edit.dispose);
    final group = edit.groups.single;
    final saved = group.existing.single;

    final added = group.formGroup!.addItem() as LiteralItem;
    expect(added.language, isNull);
    added.setValue('Journal');

    expect(group.usedLanguages(saved), {null});
    saved.setLanguage('fr');
    expect(group.formGroup!.usedLanguages(except: added), {'fr'});
    saved.setLanguage(null);
    expect(edit.buildChanges(), [
      {
        'action': 'update',
        'subject': shape,
        'predicate': name,
        'shape': null,
        'entity_type': 'http://www.w3.org/ns/shacl#NodeShape',
        'entity_shape': null,
        'object': 'Rivista',
        'newObject': 'Rivista',
        'language': 'it',
        'newLanguage': '',
      },
      {
        'action': 'create',
        'subject': shape,
        'data': {
          'entity_type': 'http://www.w3.org/ns/shacl#NodeShape',
          'properties': {
            name: ['Journal'],
          },
        },
      },
    ]);
  });

  Future<void> openSheet(
    WidgetTester tester, {
    required Set<String?> taken,
    required ValueChanged<String?> onChanged,
  }) async {
    LocaleSettings.setLocaleSync(AppLocale.en);
    await tester.pumpWidget(
      TranslationProvider(
        child: CupertinoApp(
          home: CupertinoPageScaffold(
            child: Center(
              child: SizedBox(
                width: 120,
                child: LanguageButton(
                  language: 'en',
                  taken: taken,
                  onChanged: onChanged,
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('en'));
    await tester.pumpAndSettle();
  }

  testWidgets('the sheet finds a language by name and leaves out taken ones', (
    tester,
  ) async {
    String? chosen = 'en';
    await openSheet(
      tester,
      taken: const {'it'},
      onChanged: (language) => chosen = language,
    );

    expect(find.text('No language'), findsOneWidget);
    await tester.enterText(find.byType(CupertinoSearchTextField), 'ital');
    await tester.pump();
    expect(find.text('Italian'), findsNothing);

    await tester.enterText(find.byType(CupertinoSearchTextField), 'fren');
    await tester.pump();
    expect(find.text('No language'), findsNothing);
    await tester.tap(find.text('French'));
    await tester.pumpAndSettle();
    expect(chosen, 'fr');
  });

  testWidgets('the sheet leaves out no language when another value has none', (
    tester,
  ) async {
    await openSheet(tester, taken: const {null}, onChanged: (_) {});

    expect(find.text('No language'), findsNothing);
    expect(find.text('Abkhazian'), findsOneWidget);
  });
}
