// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// A rule that a save breaks. [subject] and [predicate] name the field it
/// concerns: the subject is the IRI of a resource, the temporary id of one
/// that the save creates, or null for the resource a creation makes.
class ServerFieldError {
  const ServerFieldError({
    required this.code,
    required this.subject,
    required this.predicate,
    required this.params,
  });

  factory ServerFieldError.fromJson(Map<String, dynamic> json) =>
      ServerFieldError(
        code: json['code'] as String,
        subject: json['subject'] as String?,
        predicate: json['predicate'] as String?,
        params: (json['params'] as Map<String, dynamic>).cast<String, Object>(),
      );

  final String code;
  final String? subject;
  final String? predicate;
  final Map<String, Object> params;

  /// The value the rule rejects, for a rule about one value.
  String? get input => params['input'] as String?;
}

class ApiException implements Exception {
  const ApiException({
    required this.statusCode,
    required this.message,
    this.errors = const [],
  });

  final int statusCode;
  final String message;
  final List<ServerFieldError> errors;

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
      final List<dynamic> list => [
        for (final error in list)
          ServerFieldError.fromJson(error as Map<String, dynamic>),
      ],
      _ => const <ServerFieldError>[],
    };
    final message = data['message'] ?? data['error'];
    throw ApiException(
      statusCode: statusCode,
      message: message is String ? message : 'HTTP $statusCode',
      errors: errors,
    );
  }
}

/// Repeats a failed request only when the server gave no answer: the same
/// request would get the same answer.
Duration? retryUnansweredRequests(int retryCount, Object error) =>
    error is ApiException
    ? null
    : ProviderContainer.defaultRetry(retryCount, error);
