// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
import '../navigation/external_navigation.dart';
import '../session/session_controller.dart';

class LandingPage extends ConsumerWidget {
  const LandingPage({required this.loginError, super.key});

  final String? loginError;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final session = ref.watch(sessionProvider).value!;
    final styles = AppTextStyles.of(context);
    return Padding(
      padding: pageMargin(context),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.asset('assets/images/logo.png', height: 160),
            const SizedBox(height: appSectionSpacing),
            Text(
              session.config.appTitle,
              style: styles.display,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: appInputSpacing),
            Text(
              session.config.appSubtitle,
              style: styles.heading.copyWith(color: AppColors.secondaryText),
              textAlign: TextAlign.center,
            ),
            if (loginError != null) ...[
              const SizedBox(height: appSectionSpacing),
              _LoginErrorBanner(code: loginError!),
            ],
            const SizedBox(height: appSectionSpacing),
            AppButton(
              variant: AppButtonVariant.filled,
              onPressed: () => session.isSignedIn
                  ? context.go(cataloguePath)
                  : navigateExternally(backendUrl(loginPath)),
              icon: CupertinoIcons.book,
              label: t.ui.landing.goToCatalogue,
            ),
          ],
        ),
      ),
    );
  }
}

class _LoginErrorBanner extends StatelessWidget {
  const _LoginErrorBanner({required this.code});

  final String code;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final message = switch (code) {
      'not_authorized' => t.ui.landing.loginNotAuthorized,
      _ => t.ui.landing.loginFailed,
    };
    return AppBanner(
      text: message,
      icon: CupertinoIcons.exclamationmark_circle,
      error: true,
    );
  }
}
