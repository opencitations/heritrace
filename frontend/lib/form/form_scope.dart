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
  final Set<FormItem> checkedItems = {};

  List<ValidationError> errorsFor(FormItem item) =>
      errors.where((error) => error.item == item).toList();

  bool showsErrorsFor(FormItem item) =>
      validationStarted || checkedItems.contains(item);

  void markChecked(FormItem item) {
    if (checkedItems.add(item)) {
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
    checkedItems.clear();
    notifyListeners();
  }
}
