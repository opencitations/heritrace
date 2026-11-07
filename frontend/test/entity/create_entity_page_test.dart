// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/app.dart';
import 'package:heritrace/form/field_def.dart';
import 'package:heritrace/form/form_repository.dart';
import 'package:heritrace/navigation/app_paths.dart';
import 'package:heritrace/navigation/app_router.dart';
import 'package:heritrace/navigation/entity_store.dart';

import '../form/fixtures.dart';
import '../helpers.dart';

class _FakeFormRepository extends FormRepository {
  _FakeFormRepository() : super(Dio(), EntityStore.dataset);

  @override
  Future<List<EntityTypeOption>> entityTypes() async => const [
    EntityTypeOption(
      entityClass: article,
      shape: articleShape,
      label: 'Journal Article',
    ),
  ];

  @override
  Future<List<FieldDef>> formFields(String entityClass, String? shape) async =>
      articleFields();
}

void main() {
  testWidgets('leaving a new record with a draft asks for confirmation', (
    tester,
  ) async {
    await pumpApp(
      tester,
      child: const App(),
      overrides: [
        formRepositoryProvider.overrideWithValue(_FakeFormRepository()),
      ],
    );
    final router = ProviderScope.containerOf(tester.element(find.byType(App)))
        .read(routerProvider);
    router.go(createEntityPath);
    await tester.pumpAndSettle();

    router.go(landingPath);
    await tester.pumpAndSettle();
    expect(find.text('Go to the catalogue'), findsOneWidget);

    router.go(createEntityPath);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(CupertinoTextField).first, 'Abc');
    await tester.pumpAndSettle();

    router.go(landingPath);
    await tester.pumpAndSettle();
    expect(find.text('Yes, discard changes'), findsOneWidget);

    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    expect(find.text('Abc'), findsOneWidget);

    router.go(landingPath);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Yes, discard changes'));
    await tester.pumpAndSettle();
    expect(find.text('Go to the catalogue'), findsOneWidget);
  });
}
