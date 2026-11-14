// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/app.dart';
import 'package:heritrace/design/controls.dart';
import 'package:heritrace/entity/entity_models.dart';
import 'package:heritrace/entity/entity_page.dart';
import 'package:heritrace/entity/entity_repository.dart';
import 'package:heritrace/navigation/app_paths.dart';
import 'package:heritrace/navigation/app_router.dart';
import 'package:heritrace/navigation/entity_store.dart';
import 'package:heritrace/session/session_models.dart';

import '../helpers.dart';
import '../form/fixtures.dart' show article, articleShape, title;
import 'edit_session_test.dart' show subject, view;

class _FakeEntityRepository extends EntityRepository {
  _FakeEntityRepository() : super(Dio(), EntityStore.dataset);

  final List<String> released = [];

  @override
  Future<LockResponse> checkLock(String uri) async =>
      const LockResponse(status: 'available', title: null, message: null);

  @override
  Future<LockResponse> acquireLock(
    String uri,
    List<String> linkedResources,
  ) async => const LockResponse(status: 'success', title: null, message: null);

  @override
  Future<void> releaseLock(String uri) async => released.add(uri);

  @override
  Future<String> applyChanges(List<Map<String, Object?>> changes) async =>
      'Changes applied successfully';

  @override
  Future<ResourceListPage<LinkedResource>> linkedResources(
    String uri, {
    required int offset,
  }) async => const ResourceListPage(results: [], hasMore: false);

  @override
  Future<ResourceListPage<SimilarResource>> similarResources(
    String uri, {
    required String entityType,
    required String? shape,
    required int offset,
  }) async => const ResourceListPage(results: [], hasMore: false);
}

EntityView titledView() => EntityView.fromJson({
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
  'can_be_added': <String>[],
  'can_be_deleted': <String>[],
  'datatypes': <String, dynamic>{},
  'optional_values': <String, dynamic>{},
  'groups': [
    {
      'display_name': 'Title',
      'property': title,
      'object_shape': null,
      'is_draggable': false,
      'ordered_by': null,
      'field': null,
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
  ],
});

void main() {
  testWidgets('leaving an entity with unsaved changes asks for confirmation', (
    tester,
  ) async {
    final repository = _FakeEntityRepository();
    await pumpApp(
      tester,
      child: const App(),
      overrides: [
        entityRepositoryProvider.overrideWithValue(repository),
        entityViewProvider.overrideWith((ref, uri) async => view()),
      ],
    );
    final router = ProviderScope.containerOf(tester.element(find.byType(App)))
        .read(routerProvider);
    router.go(entityPath(subject));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Edit'));
    await tester.pumpAndSettle();
    await tester.enterText(find.text('Old title'), 'New title');
    await tester.pumpAndSettle();

    router.go(landingPath);
    await tester.pumpAndSettle();
    expect(find.text('Yes, discard changes'), findsOneWidget);

    await tester.tap(
      find.descendant(
        of: find.byType(AppDialog),
        matching: find.text('Cancel'),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('New title'), findsOneWidget);
    expect(repository.released, isEmpty);

    router.go(landingPath);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Yes, discard changes'));
    await tester.pumpAndSettle();
    expect(find.text('Go to the catalogue'), findsOneWidget);
    expect(repository.released, [subject]);
  });

  testWidgets('only the entities of the dataset can be deleted', (
    tester,
  ) async {
    await pumpApp(
      tester,
      child: const App(),
      session: const Session(
        userName: 'Admin',
        defaultPrimarySource: null,
        config: testConfig,
        isAdmin: true,
      ),
      overrides: [
        entityRepositoryProvider.overrideWithValue(_FakeEntityRepository()),
        entityViewProvider.overrideWith((ref, uri) async => view()),
      ],
    );
    final router = ProviderScope.containerOf(tester.element(find.byType(App)))
        .read(routerProvider);

    router.go(entityPath(subject));
    await tester.pumpAndSettle();
    expect(find.text('Delete resource'), findsOneWidget);

    router.go(EntityStore.configuration.entityPath(subject));
    await tester.pumpAndSettle();
    expect(find.byType(EntityPage), findsOneWidget);
    expect(find.text('Delete resource'), findsNothing);
  });

  testWidgets('a save keeps its progress until the saved entity is shown', (
    tester,
  ) async {
    final loads = [Completer<EntityView>(), Completer<EntityView>()];
    var load = 0;
    await pumpApp(
      tester,
      child: const App(),
      overrides: [
        entityRepositoryProvider.overrideWithValue(_FakeEntityRepository()),
        entityViewProvider.overrideWith((ref, uri) => loads[load++].future),
      ],
    );
    final router = ProviderScope.containerOf(tester.element(find.byType(App)))
        .read(routerProvider);
    router.go(entityPath(subject));
    await tester.pump();
    loads.first.complete(titledView());
    await tester.pumpAndSettle();

    await tester.tap(find.text('Edit'));
    await tester.pumpAndSettle();
    await tester.enterText(find.text('Old title'), 'New title');
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save changes'));
    await tester.pump(const Duration(seconds: 1));

    expect(
      find.text('Applying changes to the resource. Please wait...'),
      findsOneWidget,
    );
    loads.last.complete(titledView());
    await tester.pumpAndSettle();

    expect(
      find.text('Applying changes to the resource. Please wait...'),
      findsNothing,
    );
  });
}
