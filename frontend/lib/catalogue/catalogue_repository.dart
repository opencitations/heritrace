// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/api_exception.dart';
import 'catalogue_models.dart';

class CatalogueQuery {
  const CatalogueQuery({
    required this.recycleBin,
    this.entityClass,
    this.shape,
    this.page,
    this.sortProperty,
    this.sortDirection,
  });

  factory CatalogueQuery.fromParams({
    required bool recycleBin,
    required Map<String, String> params,
  }) => CatalogueQuery(
    recycleBin: recycleBin,
    entityClass: params['class'],
    shape: params['shape'],
    sortProperty: params['sort_property'],
    sortDirection: params['sort_direction'],
  );

  final bool recycleBin;
  final String? entityClass;
  final String? shape;

  /// The page to fetch; the address leaves it out, since more pages load as
  /// the list scrolls.
  final int? page;
  final String? sortProperty;
  final String? sortDirection;

  Map<String, String> toParams() => {
    'class': ?entityClass,
    'shape': ?shape,
    if (page != null) 'page': '$page',
    'sort_property': ?sortProperty,
    'sort_direction': ?sortDirection,
  };

  CatalogueQuery copyWith({
    String? entityClass,
    String? shape,
    int? page,
    String? sortProperty,
    String? sortDirection,
    bool resetShape = false,
  }) => CatalogueQuery(
    recycleBin: recycleBin,
    entityClass: entityClass ?? this.entityClass,
    shape: resetShape ? null : (shape ?? this.shape),
    page: page ?? this.page,
    sortProperty: sortProperty ?? this.sortProperty,
    sortDirection: sortDirection ?? this.sortDirection,
  );

  @override
  bool operator ==(Object other) =>
      other is CatalogueQuery &&
      other.recycleBin == recycleBin &&
      other.entityClass == entityClass &&
      other.shape == shape &&
      other.page == page &&
      other.sortProperty == sortProperty &&
      other.sortDirection == sortDirection;

  @override
  int get hashCode => Object.hash(
    recycleBin,
    entityClass,
    shape,
    page,
    sortProperty,
    sortDirection,
  );
}

class CatalogueRepository {
  const CatalogueRepository(this._dio);

  final Dio _dio;

  Future<CataloguePage> fetch(CatalogueQuery query) async {
    final response = await apiGuard(
      () => _dio.get<Map<String, dynamic>>(
        query.recycleBin ? '/api/recycle-bin' : '/api/catalogue',
        queryParameters: query.toParams(),
      ),
    );
    return CataloguePage.fromJson(response.data!);
  }
}

final catalogueRepositoryProvider = Provider<CatalogueRepository>(
  (ref) => CatalogueRepository(ref.watch(dioProvider)),
);

final cataloguePageProvider = FutureProvider.autoDispose
    .family<CataloguePage, CatalogueQuery>(
      (ref, query) => ref.watch(catalogueRepositoryProvider).fetch(query),
    );
