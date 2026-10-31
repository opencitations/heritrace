// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/api_exception.dart';
import 'session_models.dart';

final sessionProvider = AsyncNotifierProvider<SessionController, Session>(
  SessionController.new,
);

class SessionController extends AsyncNotifier<Session> {
  @override
  Future<Session> build() => _fetch();

  Future<Session> _fetch() async {
    final dio = ref.read(dioProvider);
    final response = await apiGuard(
      () => dio.get<Map<String, dynamic>>('/api/me'),
    );
    return Session.fromJson(response.data!);
  }

  Future<void> refresh() async {
    state = AsyncData(await _fetch());
  }

  void markSignedOut() {
    final current = state.value;
    if (current == null || !current.isSignedIn) {
      return;
    }
    state = AsyncData(current.signedOut());
  }

  void setDefaultPrimarySource(String? source) {
    final current = state.value;
    if (current == null) {
      return;
    }
    state = AsyncData(current.withDefaultPrimarySource(source));
  }

  /// A 401 means the session has already expired, which is what logout wants.
  Future<void> logout() async {
    final dio = ref.read(dioProvider);
    try {
      await apiGuard(
        () => dio.post<void>(
          '/auth/logout',
          options: Options(validateStatus: (status) => status == 204),
        ),
      );
    } on ApiException catch (error) {
      if (error.statusCode != 401) {
        rethrow;
      }
    }
    markSignedOut();
  }
}
