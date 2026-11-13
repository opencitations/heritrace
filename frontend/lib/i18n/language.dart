// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../common/preference_storage.dart';
import 'translations.g.dart';

const _key = 'language';

/// The language the user picked, or null to follow the system.
AppLocale? readLanguage() => AppLocale.values.asNameMap()[readPreference(_key)];

void applyLanguage(AppLocale? locale) {
  final active = locale == null
      ? LocaleSettings.useDeviceLocaleSync()
      : LocaleSettings.setLocaleSync(locale);
  Intl.defaultLocale = active.languageTag;
}

/// The language of the interface. The server reads it from every request to
/// pick the names and descriptions of the shapes.
class LanguageController extends Notifier<AppLocale> {
  @override
  AppLocale build() => LocaleSettings.currentLocale;

  void select(AppLocale locale) {
    writePreference(_key, locale.name);
    applyLanguage(locale);
    state = locale;
  }
}

final languageProvider = NotifierProvider<LanguageController, AppLocale>(
  LanguageController.new,
);
