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

class ContextConstraint {
  const ContextConstraint({
    required this.predicate,
    required this.value,
    required this.datatype,
  });

  final String predicate;
  final String value;
  final String? datatype;

  Map<String, Object?> toJson() => {
    'predicate': predicate,
    'value': value,
    'datatype': datatype,
  };
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
    required String? entityClass,
    required String predicate,
    required String searchTarget,
    required String? connectingPredicate,
    required List<ContextConstraint> context,
    required int offset,
  }) async {
    final response = await apiGuard(
      () => _dio.post<Map<String, dynamic>>(
        '${_store.apiPrefix}/search',
        data: {
          'term': term,
          'entity_class': entityClass,
          'predicate': predicate,
          'search_target': searchTarget,
          'connecting_predicate': connectingPredicate,
          'context': context.map((c) => c.toJson()).toList(),
          'offset': offset,
          'limit': 5,
        },
      ),
    );
    final data = response.data!;
    return SearchPage(
      results: (data['results'] as List<dynamic>)
          .map((e) => SearchResult.fromJson(e as Map<String, dynamic>))
          .toList(),
      hasMore: data['has_more'] as bool,
    );
  }

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
