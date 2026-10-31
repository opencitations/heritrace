// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import 'app_paths.dart';

class NotFoundPage extends StatelessWidget {
  const NotFoundPage({super.key});

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              t.ui.notFound.title,
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: appSectionSpacing),
            Text(t.ui.notFound.message),
            const SizedBox(height: appSectionSpacing),
            FilledButton(
              onPressed: () => context.go(cataloguePath),
              child: Text(t.ui.notFound.backToCatalogue),
            ),
          ],
        ),
      ),
    );
  }
}
