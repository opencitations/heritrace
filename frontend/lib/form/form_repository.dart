// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/api_exception.dart';
import '../navigation/entity_store.dart';
import 'field_def.dart';

class EntityTypeOption {
  const EntityTypeOption({
    required this.entityClass,
    required this.shape,
    required this.label,
  });

  factory EntityTypeOption.fromJson(Map<String, dynamic> json) =>
      EntityTypeOption(
        entityClass: json['class'] as String,
        shape: json['shape'] as String?,
        label: json['label'] as String,
      );

  final String entityClass;
  final String? shape;
  final String label;
}

class SearchResult {
  const SearchResult({required this.uri, required this.label});

  factory SearchResult.fromJson(Map<String, dynamic> json) =>
      SearchResult(uri: json['uri'] as String, label: json['label'] as String);

  final String uri;
  final String label;
}

class SearchPage {
  const SearchPage({required this.results, required this.hasMore});

  final List<SearchResult> results;
  final bool hasMore;
}

class FormRepository {
  const FormRepository(this._dio, this._store);

  final Dio _dio;
  final EntityStore _store;

  Future<List<EntityTypeOption>> entityTypes() async {
    final response = await apiGuard(
      () => _dio.get<Map<String, dynamic>>('${_store.apiPrefix}/entity-types'),
    );
    return (response.data!['types'] as List<dynamic>)
        .map((e) => EntityTypeOption.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<FieldDef>> formFields(String entityClass, String? shape) async {
    final response = await apiGuard(
      () => _dio.get<Map<String, dynamic>>(
        '${_store.apiPrefix}/form-fields',
        queryParameters: {'entity_class': entityClass, 'entity_shape': shape},
      ),
    );
    return parseFormFields(response.data!['form_fields'] as List<dynamic>);
  }

  Future<String?> draftLabel(Map<String, Object?> entry) async {
    final response = await apiGuard(
      () => _dio.post<Map<String, dynamic>>(
        '${_store.apiPrefix}/draft-labels',
        data: {
          'entries': [entry],
        },
      ),
    );
    return (response.data!['labels'] as List<dynamic>).first as String?;
  }

  Future<SearchPage> search({
    required String term,
    required String entityClass,
    required String? shape,
    required int offset,
    required int limit,
  }) async {
    final response = await apiGuard(
      () => _dio.post<Map<String, dynamic>>(
        '${_store.apiPrefix}/search',
        data: {
          'term': term,
          'entity_class': entityClass,
          'shape': shape,
          'offset': offset,
          'limit': limit,
        },
      ),
    );
    return _searchPage(response.data!);
  }

  Future<SearchPage> similarToDraft({
    required String entityType,
    required String? shape,
    required Map<String, List<Map<String, Object?>>> values,
  }) async {
    final response = await apiGuard(
      () => _dio.post<Map<String, dynamic>>(
        '/api/merge/similar/draft',
        data: {'entity_type': entityType, 'shape_uri': shape, 'values': values},
      ),
    );
    return _searchPage(response.data!);
  }

  SearchPage _searchPage(Map<String, dynamic> data) => SearchPage(
    results: (data['results'] as List<dynamic>)
        .map((e) => SearchResult.fromJson(e as Map<String, dynamic>))
        .toList(),
    hasMore: data['has_more'] as bool,
  );

  Future<List<String>> validDatatypes(String value) async {
    try {
      final response = await apiGuard(
        () => _dio.post<Map<String, dynamic>>(
          '${_store.apiPrefix}/validate-literal',
          data: {'value': value},
        ),
      );
      return (response.data!['valid_datatypes'] as List<dynamic>)
          .cast<String>();
    } on ApiException catch (error) {
      if (error.statusCode == 400) {
        return const [];
      }
      rethrow;
    }
  }
}

final formRepositoryProvider = Provider<FormRepository>(
  (ref) =>
      FormRepository(ref.watch(dioProvider), ref.watch(entityStoreProvider)),
  dependencies: [entityStoreProvider],
);

final entityTypesProvider = FutureProvider<List<EntityTypeOption>>(
  (ref) => ref.watch(formRepositoryProvider).entityTypes(),
  dependencies: [formRepositoryProvider],
);
