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
import '../navigation/entity_store.dart';
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
  const EntityPage({required this.uri, this.header, super.key});

  final String uri;

  /// Shown in place of the entity title.
  final Widget? header;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final view = ref.watch(entityViewProvider(uri));
    return AsyncView(
      value: view,
      onRetry: () => ref.invalidate(entityViewProvider(uri)),
      header: header,
      builder: (data) => switch (data.type) {
        null => _UntypedEntityBody(key: ValueKey(data), view: data),
        final type => _EntityBody(
          key: ValueKey(data),
          view: data,
          type: type,
          header: header,
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
    required this.header,
    required this.onReload,
    super.key,
  });

  final EntityView view;
  final String type;
  final Widget? header;
  final VoidCallback onReload;

  @override
  ConsumerState<_EntityBody> createState() => _EntityBodyState();
}

class _EntityBodyState extends ConsumerState<_EntityBody> {
  late final EditSession _session;
  late final FormScopeController _scope;
  // Linked and similar resources exist only among the dataset's entities.
  PagedResources<LinkedResource>? _linked;
  PagedResources<SimilarResource>? _similar;
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
    if (ref.read(entityStoreProvider) != EntityStore.dataset) {
      return;
    }
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
    _linked?.dispose();
    _similar?.dispose();
    super.dispose();
  }

  bool get _canEdit => !widget.view.isDeleted && widget.view.groups.isNotEmpty;

  // Deleting the configuration, or a part of it, is not offered yet.
  bool get _canDelete =>
      _canEdit && ref.read(entityStoreProvider) == EntityStore.dataset;

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
    final List<String> linkedUris;
    if (_linked case final linked?) {
      await linked.whenLoaded;
      linkedUris = linked.items.map((r) => r.subject).toList();
    } else {
      linkedUris = const [];
    }
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
      Router.neglect(context, () => context.go(cataloguePath));
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
          final margin = pageMargin(context);
          final actions = PageActionBar(
            pinned: editing,
            children: editing
                ? [
                    AppButton(
                      variant: AppButtonVariant.tinted,
                      onPressed: _session.status == EditStatus.saving
                          ? null
                          : _toggleEditing,
                      icon: CupertinoIcons.xmark,
                      label: t.ui.actions.cancel,
                    ),
                    AppButton(
                      variant: AppButtonVariant.filled,
                      onPressed:
                          _session.hasChanges &&
                              _session.status != EditStatus.saving
                          ? _save
                          : null,
                      icon: CupertinoIcons.checkmark,
                      label: t.ui.actions.save,
                    ),
                  ]
                : [
                    if (_canEdit)
                      AppButton(
                        variant: AppButtonVariant.tinted,
                        onPressed: _session.status == EditStatus.starting
                            ? null
                            : _toggleEditing,
                        icon: CupertinoIcons.pencil,
                        label: t.ui.actions.edit,
                      ),
                    if (view.hasHistory) _TimeMachineButton(uri: view.uri),
                  ],
          );
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: CustomScrollView(
                  slivers: [
                    SliverPadding(
                      padding: margin.copyWith(bottom: appInputSpacing),
                      sliver: SliverToBoxAdapter(
                        child: widget.header ?? _EntityTitle(label: view.label),
                      ),
                    ),
                    if (editing)
                      PinnedHeaderSliver(child: actions)
                    else
                      SliverToBoxAdapter(child: actions),
                    SliverPadding(
                      padding: margin.copyWith(
                        top: appInputSpacing,
                        bottom: appSectionSpacing,
                      ),
                      sliver: SliverToBoxAdapter(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          spacing: appPartSpacing,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              spacing: appSectionSpacing,
                              children: [
                                if (view.isDeleted)
                                  AppBanner(text: t.ui.entity.deletedBanner)
                                else if (view.groups.isEmpty)
                                  AppBanner(text: t.ui.entity.noInformation)
                                else
                                  for (final group in _session.groups)
                                    if (group.group.isShown &&
                                        (group.group.triples.isNotEmpty ||
                                            (group.group.field?.isBoolean ??
                                                false) ||
                                            (editing &&
                                                view.canBeAdded.contains(
                                                  group.group.property,
                                                ) &&
                                                group.formGroup != null)))
                                      EditableGroupWidget(
                                        group: group,
                                        view: view,
                                        editing: editing,
                                      ),
                                if (editing && _session.showsCustomProperties)
                                  CustomPropertiesForm(
                                    controller: _session.customProperties,
                                    datatypeOptions: ref
                                        .read(sessionProvider)
                                        .value!
                                        .config!
                                        .datatypeOptions,
                                  ),
                              ],
                            ),
                            if (_linked case final linked?)
                              _LinkedResourcesSection(resources: linked),
                            if (_similar case final similar?)
                              ResourceListSection(
                                title: t.ui.entity.similarResources,
                                emptyMessage: t.ui.entity.noSimilarResources,
                                resources: similar,
                                itemBuilder: (resource) => SimilarResourceTile(
                                  resource: resource,
                                  subject: view.uri,
                                ),
                              ),
                            if (_canDelete && !editing)
                              AppSection(
                                children: [
                                  AppListTile(
                                    title: IconLabel(
                                      icon: CupertinoIcons.delete,
                                      color: AppColors.of(context).error,
                                      label: Text(t.ui.entity.delete),
                                      style: TextStyle(
                                        color: AppColors.of(context).error,
                                      ),
                                    ),
                                    onTap: _deleteEntity,
                                  ),
                                ],
                              ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              if (editing)
                Padding(
                  padding: pageMargin(context).copyWith(top: 0),
                  child: const ValidationSummary(),
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
  Widget build(BuildContext context) =>
      AppHeading(label, style: AppTextStyles.of(context).sectionTitle);
}

class _TimeMachineButton extends StatelessWidget {
  const _TimeMachineButton({required this.uri});

  final String uri;

  @override
  Widget build(BuildContext context) => AppButton(
    variant: AppButtonVariant.tinted,
    onPressed: () => context.go(context.entityStore.historyPath(uri)),
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
