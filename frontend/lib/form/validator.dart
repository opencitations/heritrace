// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

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
    this.fieldName,
    this.required = false,
  });

  final String message;
  final List<String> path;
  final FormItem? item;
  final String? fieldName;
  final bool required;

  String get fullMessage =>
      fieldName == null ? message : '$fieldName: $message';
}

class ValidationMessages {
  const ValidationMessages({
    required this.required,
    required this.invalidUrl,
    required this.invalidInput,
    required this.tooMany,
    required this.tooFew,
  });

  final String required;
  final String invalidUrl;
  final String Function(String expected) invalidInput;
  final String Function(String name, int count, int max) tooMany;
  final String Function(String name, int count, int min) tooFew;
}

List<ValidationError> validateEntity(
  EntityNode node,
  ValidationMessages messages, {
  required List<String> path,
}) {
  final errors = <ValidationError>[];
  for (final group in node.groups) {
    _validateGroup(group, node, messages, path, errors);
  }
  return errors;
}

void _validateGroup(
  FieldGroup group,
  EntityNode node,
  ValidationMessages messages,
  List<String> path,
  List<ValidationError> errors,
) {
  final def = group.def;
  final userItems = group.items.where((item) => item is! MandatoryItem).length;
  if (def.max != null && userItems > def.max!) {
    errors.add(
      ValidationError(
        message: messages.tooMany(def.displayName, userItems, def.max!),
        path: path,
      ),
    );
  }
  if (group.items.length < def.min) {
    errors.add(
      ValidationError(
        message: messages.tooFew(def.displayName, group.items.length, def.min),
        path: path,
      ),
    );
  }
  for (final item in group.items) {
    _validateItem(item, node, messages, path, errors);
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
  EntityNode node,
  ValidationMessages messages,
  List<String> path,
  List<ValidationError> errors,
) {
  final def = item.def;
  switch (item) {
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
          ),
        );
      }
    case OrItem():
      final selected = item.selectedItem;
      if (selected != null) {
        _validateItem(selected, node, messages, path, errors);
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
      if (def.inputType == 'url' && !isValidUrl(value)) {
        errors.add(
          ValidationError(
            message: messages.invalidUrl,
            path: path,
            item: item,
            fieldName: def.displayName,
          ),
        );
      }
      final datatypes = item is DateItem ? [item.datatype] : def.datatypes;
      final expected = datatypeProblem(value, datatypes);
      if (expected != null) {
        errors.add(
          ValidationError(
            message: messages.invalidInput(expected),
            path: path,
            item: item,
            fieldName: def.displayName,
          ),
        );
      }
      for (final condition in def.conditions) {
        final dependent = _siblingValue(node, condition.path);
        if (dependent == condition.value &&
            !RegExp(condition.pattern).hasMatch(value)) {
          errors.add(
            ValidationError(
              message: condition.message,
              path: path,
              item: item,
              fieldName: def.displayName,
            ),
          );
        }
      }
  }
}

String? _siblingValue(EntityNode node, String predicate) {
  for (final group in node.groups) {
    if (group.def.uri != predicate) {
      continue;
    }
    for (final item in group.items) {
      final value = item.textValue;
      if (value != null && value.isNotEmpty) {
        return value;
      }
    }
  }
  return null;
}

bool hasAnyValue(EntityNode node) =>
    node.groups.any((group) => group.items.any(_hasValue));

bool _hasValue(FormItem item) => switch (item) {
  OrItem(:final selectedItem) =>
    selectedItem != null && _hasValue(selectedItem),
  NestedItem() => item.isExisting || hasAnyValue(item.child),
  MandatoryItem() => false,
  _ => !item.isEmpty,
};
