// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../api/api_exception.dart';

class MergeValue {
  const MergeValue({required this.readableLabel});

  factory MergeValue.fromJson(Map<String, dynamic> json) =>
      MergeValue(readableLabel: json['readable_label'] as String);

  final String readableLabel;
}

class MergeProperty {
  const MergeProperty({
    required this.predicate,
    required this.label,
    required this.values,
  });

  factory MergeProperty.fromJson(Map<String, dynamic> json) => MergeProperty(
    predicate: json['predicate'] as String,
    label: json['label'] as String,
    values: (json['values'] as List<dynamic>)
        .map((e) => MergeValue.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final String predicate;
  final String label;
  final List<MergeValue> values;
}

class MergeEntity {
  const MergeEntity({
    required this.uri,
    required this.label,
    required this.typeLabel,
    required this.properties,
  });

  factory MergeEntity.fromJson(Map<String, dynamic> json) => MergeEntity(
    uri: json['uri'] as String,
    label: json['label'] as String,
    typeLabel: json['type_label'] as String,
    properties: (json['properties'] as List<dynamic>)
        .map((e) => MergeProperty.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final String uri;
  final String label;
  final String typeLabel;
  final List<MergeProperty> properties;
}

class MergeComparison {
  const MergeComparison({required this.keep, required this.delete});

  factory MergeComparison.fromJson(Map<String, dynamic> json) =>
      MergeComparison(
        keep: MergeEntity.fromJson(json['entity1'] as Map<String, dynamic>),
        delete: MergeEntity.fromJson(json['entity2'] as Map<String, dynamic>),
      );

  final MergeEntity keep;
  final MergeEntity delete;
}

class MergeRepository {
  const MergeRepository(this._dio);

  final Dio _dio;

  Future<MergeComparison> compare(String subject, String otherSubject) async {
    final response = await apiGuard(
      () => _dio.get<Map<String, dynamic>>(
        '/api/merge/compare',
        queryParameters: {'subject': subject, 'other_subject': otherSubject},
      ),
    );
    return MergeComparison.fromJson(response.data!);
  }

  Future<void> merge({
    required String keepUri,
    required String deleteUri,
    required String? primarySource,
    required bool saveDefaultSource,
  }) => apiGuard(
    () => _dio.post<Map<String, dynamic>>(
      '/api/merge',
      data: {
        'entity1_uri': keepUri,
        'entity2_uri': deleteUri,
        'primary_source': primarySource,
        'save_default_source': saveDefaultSource,
      },
    ),
  );
}

final mergeRepositoryProvider = Provider<MergeRepository>(
  (ref) => MergeRepository(ref.watch(dioProvider)),
);

typedef MergeKey = ({String subject, String otherSubject});

final mergeComparisonProvider = FutureProvider.autoDispose
    .family<MergeComparison, MergeKey>(
      (ref, key) => ref
          .watch(mergeRepositoryProvider)
          .compare(key.subject, key.otherSubject),
    );
