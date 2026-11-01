// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

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

void selectLanguage(AppLocale locale) {
  writePreference(_key, locale.name);
  applyLanguage(locale);
}
