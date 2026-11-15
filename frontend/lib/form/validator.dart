// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'field_def.dart';
import 'form_model.dart';

const _xsd = 'http://www.w3.org/2001/XMLSchema#';

bool _intIn(String value, String min, String max) {
  final parsed = BigInt.tryParse(value);
  return parsed != null &&
      parsed >= BigInt.parse(min) &&
      parsed <= BigInt.parse(max);
}

bool _isName(String token) => RegExp(r'^[a-zA-Z_][\w.-]*$').hasMatch(token);

bool _validDate(String value) {
  if (!RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value)) {
    return false;
  }
  final parsed = DateTime.tryParse(value);
  return parsed != null && parsed.toIso8601String().startsWith(value);
}

bool _validYearMonth(String value) {
  if (!RegExp(r'^\d{4}-\d{2}$').hasMatch(value)) {
    return false;
  }
  final month = int.parse(value.substring(5));
  return month >= 1 && month <= 12;
}

bool isValidUrl(String value) => RegExp(
  r'^(https?:\/\/)?((([a-z\d]([a-z\d-]*[a-z\d])*)\.?)+[a-z]{2,}|(\d{1,3}\.){3}\d{1,3})(\:\d+)?(\/[-a-z\d%_.~+]*)*(\?[;&a-z\d%_.~+=-]*)?(\#[-a-z\d_]*)?$',
  caseSensitive: false,
).hasMatch(value);

final _whitespace = RegExp(r'\s');

/// What HERITRACE takes as an IRI, on the server too: a scheme and no spaces.
bool isIri(String value) =>
    Uri.tryParse(value)?.hasScheme == true && !value.contains(_whitespace);

class DatatypeRule {
  const DatatypeRule(this.check, this.expectedFormat);

  final bool Function(String value) check;
  final String expectedFormat;
}

