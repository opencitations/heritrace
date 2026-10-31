// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

const rdfType = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';
const xsdDate = 'http://www.w3.org/2001/XMLSchema#date';
const xsdGYearMonth = 'http://www.w3.org/2001/XMLSchema#gYearMonth';
const xsdGYear = 'http://www.w3.org/2001/XMLSchema#gYear';
const xsdString = 'http://www.w3.org/2001/XMLSchema#string';

class FieldCondition {
  const FieldCondition({
    required this.path,
    required this.value,
    required this.pattern,
    required this.message,
  });

  factory FieldCondition.fromJson(Map<String, dynamic> json) {
    final condition = json['condition'] as Map<String, dynamic>;
    return FieldCondition(
      path: condition['path'] as String,
      value: condition['value'] as String,
      pattern: json['pattern'] as String,
      message: json['message'] as String,
    );
  }

  final String path;
  final String value;
  final String pattern;
  final String message;
}

class IntermediateRelation {
  const IntermediateRelation({
    required this.intermediateClass,
    required this.targetEntityType,
    required this.targetShape,
    required this.connectingProperty,
    required this.properties,
  });

  factory IntermediateRelation.fromJson(Map<String, dynamic> json) =>
      IntermediateRelation(
        intermediateClass: json['class'] as String,
        targetEntityType: json['targetEntityType'] as String,
        targetShape: json['targetShape'] as String?,
        connectingProperty: json['connectingProperty'] as String?,
        properties: {
          for (final entry
              in (json['properties'] as Map<String, dynamic>? ?? {}).entries)
            entry.key: (entry.value as List<dynamic>)
                .map((e) => FieldDef.fromJson(e as Map<String, dynamic>))
                .toList(),
        },
      );

  final String intermediateClass;
  final String targetEntityType;
  final String? targetShape;
  final String? connectingProperty;
  final Map<String, List<FieldDef>> properties;
}

enum FieldKind { or, nested, mandatory, select, date, literal }

class FieldDef {
  const FieldDef({
    required this.uri,
    required this.displayName,
    required this.entityType,
    required this.subjectShape,
    required this.nodeShape,
    required this.datatypes,
    required this.min,
    required this.max,
    required this.hasValue,
    required this.hasValueLabel,
    required this.optionalValues,
    required this.optionalValueLabels,
    required this.conditions,
    required this.inputType,
    required this.orderedBy,
    required this.supportsSearch,
    required this.minCharsForSearch,
    required this.searchTarget,
    required this.nestedShape,
    required this.or,
    required this.intermediateRelation,
    required this.additionalProperties,
    required this.isVirtual,
    required this.shouldBeDisplayed,
  });

  factory FieldDef.fromJson(Map<String, dynamic> json) {
    final uri = json['uri'] as String;
    final optionalValues = (json['optionalValues'] as List<dynamic>? ?? [])
        .map((e) => e.toString())
        .toList();
    return FieldDef(
      uri: uri,
      displayName: json['displayName'] as String? ?? _readableUri(uri),
      entityType: json['entityType'] as String?,
      subjectShape: json['subjectShape'] as String?,
      nodeShape: json['nodeShape'] as String?,
      datatypes: (json['datatypes'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      min: (json['min'] as num?)?.toInt() ?? 0,
      max: (json['max'] as num?)?.toInt(),
      hasValue: json['hasValue'] as String?,
      hasValueLabel: json['hasValueLabel'] as String?,
      optionalValues: optionalValues,
      optionalValueLabels: {
        for (final entry
            in (json['optionalValueLabels'] as Map<String, dynamic>? ?? {})
                .entries)
          entry.key: entry.value as String,
      },
      conditions: (json['conditions'] as List<dynamic>? ?? [])
          .map((e) => FieldCondition.fromJson(e as Map<String, dynamic>))
          .toList(),
      inputType: json['inputType'] as String? ?? 'text',
      orderedBy: json['orderedBy'] as String?,
      supportsSearch: json['supportsSearch'] == true,
      minCharsForSearch: (json['minCharsForSearch'] as num?)?.toInt() ?? 4,
      searchTarget: json['searchTarget'] as String? ?? 'self',
      nestedShape: (json['nestedShape'] as List<dynamic>?)
          ?.map((e) => FieldDef.fromJson(e as Map<String, dynamic>))
          .toList(),
      or: (json['or'] as List<dynamic>?)
          ?.map((e) => FieldDef.fromJson(e as Map<String, dynamic>))
          .toList(),
      intermediateRelation: json['intermediateRelation'] == null
          ? null
          : IntermediateRelation.fromJson(
              json['intermediateRelation'] as Map<String, dynamic>,
            ),
      additionalProperties: {
        for (final entry
            in (json['additionalProperties'] as Map<String, dynamic>? ?? {})
                .entries)
          entry.key: entry.value.toString(),
      },
      isVirtual: json['is_virtual'] == true,
      shouldBeDisplayed: json['shouldBeDisplayed'] != false,
    );
  }

  final String uri;
  final String displayName;
  final String? entityType;
  final String? subjectShape;
  final String? nodeShape;
  final List<String> datatypes;
  final int min;
  final int? max;
  final String? hasValue;
  final String? hasValueLabel;
  final List<String> optionalValues;
  final Map<String, String> optionalValueLabels;
  final List<FieldCondition> conditions;
  final String inputType;
  final String? orderedBy;
  final bool supportsSearch;
  final int minCharsForSearch;
  final String searchTarget;
  final List<FieldDef>? nestedShape;
  final List<FieldDef>? or;
  final IntermediateRelation? intermediateRelation;
  final Map<String, String> additionalProperties;
  final bool isVirtual;
  final bool shouldBeDisplayed;

  bool get isRequired => min > 0 && hasValue == null;

  bool get isDate =>
      datatypes.contains(xsdDate) ||
      datatypes.contains(xsdGYearMonth) ||
      datatypes.contains(xsdGYear);

  FieldKind get kind {
    if (or != null && or!.isNotEmpty) {
      return FieldKind.or;
    }
    if (intermediateRelation != null ||
        (nestedShape != null && nestedShape!.isNotEmpty)) {
      return FieldKind.nested;
    }
    if (hasValue != null) {
      return FieldKind.mandatory;
    }
    if (optionalValues.isNotEmpty) {
      return FieldKind.select;
    }
    if (isDate) {
      return FieldKind.date;
    }
    return FieldKind.literal;
  }

  String get childEntityType =>
      intermediateRelation?.targetEntityType ?? nestedShape!.first.entityType!;

  String? get childEntityShape => intermediateRelation != null
      ? intermediateRelation!.targetShape
      : nodeShape;

  List<FieldDef> get childFields {
    final relation = intermediateRelation;
    if (relation != null) {
      return [for (final defs in relation.properties.values) ...defs];
    }
    return nestedShape!;
  }

  String optionalValueLabel(String value) =>
      optionalValueLabels[value] ?? value;
}

String _readableUri(String uri) {
  final fragment = uri.contains('#')
      ? uri.split('#').last
      : uri.split('/').last;
  final buffer = StringBuffer();
  for (var i = 0; i < fragment.length; i++) {
    final char = fragment[i];
    if (i > 0 && char.toUpperCase() == char && char.toLowerCase() != char) {
      buffer.write(' ');
    }
    buffer.write(char.toLowerCase());
  }
  return buffer.toString();
}

List<FieldDef> parseFormFields(List<dynamic> formFields) => [
  for (final pair in formFields)
    for (final details in (pair as List<dynamic>)[1] as List<dynamic>)
      FieldDef.fromJson(details as Map<String, dynamic>),
];
