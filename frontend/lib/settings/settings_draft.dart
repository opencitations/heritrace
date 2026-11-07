// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:convert';

import 'package:flutter/widgets.dart';

import 'settings_models.dart';

/// The settings being edited. Every change goes through [update], which
/// redraws the form.
class SettingsDraft extends ChangeNotifier {
  SettingsDraft({required this.settings, required this.options})
    : _saved = jsonEncode(settings.toJson());

  /// Replaced by [cancel], so widgets keyed by it start again from the saved
  /// values.
  SystemSettings settings;
  final SettingsOptions options;
  bool editing = false;
  String _saved;
  Map<String, String> _issues = {};
  final Set<String> _unreadable = {};

  bool get changed => jsonEncode(settings.toJson()) != _saved;

  /// True while a field holds text that cannot become a value, such as letters
  /// in a number, so saving would store the last value that could.
  bool get hasUnreadableInput => _unreadable.isNotEmpty;

  void setReadable(String field, {required bool readable}) {
    final changed = readable
        ? _unreadable.remove(field)
        : _unreadable.add(field);
    if (changed) {
      notifyListeners();
    }
  }

  void startEditing() {
    editing = true;
    notifyListeners();
  }

  void cancel() {
    settings = SystemSettings.fromJson(jsonDecode(_saved) as Json);
    editing = false;
    _issues = {};
    _unreadable.clear();
    notifyListeners();
  }

  void update(VoidCallback change) {
    change();
    notifyListeners();
  }

  /// Adding or removing items shifts the positions the server used to locate
  /// its issues, so they no longer point at the right fields.
  void restructure(VoidCallback change) {
    _issues = {};
    update(change);
  }

  void setIssues(Map<String, String> issues) {
    _issues = issues;
    notifyListeners();
  }

  void markSaved() {
    _saved = jsonEncode(settings.toJson());
    editing = false;
    _issues = {};
    notifyListeners();
  }

  String? issue(String location) => _issues[location];
}
