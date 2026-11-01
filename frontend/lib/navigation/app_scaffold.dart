// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../common/async_view.dart';
import '../common/dialogs.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
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
      (
        label: t.ui.nav.catalogue,
        path: cataloguePath,
        icon: CupertinoIcons.book,
      ),
      (
        label: t.ui.nav.newRecord,
        path: createEntityPath,
        icon: CupertinoIcons.plus_circle,
      ),
      (
        label: t.ui.nav.timeVault,
        path: timeVaultPath,
        icon: CupertinoIcons.archivebox,
      ),
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

    final activeIndex = destinations.indexWhere((d) => d.path == currentPath);
    final showTabBar = signedIn && compact;

    return CupertinoPageScaffold(
      navigationBar: CupertinoNavigationBar(
        automaticallyImplyLeading: false,
        leading: GestureDetector(
          onTap: () => context.go(landingPath),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Image.asset('assets/images/logo.png', height: 28),
              const SizedBox(width: appInputSpacing / 2),
              Text(
                session?.config.appTitle ?? t.ui.appTitle,
                style: AppTextStyles.of(context).heading,
              ),
            ],
          ),
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (!signedIn)
              CupertinoButton(
                padding: EdgeInsets.zero,
                onPressed: () => navigateExternally(backendUrl(loginPath)),
                child: Text(t.ui.nav.login),
              )
            else if (compact)
              AppIconButton(
                icon: CupertinoIcons.square_arrow_right,
                label: t.ui.nav.logout,
                onPressed: logout,
              )
            else ...[
              for (final destination in destinations)
                _NavButton(
                  label: destination.label,
                  active: currentPath == destination.path,
                  onPressed: () => context.go(destination.path),
                ),
              _NavButton(
                label: t.ui.nav.logout,
                active: false,
                onPressed: logout,
              ),
            ],
          ],
        ),
      ),
      child: Column(
        children: [
          Expanded(
            child: SafeArea(
              bottom: !showTabBar,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: appPageMaxWidth),
                  child: Padding(
                    padding: EdgeInsets.all(
                      compact ? appCardPadding : appPageMargin,
                    ),
                    child: AsyncView(
                      value: sessionValue,
                      onRetry: () => ref.invalidate(sessionProvider),
                      builder: (_) => child,
                    ),
                  ),
                ),
              ),
            ),
          ),
          if (showTabBar)
            CupertinoTabBar(
              currentIndex: activeIndex < 0 ? 0 : activeIndex,
              activeColor: activeIndex < 0
                  ? CupertinoColors.inactiveGray
                  : AppColors.primary,
              onTap: (index) => context.go(destinations[index].path),
              items: [
                for (final destination in destinations)
                  BottomNavigationBarItem(
                    icon: Icon(destination.icon),
                    label: destination.label,
                  ),
              ],
            ),
        ],
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.label,
    required this.active,
    required this.onPressed,
  });

  final String label;
  final bool active;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return CupertinoButton(
      padding: const EdgeInsets.symmetric(horizontal: appInputSpacing),
      foregroundColor: active ? AppColors.primary : CupertinoColors.label,
      onPressed: onPressed,
      child: Text(
        label,
        style: active ? const TextStyle(fontWeight: FontWeight.w600) : null,
      ),
    );
  }
}
