// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../../i18n/language_names.dart';
import '../../i18n/translations.g.dart';

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

  Future<void> _pick(BuildContext context) async {
    final choice = await Navigator.of(context, rootNavigator: true).push(
      CupertinoSheetRoute<({String? language})>(
        scrollableBuilder: (context, scrollController) => _LanguageSheet(
          current: language,
          taken: taken,
          scrollController: scrollController,
        ),
      ),
    );
    if (choice != null) {
      onChanged(choice.language);
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

class _LanguageSheet extends StatefulWidget {
  const _LanguageSheet({
    required this.current,
    required this.taken,
    required this.scrollController,
  });

  final String? current;
  final Set<String?> taken;
  final ScrollController scrollController;

  @override
  State<_LanguageSheet> createState() => _LanguageSheetState();
}

class _LanguageSheetState extends State<_LanguageSheet> {
  String _query = '';

  /// Whether [code] is offered: null, for no language, is left out too when
  /// another value has no language.
  bool _offered(String? code) =>
      code == widget.current || !widget.taken.contains(code);

  bool _matches(String code, String name) {
    final query = _query.trim().toLowerCase();
    return code == query || name.toLowerCase().contains(query);
  }

  Widget _tile(String? code, String name) => SelectionContainer.disabled(
    child: MouseRegion(
      cursor: SystemMouseCursors.click,
      child: CupertinoListTile(
        title: Text(name),
        additionalInfo: code == null ? null : Text(code),
        trailing: code == widget.current
            ? const Icon(CupertinoIcons.check_mark, size: 18)
            : null,
        onTap: () => Navigator.of(context).pop((language: code)),
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final names = languageNames(TranslationProvider.of(context).locale);
    return CupertinoPageScaffold(
      navigationBar: CupertinoNavigationBar(
        automaticallyImplyLeading: false,
        leading: CupertinoButton(
          padding: EdgeInsets.zero,
          onPressed: () => Navigator.of(context).pop(),
          child: SelectionContainer.disabled(child: Text(t.ui.actions.cancel)),
        ),
        middle: Text(t.ui.form.language),
      ),
      child: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(appInputSpacing),
              child: CupertinoSearchTextField(
                placeholder: t.ui.form.searchLanguages,
                // With semantics on, the clear button that appears with the
                // first letter makes Flutter web blur the field
                // (flutter/flutter#195289, #195763).
                suffixMode: OverlayVisibilityMode.never,
                onChanged: (query) => setState(() => _query = query),
              ),
            ),
            Expanded(
              child: ListView(
                controller: widget.scrollController,
                children: [
                  if (_query.trim().isEmpty && _offered(null))
                    _tile(null, t.ui.form.noLanguage),
                  for (final MapEntry(key: code, value: name) in names.entries)
                    if (_offered(code) && _matches(code, name))
                      _tile(code, name),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
