// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import '../form/field_def.dart';

class OptionalValue {
  const OptionalValue({required this.value, required this.label});

  factory OptionalValue.fromJson(Map<String, dynamic> json) => OptionalValue(
    value: json['value'] as String,
    label: json['label'] as String,
  );

  final String value;
  final String label;
}

class EntityTriple {
  const EntityTriple({
    required this.subject,
    required this.predicate,
    required this.value,
    required this.object,
    required this.externalEntity,
    required this.isMandatory,
    required this.label,
  });

  factory EntityTriple.fromJson(Map<String, dynamic> json) => EntityTriple(
    subject: json['subject'] as String,
    predicate: json['predicate'] as String,
    value: json['value'] as String,
    object: json['object'] as String,
    externalEntity: json['external_entity'] as String?,
    isMandatory: json['is_mandatory'] as bool,
    label: json['label'] as String?,
  );

  final String subject;
  final String predicate;
  final String value;
  final String object;
  final String? externalEntity;
  final bool isMandatory;
  final String? label;
}

class PropertyGroup {
  const PropertyGroup({
    required this.displayName,
    required this.property,
    required this.objectShape,
    required this.isVirtual,
    required this.isDraggable,
    required this.orderedBy,
    required this.field,
    required this.triples,
  });

  factory PropertyGroup.fromJson(Map<String, dynamic> json) => PropertyGroup(
    displayName: json['display_name'] as String,
    property: json['property'] as String,
    objectShape: json['object_shape'] as String?,
    isVirtual: json['is_virtual'] as bool,
    isDraggable: json['is_draggable'] as bool,
    orderedBy: json['ordered_by'] as String?,
    field: json['field'] == null
        ? null
        : FieldDef.fromJson(json['field'] as Map<String, dynamic>),
    triples: (json['triples'] as List<dynamic>)
        .map((e) => EntityTriple.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final String displayName;
  final String property;
  final String? objectShape;
  final bool isVirtual;
  final bool isDraggable;
  final String? orderedBy;
  final FieldDef? field;
  final List<EntityTriple> triples;

  /// Display rules can hide a property that the shape defines.
  bool get isShown => switch (field) {
    null => true,
    final field => field.shouldBeDisplayed,
  };
}

class EntityView {
  const EntityView({
    required this.uri,
    required this.label,
    required this.type,
    required this.typeLabel,
    required this.shape,
    required this.isDeleted,
    required this.hasHistory,
    required this.shacl,
    required this.hasFormFields,
    required this.canBeAdded,
    required this.canBeDeleted,
    required this.datatypes,
    required this.optionalValues,
    required this.groups,
  });

  factory EntityView.fromJson(Map<String, dynamic> json) => EntityView(
    uri: json['uri'] as String,
    label: json['label'] as String,
    type: json['type'] as String?,
    typeLabel: json['type_label'] as String,
    shape: json['shape'] as String?,
    isDeleted: json['is_deleted'] as bool,
    hasHistory: json['has_history'] as bool,
    shacl: json['shacl'] as bool,
    hasFormFields: json['has_form_fields'] as bool,
    canBeAdded: (json['can_be_added'] as List<dynamic>).cast<String>(),
    canBeDeleted: (json['can_be_deleted'] as List<dynamic>).cast<String>(),
    datatypes: {
      for (final entry in (json['datatypes'] as Map<String, dynamic>).entries)
        entry.key: (entry.value as List<dynamic>)
            .map((e) => e.toString())
            .toList(),
    },
    optionalValues: {
      for (final entry
          in (json['optional_values'] as Map<String, dynamic>).entries)
        entry.key: (entry.value as List<dynamic>)
            .map((e) => OptionalValue.fromJson(e as Map<String, dynamic>))
            .toList(),
    },
    groups: (json['groups'] as List<dynamic>)
        .map((e) => PropertyGroup.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final String uri;
  final String label;
  final String? type;
  final String typeLabel;
  final String? shape;
  final bool isDeleted;
  final bool hasHistory;
  final bool shacl;
  final bool hasFormFields;
  final List<String> canBeAdded;
  final List<String> canBeDeleted;
  final Map<String, List<String>> datatypes;
  final Map<String, List<OptionalValue>> optionalValues;
  final List<PropertyGroup> groups;
}

class LinkedResource {
  const LinkedResource({
    required this.subject,
    required this.label,
    required this.predicate,
    required this.predicateLabel,
    required this.typeLabel,
  });

  factory LinkedResource.fromJson(Map<String, dynamic> json) => LinkedResource(
    subject: json['subject'] as String,
    label: json['label'] as String,
    predicate: json['predicate'] as String,
    predicateLabel: json['predicate_label'] as String,
    typeLabel: json['type_label'] as String?,
  );

  final String subject;
  final String label;
  final String predicate;
  final String predicateLabel;
  final String? typeLabel;
}

class ResourceListPage<T> {
  const ResourceListPage({required this.results, required this.hasMore});

  final List<T> results;
  final bool hasMore;
}

class SimilarResource {
  const SimilarResource({required this.uri, required this.label});

  factory SimilarResource.fromJson(Map<String, dynamic> json) =>
      SimilarResource(
        uri: json['uri'] as String,
        label: json['label'] as String,
      );

  final String uri;
  final String label;
}

class AffectedEntity {
  const AffectedEntity({
    required this.uri,
    required this.label,
    required this.type,
    required this.isIntermediate,
  });

  factory AffectedEntity.fromJson(Map<String, dynamic> json) => AffectedEntity(
    uri: json['uri'] as String,
    label: json['label'] as String,
    type: json['type'] as String,
    isIntermediate: json['is_intermediate'] as bool,
  );

  final String uri;
  final String label;
  final String type;
  final bool isIntermediate;

  Map<String, Object> toJson() => {
    'uri': uri,
    'label': label,
    'type': type,
    'is_intermediate': isIntermediate,
  };
}

class OrphanCheck {
  const OrphanCheck({
    required this.affectedEntities,
    required this.shouldDelete,
    required this.orphanStrategy,
    required this.proxyStrategy,
  });

  factory OrphanCheck.fromJson(Map<String, dynamic> json) => OrphanCheck(
    affectedEntities: (json['affected_entities'] as List<dynamic>)
        .map((e) => AffectedEntity.fromJson(e as Map<String, dynamic>))
        .toList(),
    shouldDelete: json['should_delete'] as bool? ?? false,
    orphanStrategy: json['orphan_strategy'] as String?,
    proxyStrategy: json['proxy_strategy'] as String?,
  );

  final List<AffectedEntity> affectedEntities;
  final bool shouldDelete;
  final String? orphanStrategy;
  final String? proxyStrategy;
}

class LockResponse {
  const LockResponse({
    required this.status,
    required this.title,
    required this.message,
  });

  factory LockResponse.fromJson(Map<String, dynamic> json) => LockResponse(
    status: json['status'] as String,
    title: json['title'] as String?,
    message: json['message'] as String?,
  );

  final String status;
  final String? title;
  final String? message;

  bool get isLocked => status == 'locked';
}
