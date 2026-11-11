// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/api_exception.dart';
import '../common/async_view.dart';
import '../common/dialogs.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../entity/edit_session.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
import '../navigation/entity_store.dart';
import '../navigation/external_navigation.dart';
import '../navigation/leave_guard.dart';
import '../session/session_controller.dart';
import 'settings_draft.dart';
import 'settings_models.dart';
import 'settings_repository.dart';
import 'system_settings_form.dart';

enum SettingsTab { system, types }

const reloadPollInterval = Duration(seconds: 2);
const _reloadAttempts = 90;

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return AsyncView(
      value: ref.watch(storedSettingsProvider),
      onRetry: () => ref.invalidate(storedSettingsProvider),
      header: const SettingsHeader(tab: SettingsTab.system),
      builder: (stored) => _SettingsEditor(stored: stored),
    );
  }
}

class _SettingsEditor extends ConsumerStatefulWidget {
  const _SettingsEditor({required this.stored});

  final StoredSettings stored;

  @override
  ConsumerState<_SettingsEditor> createState() => _SettingsEditorState();
}

class _SettingsEditorState extends ConsumerState<_SettingsEditor> {
  late final SettingsDraft _draft;
  late final LeaveGuard _leaveGuard;
  late final SettingsRepository _repository;

  /// Runs while this admin holds the lock on the settings.
  Timer? _renewTimer;

