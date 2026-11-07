// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:intl/intl.dart';

import '../common/references.dart';

class CatalogueClass {
  const CatalogueClass({
    required this.uri,
    required this.label,
    required this.count,
    required this.capped,
    required this.shape,
  });

  factory CatalogueClass.fromJson(Map<String, dynamic> json) => CatalogueClass(
    uri: json['uri'] as String,
    label: json['label'] as String,
    count: json['count_numeric'] as int,
    capped: json['count'].toString().endsWith('+'),
    shape: json['shape'] as String?,
  );

  final String uri;
  final String label;
  final int count;

  /// Counting stopped at the configured limit, so there may be more.
  final bool capped;
  final String? shape;

  String get countText =>
      '${NumberFormat.decimalPattern().format(count)}${capped ? '+' : ''}';
}

class SortableProperty {
  const SortableProperty({required this.property, required this.displayName});

  factory SortableProperty.fromJson(Map<String, dynamic> json) =>
      SortableProperty(
        property: json['property'] as String,
        displayName: json['displayName'] as String,
      );

  final String property;
  final String displayName;
}

/// An entry of the catalogue, or of the recycle bin when [deletion] is set.
class CatalogueEntity {
  const CatalogueEntity({
    required this.uri,
    required this.label,
    required this.deletion,
  });

  factory CatalogueEntity.fromJson(Map<String, dynamic> json) =>
      CatalogueEntity(
        uri: json['uri'] as String,
        label: json['label'] as String,
        deletion: json.containsKey('deletionTime')
            ? Deletion.fromJson(json)
            : null,
      );

  final String uri;
  final String label;
  final Deletion? deletion;
}

class Deletion {
  const Deletion({
    required this.time,
    required this.deletedBy,
    required this.lastValidSnapshotTime,
    required this.type,
  });

  factory Deletion.fromJson(Map<String, dynamic> json) => Deletion(
    time: json['deletionTime'] as String,
    deletedBy: AgentRef.fromJson(json['deletedBy'] as Map<String, dynamic>),
    lastValidSnapshotTime: json['lastValidSnapshotTime'] as String,
    type: json['type'] as String,
  );

  final String time;
  final AgentRef deletedBy;
  final String lastValidSnapshotTime;
  final String type;
}

class CataloguePage {
  const CataloguePage({
    required this.entities,
    required this.totalPages,
    required this.currentPage,
    required this.sortProperty,
    required this.sortDirection,
    required this.sortableProperties,
    required this.selectedClass,
    required this.selectedShape,
    required this.availableClasses,
  });

  factory CataloguePage.fromJson(Map<String, dynamic> json) => CataloguePage(
    entities: (json['entities'] as List<dynamic>)
        .map((e) => CatalogueEntity.fromJson(e as Map<String, dynamic>))
        .toList(),
    totalPages: json['total_pages'] as int,
    currentPage: json['current_page'] as int,
    sortProperty: json['sort_property'] as String?,
    sortDirection: json['sort_direction'] as String,
    sortableProperties: (json['sortable_properties'] as List<dynamic>)
        .map((e) => SortableProperty.fromJson(e as Map<String, dynamic>))
        .toList(),
    selectedClass: json['selected_class'] as String?,
    selectedShape: json['selected_shape'] as String?,
    availableClasses: (json['available_classes'] as List<dynamic>)
        .map((e) => CatalogueClass.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final List<CatalogueEntity> entities;
  final int totalPages;
  final int currentPage;
  final String? sortProperty;
  final String sortDirection;
  final List<SortableProperty> sortableProperties;
  final String? selectedClass;
  final String? selectedShape;
  final List<CatalogueClass> availableClasses;
}
