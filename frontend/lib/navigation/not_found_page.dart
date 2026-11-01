// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:go_router/go_router.dart';

import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import 'app_paths.dart';

class NotFoundPage extends StatelessWidget {
  const NotFoundPage({super.key});

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return CupertinoPageScaffold(
      child: Padding(
        padding: pageMargin(context),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AppHeading(
                t.ui.notFound.title,
                style: AppTextStyles.of(context).pageTitle,
              ),
              const SizedBox(height: appSectionSpacing),
              Text(t.ui.notFound.message),
              const SizedBox(height: appSectionSpacing),
              AppButton(
                variant: AppButtonVariant.filled,
                onPressed: () => context.go(cataloguePath),
                label: t.ui.notFound.backToCatalogue,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
