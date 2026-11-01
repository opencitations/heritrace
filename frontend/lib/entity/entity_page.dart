// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../common/async_view.dart';
import '../common/dialogs.dart';
import '../common/primary_source_dialog.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../form/form_scope.dart';
import '../form/widgets/custom_properties_form.dart';
import '../form/widgets/validation_summary.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
import '../navigation/leave_guard.dart';
import '../session/session_controller.dart';
import 'create_entity_page.dart';
import 'edit_session.dart';
import 'entity_models.dart';
import 'entity_repository.dart';
import 'existing_value_widgets.dart';
import 'orphan_dialog.dart';
import 'resource_lists.dart';

class EntityPage extends ConsumerWidget {
  const EntityPage({required this.uri, super.key});

  final String uri;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final view = ref.watch(entityViewProvider(uri));
    return AsyncView(
      value: view,
      onRetry: () => ref.invalidate(entityViewProvider(uri)),
      builder: (data) => switch (data.type) {
        null => _UntypedEntityBody(key: ValueKey(data), view: data),
        final type => _EntityBody(
          key: ValueKey(data),
          view: data,
          type: type,
          onReload: () => ref.invalidate(entityViewProvider(uri)),
        ),
      },
    );
  }
}

/// An entity without `rdf:type` has no shape to edit: only its references and
/// history are shown.
class _UntypedEntityBody extends ConsumerStatefulWidget {
  const _UntypedEntityBody({required this.view, super.key});

  final EntityView view;

  @override
  ConsumerState<_UntypedEntityBody> createState() => _UntypedEntityBodyState();
}

class _UntypedEntityBodyState extends ConsumerState<_UntypedEntityBody> {
  late final PagedResources<LinkedResource> _linked = PagedResources(
    (offset) => ref
        .read(entityRepositoryProvider)
        .linkedResources(widget.view.uri, offset: offset),
  )..loadMore();

  @override
  void dispose() {
    _linked.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final view = widget.view;
    return SingleChildScrollView(
      padding: pageMargin(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _EntityTitle(label: view.label),
          if (view.hasHistory) ...[
            const SizedBox(height: appSectionSpacing),
            Align(
              alignment: Alignment.centerLeft,
              child: _TimeMachineButton(uri: view.uri),
            ),
          ],
          const SizedBox(height: appSectionSpacing),
          AppBanner(
            text: view.isDeleted
                ? t.ui.entity.deletedBanner
                : t.ui.entity.noInformation,
          ),
          const SizedBox(height: appSectionSpacing * 2),
          _LinkedResourcesSection(resources: _linked),
        ],
      ),
    );
  }
}

class _EntityBody extends ConsumerStatefulWidget {
  const _EntityBody({
    required this.view,
    required this.type,
    required this.onReload,
    super.key,
  });

  final EntityView view;
  final String type;
  final VoidCallback onReload;

  @override
  ConsumerState<_EntityBody> createState() => _EntityBodyState();
}

class _EntityBodyState extends ConsumerState<_EntityBody> {
  late final EditSession _session;
  late final FormScopeController _scope;
  late final PagedResources<LinkedResource> _linked;
  late final PagedResources<SimilarResource> _similar;
  late final LeaveGuard _leaveGuard;

  @override
  void initState() {
    super.initState();
    _leaveGuard = ref.read(leaveGuardProvider)..register(_confirmDiscard);
    final repository = ref.read(entityRepositoryProvider);
    final view = widget.view;
    _session = EditSession(
      view: view,
      entityType: widget.type,
      repository: repository,
      validationMessages: validationMessages(t),
      atLeastOnePropertyMessage: t.ui.form.atLeastOneProperty,
    )..onLockLost = _onLockLost;
    _session.addListener(_revalidate);
    _scope = FormScopeController(rootLabel: view.typeLabel);
    _linked = PagedResources(
      (offset) => repository.linkedResources(view.uri, offset: offset),
    )..loadMore();
    _similar = PagedResources(
      (offset) => repository.similarResources(
        view.uri,
        entityType: widget.type,
        shape: view.shape,
        offset: offset,
      ),
    )..loadMore();
  }

  @override
  void dispose() {
    _leaveGuard.unregister(_confirmDiscard);
    _session.removeListener(_revalidate);
    _session.dispose();
    _scope.dispose();
    _linked.dispose();
    _similar.dispose();
    super.dispose();
  }

  void _revalidate() {
    if (_session.editing) {
      _scope.setErrors(_session.validate(), started: false);
    }
  }

  Future<void> _onLockLost() async {
    if (!mounted) {
      return;
    }
    final t = Translations.of(context);
    await showMessageDialog(
      context,
      title: t.ui.lock.lostTitle,
      message: t.ui.lock.lostMessage,
    );
    widget.onReload();
  }

  Future<bool> _confirmDiscard() async {
    if (!_session.editing || !_session.hasChanges) {
      return true;
    }
    final t = Translations.of(context);
    return showConfirmDialog(
      context,
      title: t.ui.entity.unsavedTitle,
      message: t.ui.entity.unsavedMessage,
      confirmLabel: t.ui.entity.discardChanges,
      destructive: true,
    );
  }

