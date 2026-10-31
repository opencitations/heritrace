// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';

class ApiException implements Exception {
  const ApiException({
    required this.statusCode,
    required this.message,
    this.errorType,
    this.errors = const [],
  });

  final int statusCode;
  final String message;
  final String? errorType;
  final List<String> errors;

  @override
  String toString() => 'ApiException($statusCode, $message)';
}

class NetworkException implements Exception {
  const NetworkException();
}

Future<T> apiGuard<T>(Future<T> Function() request) async {
  try {
    return await request();
  } on DioException catch (exception) {
    final response = exception.response;
    final statusCode = response?.statusCode;
    if (response == null || statusCode == null) {
      throw const NetworkException();
    }
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw ApiException(statusCode: statusCode, message: 'HTTP $statusCode');
    }
    final errors = switch (data['errors']) {
      final List<dynamic> list => list.map((e) => e.toString()).toList(),
      _ => <String>[],
    };
    final message = data['message'] ?? data['error'];
    throw ApiException(
      statusCode: statusCode,
      message: message is String
          ? message
          : errors.isNotEmpty
          ? errors.join('\n')
          : 'HTTP $statusCode',
      errorType: data['error_type'] as String?,
      errors: errors,
    );
  }
}
