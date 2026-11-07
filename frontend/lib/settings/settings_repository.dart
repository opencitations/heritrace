// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/api_exception.dart';
import 'orcid.dart';
import 'settings_models.dart';

class SettingsRepository {
  const SettingsRepository(this._dio);

  final Dio _dio;

  Future<StoredSettings> load() async {
    final response = await apiGuard(() => _dio.get<Json>('/api/configuration'));
    return StoredSettings.fromJson(response.data!);
  }

  Future<SaveResult> save(SystemSettings settings) async {
    final response = await apiGuard(
      () => _dio.put<Json>(
        '/api/configuration',
        data: settings.toJson(),
        options: Options(
          validateStatus: (status) => const {200, 422, 423}.contains(status),
        ),
      ),
    );
    final data = response.data!;
    if (response.statusCode == 423) {
      return HeldBy(LockHolder.fromJson(data));
    }
    if (response.statusCode == 422) {
      return Rejected({
        for (final issue in data['issues'] as List<dynamic>)
          (issue as Json)['location'] as String: issue['message'] as String,
      });
    }
    return Saved(
      revision: data['revision'] as String,
      reloading: data['reloading'] as bool,
    );
  }

  /// Locks the settings for the signed-in admin, or renews the lock. Returns
  /// the admin who holds it instead, or null once the lock is acquired.
  Future<LockHolder?> lock() async {
    final response = await apiGuard(
      () => _dio.post<Json>('/api/configuration/lock'),
    );
    final data = response.data!;
    return data['status'] == 'locked' ? LockHolder.fromJson(data) : null;
  }

  Future<void> unlock() =>
      apiGuard(() => _dio.delete<Json>('/api/configuration/lock'));

  Future<OrcidLookup> lookUpOrcid(String orcidId) async {
    final response = await apiGuard(
      () => _dio.get<Json>(
        '/api/configuration/orcid/$orcidId',
        options: Options(
          validateStatus: (status) => const {200, 404, 502}.contains(status),
        ),
      ),
    );
    return switch (response.statusCode) {
      200 => OrcidFound(response.data!['name'] as String?),
      404 => const OrcidMissing(),
      _ => const OrcidUnreachable(),
    };
  }
}

final settingsRepositoryProvider = Provider<SettingsRepository>(
  (ref) => SettingsRepository(ref.watch(dioProvider)),
);

final storedSettingsProvider = FutureProvider.autoDispose<StoredSettings>(
  (ref) => ref.watch(settingsRepositoryProvider).load(),
);

final orcidLookupProvider = FutureProvider.autoDispose
    .family<OrcidLookup, String>(
      (ref, orcidId) =>
          ref.watch(settingsRepositoryProvider).lookUpOrcid(orcidId),
    );
