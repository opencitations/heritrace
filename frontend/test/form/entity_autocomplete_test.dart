// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/form/form_model.dart';
import 'package:heritrace/form/form_repository.dart';
import 'package:heritrace/form/form_scope.dart';
import 'package:heritrace/form/widgets/entity_autocomplete.dart';
import 'package:heritrace/form/widgets/item_widgets.dart';
import 'package:heritrace/i18n/translations.g.dart';
import 'package:heritrace/navigation/entity_store.dart';

import 'fixtures.dart';

class _FakeFormRepository extends FormRepository {
  _FakeFormRepository() : super(Dio(), EntityStore.dataset);

  final searches = <({String term, String entityClass, String? shape})>[];

  @override
  Future<SearchPage> search({
    required String term,
    required String entityClass,
    required String? shape,
    required int offset,
    required int limit,
  }) async {
    searches.add((term: term, entityClass: entityClass, shape: shape));
    return const SearchPage(
      results: [SearchResult(uri: 'https://example.org/ra/1', label: 'Ada')],
      hasMore: false,
    );
  }
}

void main() {
  late EntityNode root;
  late NestedItem item;
  late _FakeFormRepository repository;

  setUp(() {
    root = EntityNode(
      entityType: article,
      entityShape: articleShape,
      fields: articleFields(),
      depth: 0,
    );
    item =
        root.groups.firstWhere((g) => g.def.uri == documentContext).addItem()
            as NestedItem;
    repository = _FakeFormRepository();
  });

  tearDown(() => root.dispose());

  Future<void> pumpItem(WidgetTester tester) async {
    LocaleSettings.setLocale(AppLocale.en);
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      TranslationProvider(
        child: ProviderScope(
          overrides: [formRepositoryProvider.overrideWithValue(repository)],
          child: CupertinoApp(
            home: CupertinoPageScaffold(
              child: FormScope(
                notifier: FormScopeController(rootLabel: 'Journal Article'),
                child: SingleChildScrollView(
                  child: EntityAutocompleteField(item: item),
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
  }

  Future<void> typeTerm(WidgetTester tester, String term) async {
    await tester.enterText(find.byType(CupertinoTextField), term);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump();
  }

  testWidgets('one character starts a search', (tester) async {
    await pumpItem(tester);

    await typeTerm(tester, 'A');

    expect(repository.searches.single.term, 'A');
  });

  testWidgets('a search looks for the final entity of a proxy', (tester) async {
    await pumpItem(tester);

    await typeTerm(tester, 'Ad');

    expect(repository.searches.single.term, 'Ad');
    expect(repository.searches.single.entityClass, agent);
    expect(repository.searches.single.shape, agentShape);
    expect(find.text('Ada'), findsOneWidget);
  });

  testWidgets('closing an untouched new entity brings search back', (
    tester,
  ) async {
    await pumpItem(tester);

    await tester.tap(find.text('Create new resource'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();

    expect(find.byType(NestedTile), findsNothing);
    expect(find.text('Search for a resource'), findsOneWidget);
  });

  testWidgets('values entered in the nested form replace the search', (
    tester,
  ) async {
    await pumpItem(tester);

    (item.child.groups.firstWhere((g) => g.def.uri == name).addItem()
            as LiteralItem)
        .setValue('Ada');
    await tester.pump();

    expect(find.byType(NestedTile), findsOneWidget);
    expect(find.text('Search for a resource'), findsNothing);
  });

  testWidgets('choosing a result links it and clearing brings search back', (
    tester,
  ) async {
    await pumpItem(tester);
    await typeTerm(tester, 'Ad');

    await tester.tap(find.text('Ada'));
    await tester.pump();

    expect(item.existingUri, 'https://example.org/ra/1');
    expect(find.byType(CupertinoTextField), findsNothing);

    await tester.tap(find.byIcon(CupertinoIcons.xmark));
    await tester.pump();

    expect(item.isExisting, isFalse);
    expect(find.byType(CupertinoTextField), findsOneWidget);
  });
}
