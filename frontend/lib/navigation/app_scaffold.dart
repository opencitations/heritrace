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
import '../design/appearance.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../i18n/language.dart';
import '../i18n/translations.g.dart';
import '../session/session_controller.dart';
import 'app_paths.dart';
import 'external_navigation.dart';

const _tabPaths = [cataloguePath, createEntityPath, recycleBinPath];

/// The page one level up from an inner page, or null for the landing page and
/// the tab pages.
String? _parentPath(Uri uri) {
  if (uri.path == mergePath) {
    return entityPath(uri.queryParameters['subject']!);
  }
  return switch (uri.pathSegments) {
    ['about', _] => cataloguePath,
    ['entity-history', final entity] => entityPath(entity),
    ['entity-version', final entity, _] => entityHistoryPath(entity),
    _ => null,
  };
}

class AppScaffold extends ConsumerStatefulWidget {
  const AppScaffold({required this.child, super.key});

  final Widget child;

  @override
  ConsumerState<AppScaffold> createState() => _AppScaffoldState();
}

class _AppScaffoldState extends ConsumerState<AppScaffold> {
  /// Inner pages belong to the tab they were opened from.
  int _tab = 0;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final tab = _tabPaths.indexOf(GoRouterState.of(context).uri.path);
    if (tab >= 0) {
      _tab = tab;
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final sessionValue = ref.watch(sessionProvider);
    final session = sessionValue.value;
    final uri = GoRouterState.of(context).uri;
    final parentPath = _parentPath(uri);
    final userName = session?.userName;
    final signedIn = userName != null;
    final compact = MediaQuery.sizeOf(context).width < appCompactWidth;
    final destinations = [
      (label: t.ui.nav.catalogue, icon: CupertinoIcons.book),
      (label: t.ui.nav.add, icon: CupertinoIcons.plus_circle),
      (label: t.ui.nav.recycleBin, icon: CupertinoIcons.trash),
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

    final activeIndex = uri.path == landingPath ? -1 : _tab;
    final showTabBar = signedIn && compact;

    return CupertinoPageScaffold(
      navigationBar: CupertinoNavigationBar(
        automaticallyImplyLeading: false,
        leading: parentPath == null
            ? GestureDetector(
                onTap: () => context.go(landingPath),
                child: MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: Image.asset(
                    'assets/images/logo.png',
                    height: 28,
                    semanticLabel: session?.config.appTitle ?? t.ui.appTitle,
                  ),
                ),
              )
            : SelectionContainer.disabled(
                child: CupertinoNavigationBarBackButton(
                  previousPageTitle: t.ui.nav.back,
                  onPressed: () {
                    if (!navigateBack()) {
                      context.go(parentPath);
                    }
                  },
                ),
              ),
        middle: signedIn && !compact
            ? Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (final (index, destination) in destinations.indexed)
                    _NavButton(
                      label: destination.label,
                      icon: destination.icon,
                      active: index == activeIndex,
                      onPressed: () => context.go(_tabPaths[index]),
                    ),
                ],
              )
            : null,
        trailing: signedIn
            ? _AccountMenu(name: userName, onLogout: logout)
            : AppButton(
                icon: CupertinoIcons.person_crop_circle,
                label: t.ui.nav.login,
                onPressed: () => navigateExternally(backendUrl(loginPath)),
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
                  child: AsyncView(
                    value: sessionValue,
                    onRetry: () => ref.invalidate(sessionProvider),
                    builder: (_) => widget.child,
                  ),
                ),
              ),
            ),
          ),
          if (showTabBar)
            SelectionContainer.disabled(
              child: CupertinoTabBar(
                currentIndex: activeIndex < 0 ? 0 : activeIndex,
                activeColor: activeIndex < 0
                    ? AppColors.of(context).inactive
                    : AppColors.primary,
                onTap: (index) => context.go(_tabPaths[index]),
                items: [
                  for (final destination in destinations)
                    BottomNavigationBarItem(
                      icon: Icon(destination.icon),
                      label: destination.label,
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// The signed-in user's name, opening a menu with the appearance and language
/// choices and the account actions.
class _AccountMenu extends ConsumerWidget {
  const _AccountMenu({required this.name, required this.onLogout});

  final String name;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final currentAppearance = ref.watch(appearanceProvider);
    final currentLanguage = TranslationProvider.of(context).locale;
    final appearances = [
      (
        value: Appearance.system,
        label: t.ui.nav.appearanceSystem,
        icon: CupertinoIcons.circle_lefthalf_fill,
      ),
      (
        value: Appearance.light,
        label: t.ui.nav.appearanceLight,
        icon: CupertinoIcons.sun_max,
      ),
      (
        value: Appearance.dark,
        label: t.ui.nav.appearanceDark,
        icon: CupertinoIcons.moon,
      ),
    ];
    return SelectionContainer.disabled(
      child: CupertinoMenuAnchor(
        menuChildren: [
          for (final appearance in appearances)
            CupertinoMenuItem(
              onPressed: () => ref
                  .read(appearanceProvider.notifier)
                  .select(appearance.value),
              leading: Icon(appearance.icon),
              trailing: appearance.value == currentAppearance
                  ? const Icon(CupertinoIcons.check_mark, size: 18)
                  : null,
              child: Text(appearance.label),
            ),
          const CupertinoMenuDivider(),
          for (final language in AppLocale.values)
            CupertinoMenuItem(
              onPressed: () => selectLanguage(language),
              trailing: language == currentLanguage
                  ? const Icon(CupertinoIcons.check_mark, size: 18)
                  : null,
              child: Text(language.buildSync().ui.nav.languageName),
            ),
          const CupertinoMenuDivider(),
          CupertinoMenuItem(
            onPressed: onLogout,
            leading: const Icon(CupertinoIcons.square_arrow_left),
            child: Text(t.ui.nav.logout),
          ),
        ],
        builder: (context, controller, _) => ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 200),
          child: AppButton(
            icon: CupertinoIcons.person_crop_circle,
            label: name,
            onPressed: () =>
                controller.isOpen ? controller.close() : controller.open(),
          ),
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.label,
    required this.icon,
    required this.active,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final bool active;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 2),
      child: CupertinoButton(
        sizeStyle: CupertinoButtonSize.small,
        minimumSize: minTapTarget,
        borderRadius: BorderRadius.circular(appRadius * 2),
        color: active ? AppColors.primaryTint : null,
        foregroundColor: active
            ? AppColors.primary
            : AppColors.of(context).label,
        onPressed: onPressed,
        child: SelectionContainer.disabled(
          child: IconLabel(
            icon: icon,
            label: Text(label),
            style: active ? const TextStyle(fontWeight: FontWeight.w600) : null,
          ),
        ),
      ),
    );
  }
}