final Map<String, DatatypeRule> datatypeRules = {
  '${_xsd}string': DatatypeRule((_) => true, 'any text'),
  '${_xsd}normalizedString': DatatypeRule(
    (v) => !RegExp(r'[\n\r\t]').hasMatch(v),
    'text without line breaks or tabs',
  ),
  '${_xsd}integer': DatatypeRule(
    (v) => RegExp(r'^-?\d+$').hasMatch(v),
    'whole number',
  ),
  '${_xsd}int': DatatypeRule(
    (v) => RegExp(r'^-?\d+$').hasMatch(v),
    'whole number',
  ),
  '${_xsd}positiveInteger': DatatypeRule(
    (v) => RegExp(r'^\d+$').hasMatch(v) && int.parse(v) > 0,
    'positive whole number',
  ),
  '${_xsd}negativeInteger': DatatypeRule(
    (v) => RegExp(r'^-\d+$').hasMatch(v) && int.parse(v) < 0,
    'negative whole number',
  ),
  '${_xsd}nonNegativeInteger': DatatypeRule(
    (v) => RegExp(r'^\d+$').hasMatch(v),
    'non-negative whole number',
  ),
  '${_xsd}nonPositiveInteger': DatatypeRule(
    (v) => RegExp(r'^-?\d+$').hasMatch(v) && int.parse(v) <= 0,
    'non-positive whole number',
  ),
  '${_xsd}byte': DatatypeRule(
    (v) => _intIn(v, '-128', '127'),
    'whole number between -128 and 127',
  ),
  '${_xsd}short': DatatypeRule(
    (v) => _intIn(v, '-32768', '32767'),
    'whole number between -32768 and 32767',
  ),
  '${_xsd}long': DatatypeRule(
    (v) => _intIn(v, '-9223372036854775808', '9223372036854775807'),
    'whole number between -9223372036854775808 and 9223372036854775807',
  ),
  '${_xsd}unsignedByte': DatatypeRule(
    (v) => _intIn(v, '0', '255'),
    'whole number between 0 and 255',
  ),
  '${_xsd}unsignedShort': DatatypeRule(
    (v) => _intIn(v, '0', '65535'),
    'whole number between 0 and 65535',
  ),
  '${_xsd}unsignedLong': DatatypeRule(
    (v) => _intIn(v, '0', '18446744073709551615'),
    'whole number between 0 and 18446744073709551615',
  ),
  '${_xsd}unsignedInt': DatatypeRule(
    (v) => _intIn(v, '0', '4294967295'),
    'whole number between 0 and 4294967295',
  ),
  '${_xsd}decimal': DatatypeRule(
    (v) => RegExp(r'^-?\d*\.?\d+$').hasMatch(v),
    'number (can include decimal point)',
  ),
  '${_xsd}float': DatatypeRule(
    (v) => RegExp(r'^-?\d*\.?\d+$').hasMatch(v),
    'number (can include decimal point)',
  ),
  '${_xsd}double': DatatypeRule(
    (v) => RegExp(r'^-?\d*\.?\d+$').hasMatch(v),
    'number (can include decimal point)',
  ),
  '${_xsd}duration': DatatypeRule(
    (v) => RegExp(
      r'^P(?=\d|T\d)(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$',
    ).hasMatch(v),
    'duration (e.g. P1Y2M3DT4H5M6S)',
  ),
  '${_xsd}dayTimeDuration': DatatypeRule(
    (v) =>
        RegExp(r'^P(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?$')
            .hasMatch(v),
    'day and time duration (e.g. P1DT2H3M4S)',
  ),
  '${_xsd}yearMonthDuration': DatatypeRule(
    (v) => RegExp(r'^P(?:\d+Y)?(?:\d+M)?$').hasMatch(v),
    'year and month duration (e.g. P1Y2M)',
  ),
  '${_xsd}gYearMonth': DatatypeRule(
    _validYearMonth,
    'year and month in format YYYY-MM',
  ),
  '${_xsd}gYear': DatatypeRule(
    (v) => RegExp(r'^\d{4}$').hasMatch(v),
    'year in format YYYY',
  ),
  '${_xsd}dateTime': DatatypeRule(
    (v) => RegExp(
      r'^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$',
    ).hasMatch(v),
    'date and time (e.g. 2023-06-15T14:30:00+02:00)',
  ),
  '${_xsd}dateTimeStamp': DatatypeRule(
    (v) => RegExp(
      r'^-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(Z|[+-]\d{2}:\d{2})$',
    ).hasMatch(v),
    'date and time with timezone (e.g. 2023-06-15T14:30:00+02:00)',
  ),
  '${_xsd}date': DatatypeRule(_validDate, 'date in format YYYY-MM-DD'),
  '${_xsd}time': DatatypeRule(
    (v) => RegExp(r'^([01]\d|2[0-3]):?([0-5]\d):?([0-5]\d)$').hasMatch(v),
    'time in format HH:MM:SS',
  ),
  '${_xsd}gMonth': DatatypeRule(
    (v) => RegExp(r'^--(0[1-9]|1[0-2])$').hasMatch(v),
    'month in format --MM',
  ),
  '${_xsd}gDay': DatatypeRule(
    (v) => RegExp(r'^---(0[1-9]|[12]\d|3[01])$').hasMatch(v),
    'day in format ---DD',
  ),
  '${_xsd}gMonthDay': DatatypeRule(
    (v) => RegExp(r'^--(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$').hasMatch(v),
    'month and day in format --MM-DD',
  ),
  '${_xsd}boolean': DatatypeRule(
    (v) => RegExp(r'^(true|false|1|0)$', caseSensitive: false).hasMatch(v),
    'true or false',
  ),
  '${_xsd}hexBinary': DatatypeRule(
    (v) => RegExp(r'^[0-9A-Fa-f]*$').hasMatch(v),
    'hexadecimal digits',
  ),
  '${_xsd}base64Binary': DatatypeRule(
    (v) => RegExp(r'^[A-Za-z0-9+/]*={0,2}$').hasMatch(v),
    'base64 encoded data',
  ),
  '${_xsd}anyURI': DatatypeRule(
    (v) => RegExp(
      r'^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$',
    ).hasMatch(v),
    'valid URL',
  ),
  '${_xsd}QName': DatatypeRule(
    (v) => RegExp(r'^(?:[a-zA-Z_][\w.-]*:)?[a-zA-Z_][\w.-]*$').hasMatch(v),
    'qualified name',
  ),
  '${_xsd}NOTATION': DatatypeRule(
    (v) => RegExp(r'^(?:[a-zA-Z_][\w.-]*:)?[a-zA-Z_][\w.-]*$').hasMatch(v),
    'qualified name',
  ),
  '${_xsd}ENTITY': DatatypeRule(_isName, 'valid XML name'),
  '${_xsd}ID': DatatypeRule(_isName, 'valid XML name'),
  '${_xsd}IDREF': DatatypeRule(_isName, 'valid XML name'),
  '${_xsd}NCName': DatatypeRule(_isName, 'valid XML name'),
  '${_xsd}ENTITIES': DatatypeRule(
    (v) => v.split(RegExp(r'\s+')).every(_isName),
    'list of valid XML names',
  ),
  '${_xsd}IDREFS': DatatypeRule(
    (v) => v.split(RegExp(r'\s+')).every(_isName),
    'list of valid XML names',
  ),
  '${_xsd}NMTOKEN': DatatypeRule(
    (v) => RegExp(r'^[\w.-]+$').hasMatch(v),
    'valid XML token',
  ),
  '${_xsd}NMTOKENS': DatatypeRule(
    (v) =>
        v.split(RegExp(r'\s+')).every((t) => RegExp(r'^[\w.-]+$').hasMatch(t)),
    'list of valid XML tokens',
  ),
  '${_xsd}Name': DatatypeRule(
    (v) => RegExp(r'^[a-zA-Z_:][\w.-]*$').hasMatch(v),
    'valid XML Name',
  ),
};

