// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'design/app_theme.dart';
import 'design/spacing.dart';
import 'i18n/translations.g.dart';
import 'navigation/app_router.dart';

class App extends ConsumerWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    return MaterialApp.router(
      title: t.ui.appTitle,
      theme: buildAppTheme(),
      locale: TranslationProvider.of(context).flutterLocale,
      supportedLocales: AppLocaleUtils.supportedLocales,
      routerConfig: ref.watch(routerProvider),
      builder: (context, child) {
        if (MediaQuery.sizeOf(context).width >= appCompactWidth) {
          return child!;
        }
        final theme = Theme.of(context);
        final text = theme.textTheme;
        return Theme(
          data: theme.copyWith(
            textTheme: text.copyWith(
              headlineMedium: text.headlineSmall,
              headlineSmall: text.titleLarge,
            ),
          ),
          child: child!,
        );
      },
    );
  }
}
