// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

const rdfType = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type';
const xsdDate = 'http://www.w3.org/2001/XMLSchema#date';
const xsdGYearMonth = 'http://www.w3.org/2001/XMLSchema#gYearMonth';
const xsdGYear = 'http://www.w3.org/2001/XMLSchema#gYear';
const xsdString = 'http://www.w3.org/2001/XMLSchema#string';
const xsdAnyUri = 'http://www.w3.org/2001/XMLSchema#anyURI';

const _shui = 'http://www.w3.org/ns/shacl-ui/';
const shuiAutoCompleteEditor = '${_shui}AutoCompleteEditor';
const shuiBooleanEditor = '${_shui}BooleanEditor';
const shuiDatePickerEditor = '${_shui}DatePickerEditor';
const shuiDetailsEditor = '${_shui}DetailsEditor';
const shuiEnumSelectEditor = '${_shui}EnumSelectEditor';
const shuiNumberFieldEditor = '${_shui}NumberFieldEditor';
const shuiTextAreaEditor = '${_shui}TextAreaEditor';
const shuiTextAreaWithLangEditor = '${_shui}TextAreaWithLangEditor';
const shuiTextFieldWithLangEditor = '${_shui}TextFieldWithLangEditor';

const _xsd = 'http://www.w3.org/2001/XMLSchema#';
const shIri = 'http://www.w3.org/ns/shacl#IRI';
const _unsignedIntegerDatatypes = {
  '${_xsd}nonNegativeInteger',
  '${_xsd}positiveInteger',
  '${_xsd}unsignedLong',
  '${_xsd}unsignedInt',
  '${_xsd}unsignedShort',
  '${_xsd}unsignedByte',
};
const _integerDatatypes = {
  ..._unsignedIntegerDatatypes,
  '${_xsd}integer',
  '${_xsd}int',
  '${_xsd}long',
  '${_xsd}short',
  '${_xsd}byte',
  '${_xsd}negativeInteger',
  '${_xsd}nonPositiveInteger',
};

/// A pattern that the values of a field match: the field's own, or one that
/// applies when the resource holds [condition]'s value in its field.
class ValuePattern {
  const ValuePattern({
    required this.condition,
    required this.pattern,
    required this.message,
  });

  factory ValuePattern.fromJson(Map<String, dynamic> json) => ValuePattern(
    condition: switch (json['condition']) {
      final Map<String, dynamic> condition => (
        path: condition['path'] as String,
        value: condition['value'] as String,
      ),
      _ => null,
    },
    pattern: json['pattern'] as String,
    message: json['message'] as String?,
  );

  final ({String path, String value})? condition;
  final String pattern;
  final String? message;
}

enum FieldKind { or, nested, mandatory, select, date, literal }

class FieldDef {
  const FieldDef({
    required this.uri,
    required this.displayName,
    required this.description,
    required this.entityType,
    required this.subjectShape,
    required this.nodeShape,
    required this.objectClass,
    required this.datatypes,
    required this.min,
    required this.max,
    required this.minInclusive,
    required this.maxInclusive,
    required this.minExclusive,
    required this.maxExclusive,
    required this.hasValue,
    required this.hasValueLabel,
    required this.optionalValues,
    required this.optionalValueLabels,
    required this.optionalValueDescriptions,
    required this.patterns,
    required this.editor,
    required this.orderedBy,
    required this.detailPaths,
    required this.nestedShape,
    required this.or,
    required this.nodeKind,
    required this.lessThanOrEquals,
    required this.hidden,
    required this.shownWith,
    required this.excludedWith,
  });