/// Returns null when the value satisfies one of the datatypes, otherwise the
/// expected format of the last datatype checked.
String? datatypeProblem(String value, List<String> datatypes) {
  String? expected;
  for (final datatype in datatypes) {
    final rule = datatypeRules[datatype];
    if (rule == null) {
      continue;
    }
    if (rule.check(value)) {
      return null;
    }
    expected = rule.expectedFormat;
  }
  return expected;
}

class ValidationError {
  const ValidationError({
    required this.message,
    required this.path,
    this.item,
    this.value,
    this.fieldName,
    this.required = false,
  });

  final String message;
  final List<String> path;
  final FormItem? item;

  /// The saved value edited in place that the error concerns, for an error
  /// that the server reports on a value with no form item.
  final Object? value;
  final String? fieldName;
  final bool required;

  String get fullMessage =>
      fieldName == null ? message : '$fieldName: $message';
}

class ValidationMessages {
  const ValidationMessages({
    required this.required,
    required this.invalidUrl,
    required this.invalidIri,
    required this.exceeds,
    required this.invalidInput,
    required this.tooMany,
    required this.tooFew,
    required this.atLeast,
    required this.atMost,
    required this.greaterThan,
    required this.lessThan,
  });

  final String required;
  final String invalidUrl;
  final String invalidIri;
  final String Function(String other) exceeds;
  final String Function(String expected) invalidInput;
  final String Function(String name, int count, int max) tooMany;
  final String Function(String name, int count, int min) tooFew;
  final String Function(num limit) atLeast;
  final String Function(num limit) atMost;
  final String Function(num limit) greaterThan;
  final String Function(num limit) lessThan;
}

/// The values a resource holds for a property, which the rules of its other
/// fields read.
typedef FieldValues = Iterable<String> Function(String predicate);

/// The values that the items of [node] hold.
FieldValues nodeValues(EntityNode node) =>
    (predicate) => [
      for (final group in node.groups)
        if (group.def.uri == predicate)
          for (final item in group.items)
            if (item.textValue case final value? when value.isNotEmpty) value,
    ];

/// The errors of the items of [node]; [values] gives the values of its fields.
List<ValidationError> validateEntity(
  EntityNode node,
  ValidationMessages messages, {
  required List<String> path,
  required FieldValues values,
}) {
  final errors = <ValidationError>[];
  for (final group in node.groups) {
    _validateGroup(group, values, messages, path, errors);
  }
  return errors;
}

void _validateGroup(
  FieldGroup group,
  FieldValues values,
  ValidationMessages messages,
  List<String> path,
  List<ValidationError> errors,
) {
  final def = group.def;
  final kept = group.keptCount();
  final userItems =
      kept + group.items.where((item) => item is! MandatoryItem).length;
  if (def.max != null && userItems > def.max!) {
    errors.add(
      ValidationError(
        message: messages.tooMany(def.displayName, userItems, def.max!),
        path: path,
      ),
    );
  }
  final count = kept + group.items.length;
  if (count < def.min) {
    errors.add(
      ValidationError(
        message: messages.tooFew(def.displayName, count, def.min),
        path: path,
      ),
    );
  }
  for (final item in group.items) {
    _validateItem(item, values, messages, path, errors);
  }
}

ValidationError _requiredError(
  FormItem item,
  ValidationMessages messages,
  List<String> path,
) => ValidationError(
  message: messages.required,
  path: path,
  item: item,
  fieldName: item.def.displayName,
  required: true,
);

