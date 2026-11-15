// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/widgets.dart';

import 'form_model.dart';
import 'validator.dart';

/// Shared state of one editable entity tree: the label of the root entity for
/// breadcrumbs and the errors shown after a save attempt.
class FormScope extends InheritedNotifier<FormScopeController> {
  const FormScope({required super.notifier, required super.child, super.key});

  static FormScopeController of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<FormScope>()!.notifier!;
}

class FormScopeController extends ChangeNotifier {
  FormScopeController({required this.rootLabel});

  String rootLabel;
  List<ValidationError> errors = [];
  bool validationStarted = false;

  /// The items and saved values the user has left, whose errors show before
  /// the first save attempt.
  final Set<Object> checked = {};

  List<ValidationError> errorsFor(FormItem item) =>
      errors.where((error) => error.item == item).toList();

  List<ValidationError> errorsForValue(Object value) =>
      errors.where((error) => error.value == value).toList();

  bool showsErrorsFor(Object target) =>
      validationStarted || checked.contains(target);

  void markChecked(Object target) {
    if (checked.add(target)) {
      notifyListeners();
    }
  }

  void setErrors(List<ValidationError> next, {bool started = true}) {
    errors = next;
    validationStarted = validationStarted || started;
    notifyListeners();
  }

  void reset() {
    errors = [];
    validationStarted = false;
    checked.clear();
    notifyListeners();
  }
}