  factory FieldDef.fromJson(Map<String, dynamic> json) {
    final uri = json['uri'] as String;
    final optionalValues = (json['optionalValues'] as List<dynamic>? ?? [])
        .map((e) => e.toString())
        .toList();
    return FieldDef(
      uri: uri,
      displayName: json['displayName'] as String? ?? _readableUri(uri),
      description: json['description'] as String?,
      entityType: json['entityType'] as String?,
      subjectShape: json['subjectShape'] as String?,
      nodeShape: json['nodeShape'] as String?,
      objectClass: json['objectClass'] as String?,
      datatypes: (json['datatypes'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      min: (json['min'] as num?)?.toInt() ?? 0,
      max: (json['max'] as num?)?.toInt(),
      minInclusive: json['minInclusive'] as num?,
      maxInclusive: json['maxInclusive'] as num?,
      minExclusive: json['minExclusive'] as num?,
      maxExclusive: json['maxExclusive'] as num?,
      hasValue: json['hasValue'] as String?,
      hasValueLabel: json['hasValueLabel'] as String?,
      optionalValues: optionalValues,
      optionalValueLabels: {
        for (final entry
            in (json['optionalValueLabels'] as Map<String, dynamic>? ?? {})
                .entries)
          entry.key: entry.value as String,
      },
      optionalValueDescriptions: {
        for (final entry
            in (json['optionalValueDescriptions'] as Map<String, dynamic>? ??
                    {})
                .entries)
          entry.key: entry.value as String,
      },
      patterns: (json['patterns'] as List<dynamic>? ?? [])
          .map((e) => ValuePattern.fromJson(e as Map<String, dynamic>))
          .toList(),
      editor: json['editor'] as String,
      orderedBy: json['orderedBy'] as String?,
      detailPaths: (json['detailPaths'] as List<dynamic>?)?.cast<String>(),
      nestedShape: (json['nestedShape'] as List<dynamic>?)
          ?.map((e) => FieldDef.fromJson(e as Map<String, dynamic>))
          .toList(),
      or: (json['or'] as List<dynamic>?)
          ?.map((e) => FieldDef.fromJson(e as Map<String, dynamic>))
          .toList(),
      nodeKind: json['nodeKind'] as String?,
      lessThanOrEquals: [
        for (final limit in json['lessThanOrEquals'] as List<dynamic>? ?? [])
          (
            path: (limit as Map<String, dynamic>)['path'] as String,
            name: limit['name'] as String,
          ),
      ],
      hidden: json['hidden'] == true,
      shownWith: (json['shownWith'] as List<dynamic>? ?? []).cast<String>(),
      excludedWith: (json['excludedWith'] as List<dynamic>? ?? [])
          .cast<String>(),
    );
  }

  final String uri;
  final String displayName;

  /// The `sh:description` of the property shape, shown under the field.
  final String? description;
  final String? entityType;
  final String? subjectShape;
  final String? nodeShape;
  final String? objectClass;
  final List<String> datatypes;
  final int min;
  final int? max;
  final num? minInclusive;
  final num? maxInclusive;
  final num? minExclusive;
  final num? maxExclusive;
  final String? hasValue;
  final String? hasValueLabel;
  final List<String> optionalValues;
  final Map<String, String> optionalValueLabels;
  final Map<String, String> optionalValueDescriptions;
  final List<ValuePattern> patterns;

  /// The IRI of the editor that the SHACL UI scores choose for the field.
  final String editor;
  final String? orderedBy;

  bool get autocomplete => editor == shuiAutoCompleteEditor;

  /// The only field shown for this nested entity, without a frame around it.
  bool get detailsEditor => editor == shuiDetailsEditor;

  /// The fields of the nested entity shown in place, declared with
  /// `sh:property` on the property shape; all of them when null.
  final List<String>? detailPaths;
  final List<FieldDef>? nestedShape;
  final List<FieldDef>? or;

  /// The `sh:nodeKind` of the values; for an alternative of a `sh:or` field,
  /// `sh:IRI` marks the one that takes an IRI typed in place.
  final String? nodeKind;

  bool get takesIri => nodeKind == shIri;

  /// The fields of the same resource whose values the values of this one do
  /// not exceed, declared with `sh:lessThanOrEquals`.
  final List<({String path, String name})> lessThanOrEquals;
  final bool hidden;

  /// Each value carries a language, picked next to its input.
  bool get withLanguage =>
      editor == shuiTextFieldWithLangEditor ||
      editor == shuiTextAreaWithLangEditor;

  bool get multiline =>
      editor == shuiTextAreaEditor || editor == shuiTextAreaWithLangEditor;

  /// The properties of the same entity of which at least one must have a
  /// value for this field to apply; the field always applies when empty.
  final List<String> shownWith;

  /// The properties of the same entity that cannot have a value together with
  /// this field. While one of them has a value, the field applies only if it
  /// has a value itself.
  final List<String> excludedWith;

  bool get isRequired => min > 0 && hasValue == null;

  bool get isBoolean => editor == shuiBooleanEditor;

  bool get takesUrl => datatypes.contains(xsdAnyUri);

  bool get isInteger =>
      datatypes.isNotEmpty && datatypes.every(_integerDatatypes.contains);

  bool get acceptsNegative =>
      !datatypes.every(_unsignedIntegerDatatypes.contains) &&
      (minInclusive == null || minInclusive! < 0) &&
      (minExclusive == null || minExclusive! < -1);

  FieldKind get kind {
    if (or != null && or!.isNotEmpty) {
      return FieldKind.or;
    }
    if (nestedShape != null && (nestedShape!.isNotEmpty || autocomplete)) {
      return FieldKind.nested;
    }
    if (hasValue != null) {
      return FieldKind.mandatory;
    }
    return switch (editor) {
      shuiEnumSelectEditor => FieldKind.select,
      shuiDatePickerEditor => FieldKind.date,
      _ => FieldKind.literal,
    };
  }

  String get childEntityType =>
      nestedShape!.isEmpty ? objectClass! : nestedShape!.first.entityType!;

  String? get childEntityShape => nodeShape;

  List<FieldDef> get childFields => nestedShape!;

  String optionalValueLabel(String value) =>
      optionalValueLabels[value] ?? value;
}

bool isTrueLiteral(String value) => value == 'true' || value == '1';

bool _isUpper(String char) =>
    char.toUpperCase() == char && char.toLowerCase() != char;

bool _isLower(String char) =>
    char.toLowerCase() == char && char.toUpperCase() != char;

bool _isDigit(String char) => '0123456789'.contains(char);

// A capital starts a word after a lowercase letter or a digit, or when it
// closes an acronym and a lowercase letter follows: NCName gives NC and Name.
bool _startsWord(String name, int i) {
  if (i == 0 || !_isUpper(name[i])) {
    return false;
  }
  final previous = name[i - 1];
  if (_isLower(previous) || _isDigit(previous)) {
    return true;
  }
  return _isUpper(previous) && i + 1 < name.length && _isLower(name[i + 1]);
}

String _readableUri(String uri) {
  final name = uri.contains('#') ? uri.split('#').last : uri.split('/').last;
  final words = [StringBuffer()];
  for (var i = 0; i < name.length; i++) {
    if (_startsWord(name, i)) {
      words.add(StringBuffer());
    }
    words.last.write(name[i]);
  }
  final text = words
      .map((buffer) => buffer.toString())
      .map(
        (word) => word.length > 1 && word == word.toUpperCase()
            ? word
            : word.toLowerCase(),
      )
      .join(' ');
  return text.isEmpty ? text : text[0].toUpperCase() + text.substring(1);
}

List<FieldDef> parseFormFields(List<dynamic> formFields) => [
  for (final pair in formFields)
    for (final details in (pair as List<dynamic>)[1] as List<dynamic>)
      FieldDef.fromJson(details as Map<String, dynamic>),
];
