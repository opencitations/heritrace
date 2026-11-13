// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';

/// The longest list that still opens as a pull-down menu; longer lists open
/// a sheet with a search field.
const _menuLimit = 10;

/// Opens a sheet that lists [options] under [title], with a search field.
/// It returns the chosen option, or null when the user cancels.
Future<({T value})?> showOptionSheet<T>(
  BuildContext context, {
  required String title,
  required String searchPlaceholder,
  required List<AppMenuOption<T>> options,
  required T current,
}) => Navigator.of(context, rootNavigator: true).push(
  CupertinoSheetRoute<({T value})>(
    scrollableBuilder: (context, scrollController) => _OptionSheet<T>(
      title: title,
      searchPlaceholder: searchPlaceholder,
      options: options,
      current: current,
      scrollController: scrollController,
    ),
  ),
);

/// A pop-up button for one of [options]: a pull-down menu for a short list,
/// a searchable sheet titled [title] for a long one.
class OptionsButton<T> extends StatelessWidget {
  const OptionsButton({
    required this.title,
    required this.value,
    required this.options,
    required this.onChanged,
    this.errorText,
    this.focusNode,
    super.key,
  });

  final String title;
  final T value;
  final List<AppMenuOption<T>> options;
  final ValueChanged<T> onChanged;
  final String? errorText;
  final FocusNode? focusNode;

  Future<void> _pick(BuildContext context) async {
    final choice = await showOptionSheet(
      context,
      title: title,
      searchPlaceholder: Translations.of(context).ui.form.searchOptions,
      options: options,
      current: value,
    );
    if (choice != null) {
      onChanged(choice.value);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (options.length <= _menuLimit) {
      return AppMenuButton<T>(
        value: value,
        options: options,
        onChanged: onChanged,
        errorText: errorText,
        focusNode: focusNode,
      );
    }
    final selected = options.where((o) => o.value == value).firstOrNull;
    return AppSheetButton(
      label: selected?.label,
      semanticLabel: '$title: ${selected?.label ?? ''}',
      errorText: errorText,
      focusNode: focusNode,
      onPressed: () => _pick(context),
    );
  }
}

class _OptionSheet<T> extends StatefulWidget {
  const _OptionSheet({
    required this.title,
    required this.searchPlaceholder,
    required this.options,
    required this.current,
    required this.scrollController,
  });

  final String title;
  final String searchPlaceholder;
  final List<AppMenuOption<T>> options;
  final T current;
  final ScrollController scrollController;

  @override
  State<_OptionSheet<T>> createState() => _OptionSheetState<T>();
}

class _OptionSheetState<T> extends State<_OptionSheet<T>> {
  String _query = '';

  bool _matches(AppMenuOption<T> option) {
    final query = _query.trim().toLowerCase();
    return option.detail?.toLowerCase() == query ||
        option.label.toLowerCase().contains(query);
  }

  Widget _tile(AppMenuOption<T> option) => SelectionContainer.disabled(
    child: MouseRegion(
      cursor: SystemMouseCursors.click,
      child: CupertinoListTile(
        title: Text(option.label),
        subtitle: option.description == null ? null : Text(option.description!),
        additionalInfo: option.detail == null ? null : Text(option.detail!),
        trailing: option.value == widget.current
            ? const Icon(CupertinoIcons.check_mark, size: 18)
            : null,
        onTap: () => Navigator.of(context).pop((value: option.value)),
      ),
    ),
  );

  @override
  Widget build(BuildContext context) => CupertinoPageScaffold(
    navigationBar: CupertinoNavigationBar(
      automaticallyImplyLeading: false,
      leading: CupertinoButton(
        padding: EdgeInsets.zero,
        onPressed: () => Navigator.of(context).pop(),
        child: SelectionContainer.disabled(
          child: Text(Translations.of(context).ui.actions.cancel),
        ),
      ),
      middle: Text(widget.title),
    ),
    child: SafeArea(
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(appInputSpacing),
            child: CupertinoSearchTextField(
              placeholder: widget.searchPlaceholder,
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
                for (final option in widget.options)
                  if (_matches(option)) _tile(option),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}