  Future<void> _toggleEditing() async {
    final t = Translations.of(context);
    if (_session.editing) {
      if (!await _confirmDiscard() || !mounted) {
        return;
      }
      _scope.reset();
      try {
        await _session.stopEditing();
      } on Exception catch (error) {
        if (mounted) {
          await showErrorDialog(context, error);
        }
      }
      return;
    }
    await _linked.whenLoaded;
    final linkedUris = _linked.items.map((r) => r.subject).toList();
    try {
      final response = await _session.startEditing(linkedUris);
      if (!mounted) {
        return;
      }
      if (response.status != 'success') {
        await showMessageDialog(
          context,
          title: response.title ?? t.ui.lock.lockedTitle,
          message: response.message ?? t.ui.lock.lockedMessage,
        );
      } else {
        _scope.reset();
      }
    } on Exception catch (error) {
      if (!mounted) {
        return;
      }
      await showErrorDialog(context, error);
      widget.onReload();
    }
  }

  Future<void> _save() async {
    final t = Translations.of(context);
    final errors = _session.validate();
    if (errors.isNotEmpty) {
      _scope.setErrors(errors);
      return;
    }
    final changes = _session.buildChanges();
    if (changes.isEmpty) {
      await showMessageDialog(
        context,
        title: t.ui.entity.noChangesTitle,
        message: t.ui.entity.noChangesMessage,
      );
      return;
    }
    final affected = await _resolveAffectedEntities(changes);
    if (affected == null || !mounted) {
      return;
    }
    final session = ref.read(sessionProvider).value!;
    final choice = await showPrimarySourceDialog(
      context,
      defaultPrimarySource: session.defaultPrimarySource,
      confirmLabel: t.ui.entity.saveChanges,
      description: t.ui.entity.primarySourceDescription,
    );
    if (choice == null || !mounted) {
      return;
    }
    changes.first.addAll({
      'affected_entities': affected.entities.map((e) => e.toJson()).toList(),
      'delete_affected': affected.delete,
      'primary_source': choice.url,
      'save_default_source': choice.saveAsDefault,
    });
    _session.setSaving(saving: true);
    final ok = await runWithProgress(
      context,
      message: t.ui.entity.applying,
      action: () => _session.repository.applyChanges(changes),
    );
    if (!mounted) {
      return;
    }
    if (!ok) {
      _session.setSaving(saving: false);
      return;
    }
    if (choice.saveAsDefault) {
      ref.read(sessionProvider.notifier).setDefaultPrimarySource(choice.url);
    }
    _session.markSaved();
    try {
      await _session.stopEditing();
    } on Exception catch (error) {
      if (mounted) {
        await showErrorDialog(context, error);
      }
    }
    widget.onReload();
  }

  Future<({List<AffectedEntity> entities, bool delete})?>
  _resolveAffectedEntities(List<Map<String, Object?>> changes) async {
    final t = Translations.of(context);
    final deletions = EditSession.deletionChanges(changes);
    if (deletions.isEmpty) {
      return (entities: <AffectedEntity>[], delete: false);
    }
    OrphanCheck? check;
    final ok = await runWithProgress(
      context,
      message: t.ui.entity.checkingDependencies,
      action: () async {
        check = await _session.repository.checkOrphans(
          changes: deletions,
          entityType: widget.type,
          entityShape: widget.view.shape,
        );
      },
    );
    if (!ok || !mounted) {
      return null;
    }
    final result = check!;
    if (result.affectedEntities.isEmpty) {
      return (entities: <AffectedEntity>[], delete: false);
    }
    if (result.shouldDelete) {
      return (entities: result.affectedEntities, delete: true);
    }
    final delete = await showOrphanDialog(context, result);
    if (delete == null) {
      return null;
    }
    return (entities: result.affectedEntities, delete: delete);
  }

