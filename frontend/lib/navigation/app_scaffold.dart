// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../common/async_view.dart';
import '../common/dialogs.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import '../session/session_controller.dart';
import 'app_paths.dart';
import 'external_navigation.dart';

class AppScaffold extends ConsumerWidget {
  const AppScaffold({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final sessionValue = ref.watch(sessionProvider);
    final session = sessionValue.value;
    final currentPath = GoRouterState.of(context).uri.path;
    final signedIn = session?.isSignedIn ?? false;
    final compact = MediaQuery.sizeOf(context).width < appCompactWidth;
    final destinations = [
      (label: t.ui.nav.catalogue, path: cataloguePath),
      (label: t.ui.nav.newRecord, path: createEntityPath),
      (label: t.ui.nav.timeVault, path: timeVaultPath),
    ];

    Future<void> logout() async {
      try {
        await ref.read(sessionProvider.notifier).logout();
      } on Exception catch (error) {
        if (context.mounted) {
          await showErrorDialog(context, error);
        }
        return;
      }
      navigateExternally(landingPath);
    }

    return Scaffold(
      appBar: AppBar(
        title: InkWell(
          onTap: () => context.go(landingPath),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Image.asset('assets/images/logo.png', height: 32),
              const SizedBox(width: appInputSpacing),
              Text(session?.config.appTitle ?? t.ui.appTitle),
            ],
          ),
        ),
        actions: [
          if (!signedIn)
            TextButton(
              onPressed: () => navigateExternally(backendUrl(loginPath)),
              child: Text(t.ui.nav.login),
            )
          else if (compact)
            PopupMenuButton<VoidCallback>(
              icon: const Icon(Icons.menu),
              onSelected: (action) => action(),
              itemBuilder: (context) => [
                for (final destination in destinations)
                  CheckedPopupMenuItem(
                    checked: currentPath == destination.path,
                    value: () => context.go(destination.path),
                    child: Text(destination.label),
                  ),
                const PopupMenuDivider(),
                PopupMenuItem(
                  value: logout,
                  child: ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.logout),
                    title: Text(t.ui.nav.logout),
                  ),
                ),
              ],
            )
          else ...[
            for (final destination in destinations)
              _NavButton(
                label: destination.label,
                path: destination.path,
                currentPath: currentPath,
              ),
            TextButton(onPressed: logout, child: Text(t.ui.nav.logout)),
          ],
          const SizedBox(width: appInputSpacing),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: appPageMaxWidth),
          child: Padding(
            padding: EdgeInsets.all(compact ? appCardPadding : appPageMargin),
            child: AsyncView(
              value: sessionValue,
              onRetry: () => ref.invalidate(sessionProvider),
              builder: (_) => child,
            ),
          ),
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.label,
    required this.path,
    required this.currentPath,
  });

  final String label;
  final String path;
  final String currentPath;

  @override
  Widget build(BuildContext context) {
    final active = currentPath == path;
    final colorScheme = Theme.of(context).colorScheme;
    return TextButton(
      style: TextButton.styleFrom(
        foregroundColor: active ? colorScheme.primary : colorScheme.onSurface,
      ),
      onPressed: () => context.go(path),
      child: Text(label),
    );
  }
}
