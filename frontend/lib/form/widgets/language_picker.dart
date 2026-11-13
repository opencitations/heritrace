// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../../i18n/language_names.dart';
import '../../i18n/translations.g.dart';
import 'option_sheet.dart';

/// The name of [language] in the language of the interface; a tag outside
/// ISO 639-1 stays as it is.
String languageName(BuildContext context, String? language) {
  if (language == null) {
    return Translations.of(context).ui.form.noLanguage;
  }
  return languageNames(TranslationProvider.of(context).locale)[language] ??
      language;
}

/// A saved value with a language, under the name of its language.
class LanguageLabelled extends StatelessWidget {
  const LanguageLabelled({
    required this.language,
    required this.child,
    super.key,
  });

  final String language;
  final Widget child;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    spacing: appCaptionSpacing,
    children: [
      Text(
        languageName(context, language),
        style: AppTextStyles.of(context).caption,
      ),
      child,
    ],
  );
}

/// The language of a value: a pop-up button with its code that opens the
/// languages not in [taken], where null stands for no language.
class LanguageButton extends StatelessWidget {
  const LanguageButton({
    required this.language,
    required this.taken,
    required this.onChanged,
    super.key,
  });

  final String? language;
  final Set<String?> taken;
  final ValueChanged<String?> onChanged;

  /// Whether [code] is offered: null, for no language, is left out too when
  /// another value has no language.
  bool _offered(String? code) => code == language || !taken.contains(code);

  Future<void> _pick(BuildContext context) async {
    final t = Translations.of(context);
    final choice = await showOptionSheet<String?>(
      context,
      title: t.ui.form.language,
      searchPlaceholder: t.ui.form.searchLanguages,
      options: [
        if (_offered(null)) AppMenuOption(null, t.ui.form.noLanguage),
        for (final MapEntry(key: code, value: name) in languageNames(
          TranslationProvider.of(context).locale,
        ).entries)
          if (_offered(code)) AppMenuOption(code, name, detail: code),
      ],
      current: language,
    );
    if (choice != null) {
      onChanged(choice.value);
    }
  }

  @override
  Widget build(BuildContext context) => AppSheetButton(
    label: language,
    placeholder: '—',
    widestLabel: 'mm',
    semanticLabel:
        '${Translations.of(context).ui.form.language}: '
        '${languageName(context, language)}',
    onPressed: () => _pick(context),
  );
}
