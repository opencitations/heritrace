// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'design/app_theme.dart';
import 'design/appearance.dart';
import 'i18n/translations.g.dart';
import 'navigation/app_router.dart';

class App extends ConsumerWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final router = ref.watch(routerProvider);
    return CupertinoApp.router(
      title: t.ui.appTitle,
      theme: buildAppTheme(ref.watch(appearanceProvider).brightness),
      locale: TranslationProvider.of(context).flutterLocale,
      supportedLocales: AppLocaleUtils.supportedLocales,
      localizationsDelegates: GlobalCupertinoLocalizations.delegates,
      routerConfig: router,
      builder: (context, child) => Overlay(
        initialEntries: [
          OverlayEntry(
            builder: (context) =>
                _SelectableText(router: router, child: child!),
          ),
        ],
      ),
    );
  }
}

/// Makes all text selectable, as on a web page, and clears the selection
/// when the user moves to another page.
class _SelectableText extends StatefulWidget {
  const _SelectableText({required this.router, required this.child});

  final GoRouter router;
  final Widget child;

  @override
  State<_SelectableText> createState() => _SelectableTextState();
}

class _SelectableTextState extends State<_SelectableText> {
  final _region = GlobalKey<SelectableRegionState>();

  @override
  void initState() {
    super.initState();
    widget.router.routerDelegate.addListener(_clearSelection);
  }

  @override
  void didUpdateWidget(_SelectableText oldWidget) {
    super.didUpdateWidget(oldWidget);
    oldWidget.router.routerDelegate.removeListener(_clearSelection);
    widget.router.routerDelegate.addListener(_clearSelection);
  }

  @override
  void dispose() {
    widget.router.routerDelegate.removeListener(_clearSelection);
    super.dispose();
  }

  void _clearSelection() => _region.currentState!.clearSelection();

  @override
  Widget build(BuildContext context) => SelectableRegion(
    key: _region,
    selectionControls: cupertinoTextSelectionHandleControls,
    contextMenuBuilder: (context, state) =>
        CupertinoAdaptiveTextSelectionToolbar.buttonItems(
          anchors: state.contextMenuAnchors,
          buttonItems: state.contextMenuButtonItems,
        ),
    child: widget.child,
  );
}
