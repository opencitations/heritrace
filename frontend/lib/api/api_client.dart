// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n/language.dart';
import '../session/session_controller.dart';

const _apiTimeout = Duration(seconds: 120);
// The backend answers on the host that served the page, which keeps its session
// cookie on the same site as the page.
const _apiPort = int.fromEnvironment('API_PORT');

final String apiBaseUrl = _apiPort == 0
    ? Uri.base.origin
    : Uri.base.replace(port: _apiPort).origin;

String backendUrl(String path) => '$apiBaseUrl$path';

final dioProvider = Provider<Dio>((ref) {
  final dio = Dio(
    BaseOptions(
      baseUrl: apiBaseUrl,
      connectTimeout: _apiTimeout,
      receiveTimeout: _apiTimeout,
      headers: {
        'Accept': 'application/json',
        'Accept-Language': ref.watch(languageProvider).languageCode,
      },
      extra: const {'withCredentials': true},
    ),
  );
  dio.interceptors.add(
    InterceptorsWrapper(
      onError: (error, handler) {
        if (error.response?.statusCode == 401) {
          ref.read(sessionProvider.notifier).markSignedOut();
        }
        handler.next(error);
      },
    ),
  );
  return dio;
});
