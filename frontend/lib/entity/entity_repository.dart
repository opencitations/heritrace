// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/api_exception.dart';
import '../navigation/entity_store.dart';
import 'entity_models.dart';
import 'resource_lists.dart';

class LockLostException implements Exception {
  const LockLostException();
}

class EntityRepository {
  const EntityRepository(this._dio, this._store);

  final Dio _dio;
  final EntityStore _store;

  Future<EntityView> view(String uri) async {
    final response = await apiGuard(
      () => _dio.get<Map<String, dynamic>>(
        '${_store.apiPrefix}/entity/${Uri.encodeComponent(uri)}',
      ),
    );
    return EntityView.fromJson(response.data!);
  }

  Future<String> create({
    required Map<String, Object> structuredData,
    required String? primarySource,
    required bool saveDefaultSource,
  }) async {
    final response = await apiGuard(
      () => _dio.post<Map<String, dynamic>>(
        '${_store.apiPrefix}/entity',
        data: {
          'structured_data': structuredData,
          'primary_source': primarySource,
          'save_default_source': saveDefaultSource,
        },
      ),
    );
    return response.data!['uri'] as String;
  }

  Future<ResourceListPage<LinkedResource>> linkedResources(
    String uri, {
    required int offset,
  }) async {
    final response = await apiGuard(
      () => _dio.get<Map<String, dynamic>>(
        '/api/linked-resources/',
        queryParameters: {
          'subject_uri': uri,
          'limit': resourcePageSize,
          'offset': offset,
        },
      ),
    );
    final data = response.data!;
    return ResourceListPage(
      results: (data['results'] as List<dynamic>)
          .map((e) => LinkedResource.fromJson(e as Map<String, dynamic>))
          .toList(),
      hasMore: data['has_more'] as bool,
    );
  }

  Future<ResourceListPage<SimilarResource>> similarResources(
    String uri, {
    required String entityType,
    required String? shape,
    required int offset,
  }) async {
    final response = await apiGuard(
      () => _dio.get<Map<String, dynamic>>(
        '/api/merge/similar',
        queryParameters: {
          'subject_uri': uri,
          'entity_type': entityType,
          'shape_uri': ?shape,
          'limit': resourcePageSize,
          'offset': offset,
        },
      ),
    );
    final data = response.data!;
    return ResourceListPage(
      results: (data['results'] as List<dynamic>)
          .map((e) => SimilarResource.fromJson(e as Map<String, dynamic>))
          .toList(),
      hasMore: data['has_more'] as bool,
    );
  }

  Future<LockResponse> checkLock(String uri) =>
      _lockCall('${_store.apiPrefix}/check-lock', {'resource_uri': uri});

  Future<LockResponse> acquireLock(String uri, List<String> linkedResources) =>
      _lockCall('${_store.apiPrefix}/acquire-lock', {
        'resource_uri': uri,
        'linked_resources': linkedResources,
      });

  Future<void> renewLock(String uri) async {
    try {
      await _lockCall('${_store.apiPrefix}/renew-lock', {'resource_uri': uri});
    } on ApiException catch (error) {
      if (error.statusCode == 423) {
        throw const LockLostException();
      }
      rethrow;
    }
  }

  Future<void> releaseLock(String uri) =>
      _lockCall('${_store.apiPrefix}/release-lock', {'resource_uri': uri});

  Future<LockResponse> _lockCall(String path, Map<String, Object> body) async {
    final response = await apiGuard(
      () => _dio.post<Map<String, dynamic>>(path, data: body),
    );
    return LockResponse.fromJson(response.data!);
  }

  Future<OrphanCheck> checkOrphans({
    required List<Map<String, Object?>> changes,
    required String entityType,
  }) async {
    final response = await apiGuard(
      () => _dio.post<Map<String, dynamic>>(
        '${_store.apiPrefix}/check_orphans',
        data: {'changes': changes, 'entity_type': entityType},
      ),
    );
    return OrphanCheck.fromJson(response.data!);
  }

  Future<String> applyChanges(List<Map<String, Object?>> changes) async {
    final response = await apiGuard(
      () => _dio.post<Map<String, dynamic>>(
        '${_store.apiPrefix}/apply_changes',
        data: changes,
      ),
    );
    return response.data!['message'] as String;
  }
}

final entityRepositoryProvider = Provider<EntityRepository>(
  (ref) =>
      EntityRepository(ref.watch(dioProvider), ref.watch(entityStoreProvider)),
  dependencies: [entityStoreProvider],
);

final entityViewProvider = FutureProvider.autoDispose
    .family<EntityView, String>(
      (ref, uri) => ref.watch(entityRepositoryProvider).view(uri),
      dependencies: [entityRepositoryProvider],
    );
