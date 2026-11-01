// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/app.dart';
import 'package:heritrace/design/controls.dart';
import 'package:heritrace/entity/entity_models.dart';
import 'package:heritrace/entity/entity_repository.dart';
import 'package:heritrace/navigation/app_paths.dart';
import 'package:heritrace/navigation/app_router.dart';

import '../helpers.dart';
import 'edit_session_test.dart' show subject, view;

class _FakeEntityRepository extends EntityRepository {
  _FakeEntityRepository() : super(Dio());

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
}
