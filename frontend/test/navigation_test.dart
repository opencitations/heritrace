// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/app.dart';
import 'package:heritrace/catalogue/catalogue_repository.dart';
import 'package:heritrace/design/app_theme.dart';
import 'package:heritrace/entity/entity_page.dart';
import 'package:heritrace/entity/entity_repository.dart';
import 'package:heritrace/history/history_repository.dart';
import 'package:heritrace/navigation/app_paths.dart';
import 'package:heritrace/navigation/app_router.dart';
import 'package:heritrace/navigation/entity_store.dart';
import 'package:heritrace/session/session_models.dart';

import 'helpers.dart';

const _entity = 'urn:entity:1';

void main() {
  testWidgets('a restored entity opens under the catalogue tab', (
    tester,
  ) async {
    await pumpApp(
      tester,
      child: const App(),
      overrides: [
        cataloguePageProvider.overrideWith(
          (ref, query) => Completer<Never>().future,
        ),
        entityVersionProvider.overrideWith(
          (ref, key) => Completer<Never>().future,
        ),
        entityViewProvider.overrideWith(
          (ref, uri) => Completer<Never>().future,
        ),
      ],
    );
    final router = ProviderScope.containerOf(tester.element(find.byType(App)))
        .read(routerProvider);

    Finder activeTab(String label) => find.descendant(
      of: find.descendant(
        of: find.byType(CupertinoNavigationBar),
        matching: find.byWidgetPredicate(
          (widget) =>
              widget is CupertinoButton &&
              widget.color == AppColors.primaryTint,
        ),
      ),
      matching: find.text(label),
    );

    router.go(recycleBinPath);
    await tester.pump();
    router.go(entityVersionPath(_entity, '2026-01-01T00:00:00+00:00'));
    await tester.pump();
    expect(activeTab('Recycle bin'), findsOneWidget);

    router.go(entityPath(_entity));
    await tester.pump();
    expect(activeTab('Catalogue'), findsOneWidget);
  });

  testWidgets('configuration pages read and write the configuration store', (
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
        entityViewProvider.overrideWith(
          (ref, uri) => Completer<Never>().future,
        ),
      ],
    );
    final router = ProviderScope.containerOf(tester.element(find.byType(App)))
        .read(routerProvider);

    router.go(EntityStore.configuration.entityPath(configurationRoot));
    await tester.pump();

    final page = tester.element(find.byType(EntityPage));
    expect(page.entityStore, EntityStore.configuration);
  });
}
