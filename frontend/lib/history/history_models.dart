// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import '../common/references.dart';

class Modification {
  const Modification({
    required this.predicate,
    required this.predicateLabel,
    required this.object,
    required this.objectLabel,
    required this.position,
  });

  factory Modification.fromJson(Map<String, dynamic> json) => Modification(
    predicate: json['predicate'] as String,
    predicateLabel: json['predicate_label'] as String,
    object: json['object'] as String,
    objectLabel: json['object_label'] as String,
    position: (json['position'] as num?)?.toInt(),
  );

  final String predicate;
  final String predicateLabel;
  final String object;
  final String objectLabel;
  final int? position;
}

class Modifications {
  const Modifications({required this.additions, required this.deletions});

  factory Modifications.fromJson(Map<String, dynamic> json) => Modifications(
    additions: _list(json['additions']),
    deletions: _list(json['deletions']),
  );

  static List<Modification> _list(Object? value) => value == null
      ? const []
      : (value as List<dynamic>)
            .map((e) => Modification.fromJson(e as Map<String, dynamic>))
            .toList();

  final List<Modification> additions;
  final List<Modification> deletions;

  bool get isEmpty => additions.isEmpty && deletions.isEmpty;
}

class Snapshot {
  const Snapshot({
    required this.index,
    required this.timestamp,
    required this.endTimestamp,
    required this.responsibleAgent,
    required this.primarySource,
    required this.description,
    required this.modifications,
    required this.canRestore,
  });

  factory Snapshot.fromJson(Map<String, dynamic> json) => Snapshot(
    index: json['index'] as int,
    timestamp: json['timestamp'] as String,
    endTimestamp: json['end_timestamp'] as String?,
    responsibleAgent: AgentRef.fromJson(
      json['responsible_agent'] as Map<String, dynamic>,
    ),
    primarySource: SourceRef.fromJson(
      json['primary_source'] as Map<String, dynamic>,
    ),
    description: json['description'] as String,
    modifications: json['modifications'] == null
        ? null
        : Modifications.fromJson(json['modifications'] as Map<String, dynamic>),
    canRestore: json['can_restore'] as bool,
  );

  final int index;
  final String timestamp;
  final String? endTimestamp;
  final AgentRef responsibleAgent;
  final SourceRef primarySource;
  final String description;
  final Modifications? modifications;
  final bool canRestore;
}

class EntityHistory {
  const EntityHistory({
    required this.entityUri,
    required this.entityLabel,
    required this.snapshots,
  });

  factory EntityHistory.fromJson(Map<String, dynamic> json) => EntityHistory(
    entityUri: json['entity_uri'] as String,
    entityLabel: json['entity_label'] as String,
    snapshots: (json['snapshots'] as List<dynamic>)
        .map((e) => Snapshot.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final String entityUri;
  final String entityLabel;
  final List<Snapshot> snapshots;
}

class VersionGroup {
  const VersionGroup({required this.displayName, required this.values});

  factory VersionGroup.fromJson(Map<String, dynamic> json) => VersionGroup(
    displayName: json['display_name'] as String,
    values: (json['values'] as List<dynamic>).map((e) => e.toString()).toList(),
  );

  final String displayName;
  final List<String> values;
}

class EntityVersion {
  const EntityVersion({
    required this.entityUri,
    required this.entityLabel,
    required this.versionNumber,
    required this.timestamp,
    required this.prevTimestamp,
    required this.nextTimestamp,
    required this.isDeletionSnapshot,
    required this.generatedAt,
    required this.invalidatedAt,
    required this.attributedTo,
    required this.primarySource,
    required this.description,
    required this.modifications,
    required this.groups,
  });

  factory EntityVersion.fromJson(Map<String, dynamic> json) {
    final metadata = json['metadata'] as Map<String, dynamic>;
    return EntityVersion(
      entityUri: json['entity_uri'] as String,
      entityLabel: json['entity_label'] as String,
      versionNumber: json['version_number'] as int,
      timestamp: json['timestamp'] as String,
      prevTimestamp: json['prev_timestamp'] as String?,
      nextTimestamp: json['next_timestamp'] as String?,
      isDeletionSnapshot: json['is_deletion_snapshot'] as bool,
      generatedAt: metadata['generated_at'] as String,
      invalidatedAt: metadata['invalidated_at'] as String?,
      attributedTo: AgentRef.fromJson(
        metadata['attributed_to'] as Map<String, dynamic>,
      ),
      primarySource: SourceRef.fromJson(
        metadata['primary_source'] as Map<String, dynamic>,
      ),
      description: metadata['description'] as String?,
      modifications: json['modifications'] == null
          ? null
          : Modifications.fromJson(
              json['modifications'] as Map<String, dynamic>,
            ),
      groups: (json['groups'] as List<dynamic>)
          .map((e) => VersionGroup.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  final String entityUri;
  final String entityLabel;
  final int versionNumber;
  final String timestamp;
  final String? prevTimestamp;
  final String? nextTimestamp;
  final bool isDeletionSnapshot;
  final String generatedAt;
  final String? invalidatedAt;
  final AgentRef attributedTo;
  final SourceRef primarySource;
  final String? description;
  final Modifications? modifications;
  final List<VersionGroup> groups;
}
