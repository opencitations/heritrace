// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import '../form/field_def.dart';

class OptionalValue {
  const OptionalValue({
    required this.value,
    required this.label,
    this.description,
  });

  factory OptionalValue.fromJson(Map<String, dynamic> json) => OptionalValue(
    value: json['value'] as String,
    label: json['label'] as String,
    description: json['description'] as String?,
  );

  final String value;
  final String label;
  final String? description;
}

class DetailValue {
  const DetailValue({required this.label, required this.uri});

  factory DetailValue.fromJson(Map<String, dynamic> json) =>
      DetailValue(label: json['label'] as String, uri: json['uri'] as String?);

  final String label;
  final String? uri;
}

/// A field of a linked entity shown in place of the link (`shui:DetailsViewer`).
class EntityDetail {
  const EntityDetail({required this.name, required this.values});

  factory EntityDetail.fromJson(Map<String, dynamic> json) => EntityDetail(
    name: json['name'] as String,
    values: (json['values'] as List<dynamic>)
        .map((e) => DetailValue.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final String name;
  final List<DetailValue> values;
}

class EntityTriple {
  const EntityTriple({
    required this.subject,
    required this.predicate,
    required this.value,
    required this.object,
    required this.language,
    required this.externalEntity,
    required this.isMandatory,
    required this.label,
    required this.details,
    required this.alternative,
  });

  factory EntityTriple.fromJson(Map<String, dynamic> json) => EntityTriple(
    subject: json['subject'] as String,
    predicate: json['predicate'] as String,
    value: json['value'] as String,
    object: json['object'] as String,
    language: json['language'] as String?,
    externalEntity: json['external_entity'] as String?,
    isMandatory: json['is_mandatory'] as bool,
    label: json['label'] as String?,
    details: (json['details'] as List<dynamic>?)
        ?.map((e) => EntityDetail.fromJson(e as Map<String, dynamic>))
        .toList(),
    alternative: json['alternative'] as String?,
  );

  final String subject;
  final String predicate;
  final String value;
  final String object;

  /// The language tag of a literal value, when it has one.
  final String? language;
  final String? externalEntity;
  final bool isMandatory;
  final String? label;
  final List<EntityDetail>? details;

  /// The `sh:or` alternative the linked entity matches, named above its
  /// [details].
  final String? alternative;
}

class PropertyGroup {
  const PropertyGroup({
    required this.displayName,
    required this.property,
    required this.objectShape,
    required this.isDraggable,
    required this.orderedBy,
    required this.field,
    required this.triples,
  });

  factory PropertyGroup.fromJson(Map<String, dynamic> json) => PropertyGroup(
    displayName: json['display_name'] as String,
    property: json['property'] as String,
    objectShape: json['object_shape'] as String?,
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
  final bool isDraggable;
  final String? orderedBy;
  final FieldDef? field;
  final List<EntityTriple> triples;

  /// A shape can hide one of its properties with `dash:hidden`.
  bool get isShown => switch (field) {
    null => true,
    final field => !field.hidden,
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
    required this.isComposite,
  });

  factory AffectedEntity.fromJson(Map<String, dynamic> json) => AffectedEntity(
    uri: json['uri'] as String,
    label: json['label'] as String,
    type: json['type'] as String,
    isComposite: json['is_composite'] as bool,
  );

  final String uri;
  final String label;
  final String type;
  final bool isComposite;

  Map<String, Object> toJson() => {
    'uri': uri,
    'label': label,
    'type': type,
    'is_composite': isComposite,
  };
}

class OrphanCheck {
  const OrphanCheck({
    required this.affectedEntities,
    required this.shouldDelete,
    required this.orphanStrategy,
    required this.compositeStrategy,
  });

  factory OrphanCheck.fromJson(Map<String, dynamic> json) => OrphanCheck(
    affectedEntities: (json['affected_entities'] as List<dynamic>)
        .map((e) => AffectedEntity.fromJson(e as Map<String, dynamic>))
        .toList(),
    shouldDelete: json['should_delete'] as bool? ?? false,
    orphanStrategy: json['orphan_strategy'] as String?,
    compositeStrategy: json['composite_strategy'] as String?,
  );

  final List<AffectedEntity> affectedEntities;
  final bool shouldDelete;
  final String? orphanStrategy;
  final String? compositeStrategy;
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
