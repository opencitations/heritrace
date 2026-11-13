// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n/language.dart';
import '../session/session_controller.dart';

const _apiTimeout = Duration(seconds: 120);
const _configuredApiBaseUrl = String.fromEnvironment('API_BASE_URL');

final String apiBaseUrl = _configuredApiBaseUrl.isEmpty
    ? Uri.base.origin
    : _configuredApiBaseUrl;

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
