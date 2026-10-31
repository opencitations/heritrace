// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

class AgentRef {
  const AgentRef({
    required this.kind,
    required this.url,
    required this.label,
    required this.orcidId,
  });

  factory AgentRef.fromJson(Map<String, dynamic> json) => AgentRef(
    kind: json['kind'] as String,
    url: json['url'] as String?,
    label: json['label'] as String,
    orcidId: json['orcid_id'] as String?,
  );

  final String kind;
  final String? url;
  final String label;
  final String? orcidId;
}

class SourceRef {
  const SourceRef({
    required this.kind,
    required this.url,
    required this.label,
    required this.extra,
    required this.entityUri,
    required this.timestamp,
  });

  factory SourceRef.fromJson(Map<String, dynamic> json) => SourceRef(
    kind: json['kind'] as String,
    url: json['url'] as String?,
    label: json['label'] as String,
    extra: json['extra'] as String?,
    entityUri: json['entity_uri'] as String?,
    timestamp: json['timestamp'] as String?,
  );

  final String kind;
  final String? url;
  final String label;
  final String? extra;
  final String? entityUri;
  final String? timestamp;
}