  Future<void> _deleteEntity() async {
    final t = Translations.of(context);
    final confirmed = await showConfirmDialog(
      context,
      title: t.ui.entity.deleteTitle,
      message: t.ui.entity.deleteMessage,
      confirmLabel: t.ui.entity.deleteConfirm,
      destructive: true,
    );
    if (!confirmed || !mounted) {
      return;
    }
    final changes = <Map<String, Object?>>[
      {'action': 'delete', 'subject': widget.view.uri},
    ];
    final affected = await _resolveAffectedEntities(changes);
    if (affected == null || !mounted) {
      return;
    }
    changes.first.addAll({
      'affected_entities': affected.entities.map((e) => e.toJson()).toList(),
      'delete_affected': affected.delete,
    });
    final ok = await runWithProgress(
      context,
      message: t.ui.entity.applying,
      action: () => _session.repository.applyChanges(changes),
    );
    if (ok && mounted) {
      context.go(cataloguePath);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final view = widget.view;
    return FormScope(
      notifier: _scope,
      child: ListenableBuilder(
        listenable: _session,
        builder: (context, _) {
          final editing = _session.editing;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: SingleChildScrollView(
                  padding: pageMargin(context).copyWith(bottom: 0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _EntityTitle(label: view.label),
                      const SizedBox(height: appSectionSpacing),
                      Wrap(
                        spacing: appInputSpacing,
                        runSpacing: appInputSpacing,
                        children: [
                          if (!view.isDeleted && view.groups.isNotEmpty) ...[
                            AppButton(
                              variant: AppButtonVariant.tinted,
                              onPressed: _session.status == EditStatus.starting
                                  ? null
                                  : _toggleEditing,
                              icon: editing
                                  ? CupertinoIcons.xmark
                                  : CupertinoIcons.pencil,
                              label: editing
                                  ? t.ui.entity.cancelEditing
                                  : t.ui.entity.edit,
                            ),
                            AppButton(
                              variant: AppButtonVariant.tinted,
                              destructive: true,
                              onPressed: editing ? null : _deleteEntity,
                              icon: CupertinoIcons.delete,
                              label: t.ui.entity.delete,
                            ),
                          ],
                          if (view.hasHistory)
                            _TimeMachineButton(uri: view.uri),
                        ],
                      ),
                      const SizedBox(height: appSectionSpacing),
                      if (view.isDeleted)
                        AppBanner(text: t.ui.entity.deletedBanner)
                      else if (view.groups.isEmpty)
                        AppBanner(text: t.ui.entity.noInformation)
                      else
                        for (final group in _session.groups)
                          if (group.group.triples.isNotEmpty ||
                              (editing &&
                                  view.canBeAdded.contains(
                                    group.group.property,
                                  ) &&
                                  group.formGroup != null))
                            Padding(
                              padding: const EdgeInsets.only(
                                bottom: appSectionSpacing,
                              ),
                              child: EditableGroupWidget(
                                group: group,
                                view: view,
                                editing: editing,
                              ),
                            ),
                      if (editing && _session.showsCustomProperties) ...[
                        CustomPropertiesForm(
                          controller: _session.customProperties,
                          datatypeOptions: ref
                              .read(sessionProvider)
                              .value!
                              .config
                              .datatypeOptions,
                        ),
                        const SizedBox(height: appSectionSpacing),
                      ],
                      const SizedBox(height: appSectionSpacing),
                      _LinkedResourcesSection(resources: _linked),
                      const SizedBox(height: appSectionSpacing),
                      ResourceListSection(
                        title: t.ui.entity.similarResources,
                        emptyMessage: t.ui.entity.noSimilarResources,
                        resources: _similar,
                        itemBuilder: (resource) => SimilarResourceTile(
                          resource: resource,
                          subject: view.uri,
                        ),
                      ),
                      const SizedBox(height: appSectionSpacing),
                    ],
                  ),
                ),
              ),
              if (editing)
                Padding(
                  padding: pageMargin(context).copyWith(top: 0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const ValidationSummary(),
                      _SaveBar(session: _session, onSave: _save),
                    ],
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _EntityTitle extends StatelessWidget {
  const _EntityTitle({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Text(
    label,
    style: AppTextStyles.of(context).sectionTitle
        .copyWith(fontStyle: FontStyle.italic),
  );
}

class _TimeMachineButton extends StatelessWidget {
  const _TimeMachineButton({required this.uri});

  final String uri;

  @override
  Widget build(BuildContext context) => AppButton(
    variant: AppButtonVariant.tinted,
    onPressed: () => context.go(entityHistoryPath(uri)),
    icon: CupertinoIcons.clock,
    label: Translations.of(context).ui.history.title,
  );
}

class _LinkedResourcesSection extends StatelessWidget {
  const _LinkedResourcesSection({required this.resources});

  final PagedResources<LinkedResource> resources;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return ResourceListSection(
      title: t.ui.entity.linkedResources,
      emptyMessage: t.ui.entity.noLinkedResources,
      resources: resources,
      itemBuilder: (resource) => LinkedResourceTile(resource: resource),
    );
  }
}

class _SaveBar extends StatelessWidget {
  const _SaveBar({required this.session, required this.onSave});

  final EditSession session;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final scope = FormScope.of(context);
    final saving = session.status == EditStatus.saving;
    final hasChanges = session.hasChanges;
    final status = saving
        ? t.ui.entity.saving
        : hasChanges
        ? t.ui.entity.unsaved
        : session.saved
        ? t.ui.entity.saved
        : t.ui.entity.unchanged;
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(top: BorderSide(color: AppColors.separator, width: 0)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(appCardPadding),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(status),
                  if (scope.validationStarted)
                    Text(
                      scope.errors.isEmpty
                          ? t.ui.entity.readyToSave
                          : t.ui.entity.correctErrors,
                      style: TextStyle(
                        color: scope.errors.isEmpty
                            ? AppColors.primary
                            : AppColors.error,
                      ),
                    ),
                ],
              ),
            ),
            AppButton(
              variant: AppButtonVariant.filled,
              onPressed: hasChanges && !saving ? onSave : null,
              label: t.ui.entity.saveChanges,
            ),
          ],
        ),
      ),
    );
  }
}
