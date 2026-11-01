// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/app.dart';
import 'package:heritrace/catalogue/catalogue_models.dart';
import 'package:heritrace/catalogue/catalogue_repository.dart';
import 'package:heritrace/navigation/app_paths.dart';
import 'package:heritrace/navigation/app_router.dart';

import 'helpers.dart';

const _article = 'http://purl.org/spar/fabio/JournalArticle';
const _pageSize = 30;

class _FakeCatalogueRepository extends CatalogueRepository {
  _FakeCatalogueRepository() : super(Dio());

  final requestedPages = <int?>[];

  @override
  Future<CataloguePage> fetch(CatalogueQuery query) async {
    requestedPages.add(query.page);
    final page = query.page ?? 1;
    return CataloguePage(
      entities: [
        for (var i = (page - 1) * _pageSize; i < page * _pageSize; i++)
          CatalogueEntity(
            uri: 'urn:entity:$i',
            label: 'Entity $i',
            deletion: null,
          ),
      ],
      totalPages: 2,
      currentPage: page,
      sortProperty: null,
      sortDirection: 'ASC',
      sortableProperties: const [],
      selectedClass: _article,
      selectedShape: null,
      availableClasses: const [
        CatalogueClass(
          uri: _article,
          label: 'Journal Article',
          count: '60',
          shape: null,
        ),
      ],
    );
  }
}

void main() {
  testWidgets('the catalogue loads the next page as the list scrolls', (
    tester,
  ) async {
    final repository = _FakeCatalogueRepository();
    await pumpApp(
      tester,
      child: const App(),
      overrides: [catalogueRepositoryProvider.overrideWithValue(repository)],
    );
    final router = ProviderScope.containerOf(tester.element(find.byType(App)))
        .read(routerProvider);
    router.go(
      Uri(path: cataloguePath, queryParameters: {'class': _article}).toString(),
    );
    await tester.pumpAndSettle();

    expect(find.text('Entity 0'), findsOneWidget);
    expect(repository.requestedPages, [null]);

    await tester.scrollUntilVisible(
      find.text('Entity ${2 * _pageSize - 1}'),
      500,
      scrollable: find.byType(Scrollable).last,
    );

    expect(repository.requestedPages, [null, 2]);
  });
}
