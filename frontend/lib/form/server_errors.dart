// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import '../api/api_exception.dart';
import '../i18n/translations.g.dart';
import 'form_model.dart';
import 'validator.dart';

/// The message of [error] in the language of the interface. [name] names the
/// field of the rules that count values.
String describeServerError(
  Translations t,
  ServerFieldError error,
  String? name,
) {
  final form = t.ui.form;
  Object p(String key) => error.params[key]!;
  return switch (error.code) {
    'tooMany' => form.tooMany(name: name!, count: p('count'), max: p('max')),
    'tooFew' => form.tooFew(name: name!, count: p('count'), min: p('min')),
    'tooManyAmong' => form.tooManyAmong(
      name: name!,
      values: p('values'),
      count: p('count'),
      max: p('max'),
    ),
    'tooFewAmong' => form.tooFewAmong(
      name: name!,
      values: p('values'),
      count: p('count'),
      min: p('min'),
    ),
    'invalidInput' => form.invalidInput(expected: p('expected')),
    'atLeast' => form.atLeast(limit: p('limit')),
    'atMost' => form.atMost(limit: p('limit')),
    'greaterThan' => form.greaterThan(limit: p('limit')),
    'lessThan' => form.lessThan(limit: p('limit')),
    'notAllowed' => form.notAllowed(values: p('values')),
    'requiredValue' => form.requiredValue(value: p('value')),
    'languageNotAccepted' => form.languageNotAccepted,
    'languageTaken' => form.languageTaken,
    'invalidIri' => form.invalidIri,
    'invalidPrefix' => form.invalidPrefix,
    'maxBelowMin' => form.maxBelowMin,
    'countsMissing' => form.countsMissing,
    'boundsNeedNumber' => form.boundsNeedNumber,
    'labelQueryRole' => form.labelQueryRole,
    'invalidSparql' => form.invalidSparql(error: p('error')),
    'undeclaredPrefixes' => form.undeclaredPrefixes(prefixes: p('prefixes')),
    'selectOneVariable' => form.selectOneVariable,
    'invalidRegex' => form.invalidRegex,
    'missingFormatRule' => form.missingFormatRule(value: p('value')),
    'emptyAlternative' => form.emptyAlternative,
    'mixedAlternatives' => form.mixedAlternatives,
    'exclusive' => form.exclusive(first: p('first'), second: p('second')),
    'unsupported' => form.unsupported(part: p('part')),
    'fileChanged' => form.fileChanged,
    'message' => p('message') as String,
    _ => throw StateError('Unknown error code ${error.code}'),
  };
}

/// A node of a form tree, with the breadcrumb that leads to it.
typedef FormNode = ({EntityNode node, List<String> path});

/// The new nested resources under [at], by the temporary id that names them
/// in a rejected save.
Map<String, FormNode> nestedNodes(FormNode at) {
  final nodes = <String, FormNode>{};
  for (final group in at.node.groups) {
    for (final item in group.items) {
      if (_nested(item) case final nested? when !nested.isExisting) {
        final child = (
          node: nested.child,
          path: [...at.path, group.def.displayName],
        );
        nodes[nested.tempId!] = child;
        nodes.addAll(nestedNodes(child));
      }
    }
  }
  return nodes;
}

NestedItem? _nested(FormItem item) => switch (item) {
  NestedItem() => item,
  OrItem(selectedItem: final NestedItem selected) => selected,
  _ => null,
};

/// The error that [error] becomes in the field of [at] it concerns, beside the
/// value it rejects or the only value of the field; null when [at] has no
/// such field.
ValidationError? errorInNode(
  Translations t,
  FormNode at,
  ServerFieldError error,
) {
  final group = at.node.groups
      .where((group) => group.def.uri == error.predicate)
      .firstOrNull;
  if (group == null) {
    return null;
  }
  final input = error.input;
  final item = input == null
      ? group.items.singleOrNull
      : group.items.where((item) => item.textValue == input).firstOrNull;
  final name = group.def.displayName;
  return ValidationError(
    message: describeServerError(t, error, name),
    path: at.path,
    item: item,
    fieldName: name,
  );
}

/// The name of the field of [error] away from the form: the server names the
/// fields whose values it counts, and the predicate stands for any other.
String? _serverFieldName(ServerFieldError error) =>
    error.params['name'] as String? ?? error.predicate;

/// [error] as a message outside any form, with the field it concerns.
String describeUnplacedError(Translations t, ServerFieldError error) {
  final name = _serverFieldName(error);
  final message = describeServerError(t, error, name);
  return name == null ? message : '$name: $message';
}

/// The error that [error] becomes when the form has no field for it.
ValidationError unplacedError(
  Translations t,
  ServerFieldError error,
  List<String> path,
) {
  final name = _serverFieldName(error);
  return ValidationError(
    message: describeServerError(t, error, name),
    path: path,
    fieldName: name,
  );
}