  @override
  void initState() {
    super.initState();
    _repository = ref.read(settingsRepositoryProvider);
    _draft = SettingsDraft(
      settings: widget.stored.settings,
      options: widget.stored.options,
    );
    _leaveGuard = ref.read(leaveGuardProvider)..register(_confirmDiscard);
    if (ref.read(sessionProvider).value!.setupRequired) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _startEditing());
    }
  }

  @override
  void dispose() {
    _leaveGuard.unregister(_confirmDiscard);
    if (_renewTimer != null) {
      _releaseLock();
    }
    _draft.dispose();
    super.dispose();
  }

  Future<void> _startEditing() async {
    final LockHolder? holder;
    try {
      holder = await _repository.lock();
    } on Exception catch (error) {
      if (mounted) {
        await showErrorDialog(context, error);
      }
      return;
    }
    if (!mounted) {
      unawaited(_repository.unlock());
      return;
    }
    if (holder != null) {
      await _showHeldBy(holder);
      return;
    }
    _renewTimer = Timer.periodic(lockRenewalInterval, (_) => _renewLock());
    _draft.startEditing();
  }

  Future<void> _showHeldBy(LockHolder holder) {
    final t = Translations.of(context).ui.settings;
    return showMessageDialog(
      context,
      title: t.lockedTitle,
      message: t.lockedMessage(name: holder.name, orcid: holder.orcid),
    );
  }

  Future<void> _renewLock() async {
    final holder = await _repository.lock();
    if (holder == null || !mounted) {
      return;
    }
    _renewTimer!.cancel();
    _renewTimer = null;
    _draft.cancel();
    final t = Translations.of(context).ui.lock;
    await showMessageDialog(
      context,
      title: t.lostTitle,
      message: t.lostMessage,
    );
  }

  void _releaseLock() {
    _renewTimer!.cancel();
    _renewTimer = null;
    unawaited(_repository.unlock());
  }

  Future<bool> _confirmDiscard() async {
    if (!_draft.changed) {
      return true;
    }
    final t = Translations.of(context).ui.entity;
    return showConfirmDialog(
      context,
      title: t.unsavedTitle,
      message: t.unsavedMessage,
      confirmLabel: t.discardChanges,
      destructive: true,
    );
  }

  Future<void> _cancel() async {
    if (await _confirmDiscard() && mounted) {
      _draft.cancel();
      _releaseLock();
    }
  }

  Future<void> _save() async {
    final t = Translations.of(context).ui.settings;
    late final SaveResult result;
    final ok = await runWithProgress(
      context,
      message: t.saving,
      action: () async {
        result = await _repository.save(_draft.settings);
      },
    );
    if (!ok || !mounted) {
      return;
    }
    switch (result) {
      case HeldBy(:final holder):
        _renewTimer!.cancel();
        _renewTimer = null;
        _draft.cancel();
        await _showHeldBy(holder);
      case Rejected(:final issues):
        _draft.setIssues(issues);
        await showMessageDialog(
          context,
          title: t.invalid,
          message: t.invalidMessage,
        );
      case Saved(:final revision, reloading: true):
        _draft.markSaved();
        _releaseLock();
        await _awaitReload(revision);
      case Saved(reloading: false):
        _draft.markSaved();
        _releaseLock();
        await showMessageDialog(
          context,
          title: t.saved,
          message: t.restartNeeded,
        );
    }
  }

  /// The new workers report [revision] once they run on the saved
  /// configuration; reloading the page then picks up its forms and labels.
  Future<void> _awaitReload(String revision) async {
    final t = Translations.of(context).ui.settings;
    final session = ref.read(sessionProvider.notifier);
    var reloaded = false;
    await runWithProgress(
      context,
      message: t.applying,
      action: () async {
        for (var attempt = 0; attempt < _reloadAttempts; attempt++) {
          await Future<void>.delayed(reloadPollInterval);
          if (!mounted) {
            return;
          }
          try {
            await session.refresh();
          } on NetworkException {
            continue;
          } on ApiException {
            continue;
          }
          if (ref.read(sessionProvider).value!.configurationRevision ==
              revision) {
            reloaded = true;
            return;
          }
        }
      },
    );
    if (!mounted) {
      return;
    }
    if (reloaded) {
      navigateExternally(settingsPath);
    } else {
      await showMessageDialog(
        context,
        title: t.saved,
        message: t.reloadTimeout,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context).ui.settings;
    final session = ref.watch(sessionProvider).value!;
    final margin = pageMargin(context);
    return ListenableBuilder(
      listenable: _draft,
      builder: (context, _) {
        final actions = PageActionBar(
          pinned: _draft.editing,
          children: _draft.editing
              ? [
                  AppButton(
                    variant: AppButtonVariant.tinted,
                    icon: CupertinoIcons.xmark,
                    label: Translations.of(context).ui.actions.cancel,
                    onPressed: _cancel,
                  ),
                  AppButton(
                    variant: AppButtonVariant.filled,
                    icon: CupertinoIcons.checkmark,
                    label: Translations.of(context).ui.actions.save,
                    onPressed:
                        (_draft.changed || session.setupRequired) &&
                            !_draft.hasUnreadableInput
                        ? _save
                        : null,
                  ),
                ]
              : [
                  AppButton(
                    variant: AppButtonVariant.tinted,
                    icon: CupertinoIcons.pencil,
                    label: Translations.of(context).ui.actions.edit,
                    onPressed: _startEditing,
                  ),
                ],
        );
        return CustomScrollView(
          slivers: [
            SliverPadding(
              padding: margin.copyWith(bottom: appInputSpacing),
              sliver: const SliverToBoxAdapter(
                child: SettingsHeader(tab: SettingsTab.system),
              ),
            ),
            if (_draft.editing)
              PinnedHeaderSliver(child: actions)
            else
              SliverToBoxAdapter(child: actions),
            SliverPadding(
              padding: margin.copyWith(top: appSectionSpacing),
              sliver: SliverToBoxAdapter(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  spacing: appSectionSpacing,
                  children: [
                    if (session.setupRequired)
                      AppBanner(
                        text: session.setupError == null
                            ? t.setupBanner
                            : t.setupError(error: session.setupError!),
                        icon: CupertinoIcons.wrench,
                        error: session.setupError != null,
                      ),
                    SystemSettingsForm(
                      key: ObjectKey(_draft.settings),
                      draft: _draft,
                    ),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

/// The page title and the tabs, shared by the system settings and the page of
/// the configuration root. During setup only the system settings are reachable.
class SettingsHeader extends ConsumerWidget {
  const SettingsHeader({required this.tab, super.key});

  final SettingsTab tab;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context).ui.settings;
    final session = ref.watch(sessionProvider).value!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      spacing: appSectionSpacing,
      children: [
        AppHeading(t.title, style: AppTextStyles.of(context).pageTitle),
        if (!session.setupRequired)
          SelectionContainer.disabled(
            child: CupertinoSlidingSegmentedControl<SettingsTab>(
              groupValue: tab,
              onValueChanged: (selected) => context.go(switch (selected!) {
                SettingsTab.system => settingsPath,
                SettingsTab.types => EntityStore.configuration.entityPath(
                  configurationRoot,
                ),
              }),
              children: {
                SettingsTab.system: _TabLabel(t.tabs.system),
                SettingsTab.types: _TabLabel(t.tabs.types),
              },
            ),
          ),
      ],
    );
  }
}

class _TabLabel extends StatelessWidget {
  const _TabLabel(this.label);

  final String label;

  // Brings the control to the 32 pt height of the UIKit segmented control.
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Text(label),
  );
}
