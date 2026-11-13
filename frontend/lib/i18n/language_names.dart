// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:common_locale_data/en.dart';
import 'package:common_locale_data/it.dart';

import 'translations.g.dart';

final _isoCode = RegExp(r'^[a-z]{2}$');

final _names = <AppLocale, Map<String, String>>{};

/// The ISO 639-1 languages by code, named in [locale] and sorted by name.
Map<String, String> languageNames(AppLocale locale) =>
    _names.putIfAbsent(locale, () => _read(locale));

Map<String, String> _read(AppLocale locale) {
  final data = switch (locale) {
    AppLocale.en => CommonLocaleDataEn(),
    AppLocale.it => CommonLocaleDataIt(),
  };
  final names = [
    for (final MapEntry(key: code, value: language)
        in data.languages.languages.entries)
      if (_isoCode.hasMatch(code))
        (code, language.name[0].toUpperCase() + language.name.substring(1)),
  ]..sort((a, b) => a.$2.toLowerCase().compareTo(b.$2.toLowerCase()));
  return {for (final (code, name) in names) code: name};
}
