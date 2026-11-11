// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_model.dart';
import 'package:heritrace/form/form_scope.dart';
import 'package:heritrace/design/controls.dart';
import 'package:heritrace/form/widgets/entity_autocomplete.dart';
import 'package:heritrace/form/widgets/entity_form.dart';
import 'package:heritrace/form/widgets/field_group_widget.dart';
import 'package:heritrace/form/widgets/item_widgets.dart';
import 'package:heritrace/i18n/translations.g.dart';

import 'fixtures.dart';

Future<void> pumpGroup(WidgetTester tester, FieldGroup group) =>
    pumpInForm(tester, FieldGroupWidget(group: group));

Future<void> pumpInForm(WidgetTester tester, Widget child) async {
  LocaleSettings.setLocale(AppLocale.en);
  tester.view.physicalSize = const Size(1280, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    TranslationProvider(
      child: ProviderScope(
        child: CupertinoApp(
          home: CupertinoPageScaffold(
            child: FormScope(
              notifier: FormScopeController(rootLabel: 'Journal Article'),
              child: SingleChildScrollView(child: child),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pump();
}

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

  testWidgets('a required single value has neither add nor delete actions', (
    tester,
  ) async {
    await pumpGroup(tester, group(title));

    expect(find.text('Add Title'), findsNothing);
    expect(find.byType(RemoveButton), findsNothing);
    expect(find.byType(CupertinoTextField), findsOneWidget);

    await tester.enterText(find.byType(CupertinoTextField), 'A new title');
    expect((group(title).items.single as LiteralItem).value, 'A new title');
  });

  testWidgets('an optional single value can be added once and removed', (
    tester,
  ) async {
    await pumpGroup(tester, group(pubDate));

    expect(find.text('Add Publication Date'), findsOneWidget);
    await tester.tap(find.text('Add Publication Date'));
    await tester.pump();

    expect(find.text('Add Publication Date'), findsNothing);
    expect(find.byType(RemoveButton), findsOneWidget);
    expect(find.byType(DateTypeMenu), findsOneWidget);

    await tester.tap(find.byType(RemoveButton));
    await tester.pump();

    expect(group(pubDate).items, isEmpty);
    expect(find.text('Add Publication Date'), findsOneWidget);
  });

  testWidgets('cancelling a new nested entity discards it', (tester) async {
    final role = group(documentContext).addItem() as NestedItem;
    final person = heldByItem(role);
    final identifiers = person.child.groups.firstWhere(
      (g) => g.def.uri == identifier,
    );
    await pumpGroup(tester, identifiers);

    await tester.tap(find.text('Add Identifier'));
    await tester.pumpAndSettle();
    expect(identifiers.items, hasLength(1));

    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(identifiers.items, isEmpty);
  });

  testWidgets('a details editor shows the nested fields in place', (
    tester,
  ) async {
    await pumpGroup(tester, group(documentContext));

    await tester.tap(find.text('Add Author'));
    await tester.pumpAndSettle();

    expect(find.byType(NestedTile), findsNothing);
    expect(find.text('Role'), findsOneWidget);
    expect(find.byType(EntityAutocompleteField), findsOneWidget);
  });

  testWidgets('a single declared field is edited without a heading', (
    tester,
  ) async {
    final roleJson =
        ((articleFormFields().firstWhere(
                      (entry) =>
                          (entry as List<dynamic>).first == documentContext,
                    ) as List<dynamic>)[1]
                    as List<dynamic>)
                .first
            as Map<String, dynamic>;
    final role = createItem(
      FieldDef.fromJson({
        ...roleJson,
        'detailPaths': [heldBy],
      }),
      0,
      group(documentContext),
    ) as NestedItem;
    addTearDown(role.dispose);

    await pumpInForm(tester, NestedFields(item: role));
    await tester.pumpAndSettle();

    expect(find.text('Role'), findsNothing);
    expect(find.byType(EntityAutocompleteField), findsOneWidget);
  });

  testWidgets('a field shows its description under it', (tester) async {
    await pumpInForm(tester, EntityForm(node: root));

    expect(find.text('The title as printed on the article.'), findsOneWidget);
  });

  testWidgets(
    'a field with shownWith appears once a listed field has a value',
    (tester) async {
      const node = 'http://www.w3.org/ns/shacl#node';
      final field = EntityNode(
        entityType: 'http://www.w3.org/ns/shacl#PropertyShape',
        entityShape: null,
        fields: [
          FieldDef.fromJson({
            'uri': 'http://datashapes.org/dash#composite',
            'displayName': 'Part of the entity',
            'inputType': 'checkbox',
            'max': 1,
            'shownWith': [node],
          }),
          FieldDef.fromJson({
            'uri': node,
            'displayName': 'Nested resource type',
            'min': 1,
            'max': 1,
          }),
        ],
        depth: 0,
      );
      addTearDown(field.dispose);

      await pumpInForm(tester, EntityForm(node: field));
      expect(find.text('Part of the entity'), findsNothing);

      await tester.enterText(find.byType(CupertinoTextField), 'ex:AuthorShape');
      await tester.pump();
      expect(find.text('Part of the entity'), findsOneWidget);
    },
  );

  testWidgets('mandatory values show their label and an explanation', (
    tester,
  ) async {
    await pumpGroup(tester, group(rdfType));

    expect(find.text('Journal Article'), findsOneWidget);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is AppTooltip &&
            widget.message ==
                'This property has a mandatory value that cannot be modified',
      ),
      findsOneWidget,
    );
    expect(find.byType(RemoveButton), findsNothing);
  });

  testWidgets('a chosen container shape is one value with one delete action', (
    tester,
  ) async {
    await pumpGroup(tester, group(partOf));

    await tester.tap(find.text('Add Container'));
    await tester.pump();
    final container = group(partOf).items.single as OrItem;
    container.select(container.def.or!.first);
    await tester.pump();

    expect(find.byType(RemoveButton), findsOneWidget);
    expect(find.text('Fill in the details'), findsOneWidget);
    expect(find.text('Add Issue'), findsNothing);
  });

  Future<LiteralItem> typeInto(
    WidgetTester tester,
    Map<String, Object> bounds,
  ) async {
    final item = LiteralItem(
      def: FieldDef.fromJson({
        'uri': 'http://example.org/count',
        'datatypes': ['http://www.w3.org/2001/XMLSchema#integer'],
        ...bounds,
      }),
      depth: 0,
    );
    addTearDown(item.dispose);
    await pumpInForm(tester, ItemWidget(item: item));
    await tester.enterText(find.byType(CupertinoTextField), '-1a2.5');
    return item;
  }

  testWidgets('an integer field keeps only digits when its minimum is zero', (
    tester,
  ) async {
    final item = await typeInto(tester, {'minInclusive': 0});
    expect(item.value, '125');
  });

  testWidgets(
    'an integer field above an exclusive minimum of -1 keeps digits',
    (tester) async {
      final item = await typeInto(tester, {'minExclusive': -1});
      expect(item.value, '125');
    },
  );

  testWidgets('an integer field keeps a leading minus without a minimum', (
    tester,
  ) async {
    final item = await typeInto(tester, {});
    expect(item.value, '-125');
  });
}