void _validateItem(
  FormItem item,
  FieldValues values,
  ValidationMessages messages,
  List<String> path,
  List<ValidationError> errors,
) {
  final def = item.def;
  switch (item) {
    case NestedItem() when def.detailsEditor && !hasAnyValue(item.child):
      if (def.isRequired) {
        errors.add(_requiredError(item, messages, path));
      }
    case NestedItem()
        when def.autocomplete && !item.isExisting && !hasAnyValue(item.child):
      if (def.isRequired) {
        errors.add(_requiredError(item, messages, path));
      }
    case NestedItem():
      if (!item.isExisting) {
        errors.addAll(
          validateEntity(
            item.child,
            messages,
            path: [...path, def.displayName],
            values: nodeValues(item.child),
          ),
        );
      }
    case OrItem():
      final selected = item.selectedItem;
      if (selected != null) {
        _validateItem(selected, values, messages, path, errors);
      } else if (def.isRequired) {
        errors.add(_requiredError(item, messages, path));
      }
    case MandatoryItem():
      break;
    case LiteralItem() || SelectItem() || DateItem():
      final value = item.textValue!.trim();
      if (value.isEmpty) {
        if (def.isRequired) {
          errors.add(_requiredError(item, messages, path));
        }
        return;
      }
      final datatypes = item is DateItem ? [item.datatype] : def.datatypes;
      errors.addAll([
        for (final problem in valueProblems(
          value,
          def,
          datatypes,
          messages,
          values,
        ))
          ValidationError(
            message: problem,
            path: path,
            item: item,
            fieldName: def.displayName,
          ),
      ]);
  }
}

/// The rules that [value], of one of [datatypes], breaks in the field of
/// [def]; [values] gives the values of the other fields of its resource.
List<String> valueProblems(
  String value,
  FieldDef def,
  List<String> datatypes,
  ValidationMessages messages,
  FieldValues values,
) {
  final expected = datatypeProblem(value, datatypes);
  return [
    if (def.inputType == 'url' && !isValidUrl(value)) messages.invalidUrl,
    if (def.takesIri && !isIri(value)) messages.invalidIri,
    if (expected != null)
      messages.invalidInput(expected)
    else
      ?_boundProblem(value, def, messages),
    if (brokenPattern(value, def.patterns, values) case final broken?)
      broken.message ?? messages.invalidInput(broken.pattern),
    ...limitProblems(value, def, messages, values),
  ];
}

/// The fields of the resource whose values [value] exceeds, among those that
/// the field of [def] names with `sh:lessThanOrEquals`.
List<String> limitProblems(
  String value,
  FieldDef def,
  ValidationMessages messages,
  FieldValues values,
) => [
  for (final limit in def.lessThanOrEquals)
    if (!values(limit.path).every((other) => atMost(value, other)))
      messages.exceeds(limit.name),
];

final _year = RegExp(r'^\d{4}$');
final _yearMonth = RegExp(r'^\d{4}-\d{2}$');
final _date = RegExp(r'^\d{4}-\d{2}-\d{2}$');

/// Whether [value] does not exceed [limit]. Numbers compare with numbers and
/// dates with dates of the same kind; any other pair cannot be compared and
/// breaks the rule, as on the server.
bool atMost(String value, String limit) {
  final (number, limitNumber) = (num.tryParse(value), num.tryParse(limit));
  if (number != null && limitNumber != null) {
    return number <= limitNumber;
  }
  return [
        _year,
        _yearMonth,
        _date,
      ].any((kind) => kind.hasMatch(value) && kind.hasMatch(limit)) &&
      value.compareTo(limit) <= 0;
}

/// The pattern that [value] breaks among those of its field. The field's own
/// patterns apply to every value; among the conditional ones whose condition
/// holds in [values], the value needs to match one.
ValuePattern? brokenPattern(
  String value,
  List<ValuePattern> patterns,
  FieldValues values,
) {
  bool matches(ValuePattern pattern) => RegExp(pattern.pattern).hasMatch(value);
  final conditional = [
    for (final pattern in patterns)
      if (pattern.condition case final condition?
          when values(condition.path).contains(condition.value))
        pattern,
  ];
  return patterns
          .where((pattern) => pattern.condition == null && !matches(pattern))
          .firstOrNull ??
      (conditional.isNotEmpty && !conditional.any(matches)
          ? conditional.first
          : null);
}

String? _boundProblem(String value, FieldDef def, ValidationMessages messages) {
  num number() => num.parse(value);
  if (def.minInclusive case final limit? when number() < limit) {
    return messages.atLeast(limit);
  }
  if (def.maxInclusive case final limit? when number() > limit) {
    return messages.atMost(limit);
  }
  if (def.minExclusive case final limit? when number() <= limit) {
    return messages.greaterThan(limit);
  }
  if (def.maxExclusive case final limit? when number() >= limit) {
    return messages.lessThan(limit);
  }
  return null;
}

bool hasAnyValue(EntityNode node) =>
    node.groups.any((group) => group.items.any(hasValue));

bool hasValue(FormItem item) => switch (item) {
  OrItem(:final selectedItem) => selectedItem != null && hasValue(selectedItem),
  NestedItem() => item.isExisting || hasAnyValue(item.child),
  MandatoryItem() => false,
  _ => !item.isEmpty,
};
