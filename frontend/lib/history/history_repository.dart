// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/api_exception.dart';
import 'history_models.dart';

class HistoryRepository {
  const HistoryRepository(this._dio);

  final Dio _dio;

  Future<EntityHistory> history(String uri) async {
    final response = await apiGuard(
      () => _dio.get<Map<String, dynamic>>(
        '/api/entity-history/${Uri.encodeComponent(uri)}',
      ),
    );
    return EntityHistory.fromJson(response.data!);
  }

  Future<EntityVersion> version(String uri, String timestamp) async {
    final response = await apiGuard(
      () => _dio.get<Map<String, dynamic>>(
        '/api/entity-version/${_encodedVersion(uri, timestamp)}',
      ),
    );
    return EntityVersion.fromJson(response.data!);
  }

  Future<void> restore(String uri, String timestamp) => apiGuard(
    () => _dio.post<Map<String, dynamic>>(
      '/api/entity-restore/${_encodedVersion(uri, timestamp)}',
    ),
  );
}

String _encodedVersion(String uri, String timestamp) =>
    '${Uri.encodeComponent(uri)}/${Uri.encodeComponent(timestamp)}';

final historyRepositoryProvider = Provider<HistoryRepository>(
  (ref) => HistoryRepository(ref.watch(dioProvider)),
);

final entityHistoryProvider = FutureProvider.autoDispose
    .family<EntityHistory, String>(
      (ref, uri) => ref.watch(historyRepositoryProvider).history(uri),
    );

typedef VersionKey = ({String uri, String timestamp});

final entityVersionProvider = FutureProvider.autoDispose
    .family<EntityVersion, VersionKey>(
      (ref, key) =>
          ref.watch(historyRepositoryProvider).version(key.uri, key.timestamp),
    );
