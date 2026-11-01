// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../common/async_view.dart';
import '../common/dialogs.dart';
import '../common/reference_views.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
import '../session/session_controller.dart';
import '../history/history_repository.dart';
import '../history/history_widgets.dart';
import 'catalogue_models.dart' as models;
import 'catalogue_repository.dart';

class CataloguePage extends ConsumerWidget {
  const CataloguePage({
    required this.timeVault,
    required this.query,
    super.key,
  });

  final bool timeVault;
  final Map<String, String> query;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final catalogueQuery = CatalogueQuery.fromParams(
      timeVault: timeVault,
      params: query,
    );
    final page = ref.watch(cataloguePageProvider(catalogueQuery));
    final allowedPerPage = ref
        .watch(sessionProvider)
        .value!
        .config
        .allowedPerPage;

    String location(CatalogueQuery next) => Uri(
      path: timeVault ? timeVaultPath : cataloguePath,
      queryParameters: next.toParams(),
    ).toString();

    void navigate(CatalogueQuery next) => context.go(location(next));

    void selectFirstClass(List<models.CatalogueClass> classes) {
      final populated = classes.where((c) => c.count != '0').toList();
      final first = (populated.isEmpty ? classes : populated).reduce(
        (a, b) =>
            a.label.toLowerCase().compareTo(b.label.toLowerCase()) <= 0 ? a : b,
      );
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => context.replace(
          location(
            catalogueQuery.copyWith(entityClass: first.uri, shape: first.shape),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: pageMargin(context).copyWith(bottom: 0),
          child: Text(
            timeVault ? t.ui.catalogue.timeVaultTitle : t.ui.catalogue.title,
            style: AppTextStyles.of(context).pageTitle,
          ),
        ),
        const SizedBox(height: appSectionSpacing),
        Expanded(
          child: AsyncView(
            value: page,
            onRetry: () =>
                ref.invalidate(cataloguePageProvider(catalogueQuery)),
            builder: (data) {
              if (data.selectedClass == null &&
                  data.availableClasses.isNotEmpty) {
                selectFirstClass(data.availableClasses);
              }
              return _CatalogueBody(
                data: data,
                timeVault: timeVault,
                allowedPerPage: allowedPerPage,
                onQueryChanged: navigate,
                query: catalogueQuery,
              );
            },
          ),
        ),
      ],
    );
  }
}

class _CatalogueBody extends ConsumerStatefulWidget {
  const _CatalogueBody({
    required this.data,
    required this.timeVault,
    required this.allowedPerPage,
    required this.onQueryChanged,
    required this.query,
  });

  final models.CataloguePage data;
  final bool timeVault;
  final List<int> allowedPerPage;
  final ValueChanged<CatalogueQuery> onQueryChanged;
  final CatalogueQuery query;

  @override
  ConsumerState<_CatalogueBody> createState() => _CatalogueBodyState();
}

class _CatalogueBodyState extends ConsumerState<_CatalogueBody> {
  bool _classesAscending = true;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final data = widget.data;
    final classes = [...data.availableClasses]
      ..sort(
        (a, b) => _classesAscending
            ? a.label.toLowerCase().compareTo(b.label.toLowerCase())
            : b.label.toLowerCase().compareTo(a.label.toLowerCase()),
      );
    final wide = MediaQuery.sizeOf(context).width > 800;
    void select(models.CatalogueClass item) => widget.onQueryChanged(
      widget.query.copyWith(
        entityClass: item.uri,
        shape: item.shape,
        resetShape: item.shape == null,
        page: 1,
      ),
    );
    final selectedIndex = classes.indexWhere(
      (item) =>
          item.uri == data.selectedClass &&
          (item.shape ?? '') == (data.selectedShape ?? ''),
    );
    final entities = _EntityList(
      data: data,
      timeVault: widget.timeVault,
      allowedPerPage: widget.allowedPerPage,
      query: widget.query,
      onQueryChanged: widget.onQueryChanged,
    );
    final margin = pageMargin(context).copyWith(top: 0);
    if (data.availableClasses.isEmpty) {
      return Padding(
        padding: margin,
        child: Text(
          widget.timeVault ? t.ui.timeVault.empty : t.ui.catalogue.noClasses,
        ),
      );
    }
    if (!wide) {
      return ListView(
        padding: margin,
        children: [
          AppLabeledField(
            label: t.ui.catalogue.categories,
            child: AppMenuButton<int?>(
              value: selectedIndex < 0 ? null : selectedIndex,
              options: [
                for (final (index, item) in classes.indexed)
                  AppMenuOption(index, '${item.label} (${item.count})'),
              ],
              onChanged: (index) => select(classes[index!]),
            ),
          ),
          const SizedBox(height: appSectionSpacing),
          entities,
        ],
      );
    }
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 320 + margin.left + appSectionSpacing / 2,
          child: SingleChildScrollView(
            padding: margin.copyWith(right: appSectionSpacing / 2),
            child: _ClassList(
              classes: classes,
              selectedIndex: selectedIndex,
              ascending: _classesAscending,
              onToggleOrder: () =>
                  setState(() => _classesAscending = !_classesAscending),
              onSelect: select,
            ),
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: margin.copyWith(left: appSectionSpacing / 2),
            child: entities,
          ),
        ),
      ],
    );
  }
}

class _ClassList extends StatelessWidget {
  const _ClassList({
    required this.classes,
    required this.selectedIndex,
    required this.ascending,
    required this.onToggleOrder,
    required this.onSelect,
  });

  final List<models.CatalogueClass> classes;
  final int selectedIndex;
  final bool ascending;
  final VoidCallback onToggleOrder;
  final ValueChanged<models.CatalogueClass> onSelect;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return AppSection(
      children: [
        CupertinoListTile(
          title: Text(
            t.ui.catalogue.categories,
            style: AppTextStyles.of(context).heading,
          ),
          trailing: AppIconButton(
            label: ascending
                ? t.ui.catalogue.sortDescending
                : t.ui.catalogue.sortAscending,
            onPressed: onToggleOrder,
            icon: ascending
                ? CupertinoIcons.arrow_down
                : CupertinoIcons.arrow_up,
          ),
        ),
        for (final (index, item) in classes.indexed)
          SelectionContainer.disabled(
            child: CupertinoListTile(
              backgroundColor: index == selectedIndex
                  ? AppColors.primaryTint
                  : null,
              title: Text(
                item.label,
                style: index == selectedIndex
                    ? const TextStyle(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w600,
                      )
                    : null,
              ),
              additionalInfo: Text(item.count),
              onTap: () => onSelect(item),
            ),
          ),
      ],
    );
  }
}

class _EntityList extends ConsumerWidget {
  const _EntityList({
    required this.data,
    required this.timeVault,
    required this.allowedPerPage,
    required this.query,
    required this.onQueryChanged,
  });

  final models.CataloguePage data;
  final bool timeVault;
  final List<int> allowedPerPage;
  final CatalogueQuery query;
  final ValueChanged<CatalogueQuery> onQueryChanged;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (data.sortableProperties.isNotEmpty) ...[
          _SortControls(
            properties: data.sortableProperties,
            currentProperty: data.sortProperty,
            currentDirection: data.sortDirection,
            onChanged: (property, direction) => onQueryChanged(
              query.copyWith(
                sortProperty: property,
                sortDirection: direction,
                page: 1,
              ),
            ),
          ),
          const SizedBox(height: appInputSpacing),
        ],
        if (data.entities.isEmpty)
          Padding(
            padding: const EdgeInsets.all(appCardPadding),
            child: Text(t.ui.catalogue.noEntities),
          )
        else
          AppSection(
            children: [
              for (final entity in data.entities)
                timeVault
                    ? _TimeVaultTile(entity: entity)
                    : AppListTile(
                        title: TileText(entity.label),
                        trailing: const CupertinoListTileChevron(),
                        onTap: () => context.go(entityPath(entity.uri)),
                      ),
            ],
          ),
        if (data.entities.isNotEmpty) ...[
          const SizedBox(height: appInputSpacing),
          _PaginationControls(
            currentPage: data.currentPage,
            totalPages: data.totalPages,
            perPage: data.perPage,
            allowedPerPage: allowedPerPage,
            onPageChanged: (page) => onQueryChanged(query.copyWith(page: page)),
            onPerPageChanged: (perPage) =>
                onQueryChanged(query.copyWith(perPage: perPage, page: 1)),
          ),
        ],
      ],
    );
  }
}

class _TimeVaultTile extends ConsumerWidget {
  const _TimeVaultTile({required this.entity});

  final models.CatalogueEntity entity;

  models.Deletion get deletion => entity.deletion!;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final styles = AppTextStyles.of(context);
    return Padding(
      padding: const EdgeInsets.all(appCardPadding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(entity.label, style: styles.heading),
          const SizedBox(height: 4),
          Text(deletion.type, style: styles.secondary),
          const SizedBox(height: appInputSpacing),
          Text(
            t.ui.timeVault.deletedOn(time: formatTimestamp(deletion.time)),
            style: styles.secondary,
          ),
          const SizedBox(height: 4),
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(t.ui.timeVault.deletedBy, style: styles.secondary),
              const SizedBox(width: 4),
              AgentRefView(agent: deletion.deletedBy),
            ],
          ),
          const SizedBox(height: appInputSpacing),
          Wrap(
            spacing: appInputSpacing / 2,
            runSpacing: appInputSpacing / 2,
            children: [
              AppButton(
                variant: AppButtonVariant.tinted,
                onPressed: () => context.go(
                  entityVersionPath(entity.uri, deletion.lastValidSnapshotTime),
                ),
                label: t.ui.timeVault.viewLastVersion,
              ),
              AppButton(
                variant: AppButtonVariant.filled,
                icon: CupertinoIcons.arrow_counterclockwise,
                label: t.ui.timeVault.restore,
                onPressed: () => _restore(context, ref),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _restore(BuildContext context, WidgetRef ref) async {
    final t = Translations.of(context);
    final confirmed = await showConfirmDialog(
      context,
      title: t.ui.timeVault.restoreTitle,
      message: t.ui.timeVault.restoreMessage(label: entity.label),
      confirmLabel: t.ui.timeVault.restore,
    );
    if (!confirmed || !context.mounted) {
      return;
    }
    final ok = await runWithProgress(
      context,
      message: t.ui.timeVault.restoring,
      action: () => ref
          .read(historyRepositoryProvider)
          .restore(entity.uri, deletion.lastValidSnapshotTime),
    );
    if (ok && context.mounted) {
      context.go(entityPath(entity.uri));
    }
  }
}

class _SortControls extends StatelessWidget {
  const _SortControls({
    required this.properties,
    required this.currentProperty,
    required this.currentDirection,
    required this.onChanged,
  });

  final List<models.SortableProperty> properties;
  final String? currentProperty;
  final String currentDirection;
  final void Function(String property, String direction) onChanged;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final current = currentProperty!;
    return Row(
      children: [
        Text(t.ui.catalogue.sortBy),
        const SizedBox(width: appInputSpacing),
        Flexible(
          child: AppMenuButton<String>(
            value: current,
            options: [
              for (final property in properties)
                AppMenuOption(property.property, property.displayName),
            ],
            onChanged: (value) => onChanged(value, currentDirection),
          ),
        ),
        AppIconButton(
          label: currentDirection == 'ASC'
              ? t.ui.catalogue.sortAscending
              : t.ui.catalogue.sortDescending,
          onPressed: () =>
              onChanged(current, currentDirection == 'ASC' ? 'DESC' : 'ASC'),
          icon: currentDirection == 'ASC'
              ? CupertinoIcons.arrow_up
              : CupertinoIcons.arrow_down,
        ),
      ],
    );
  }
}

class _PaginationControls extends StatelessWidget {
  const _PaginationControls({
    required this.currentPage,
    required this.totalPages,
    required this.perPage,
    required this.allowedPerPage,
    required this.onPageChanged,
    required this.onPerPageChanged,
  });

  final int currentPage;
  final int totalPages;
  final int perPage;
  final List<int> allowedPerPage;
  final ValueChanged<int> onPageChanged;
  final ValueChanged<int> onPerPageChanged;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return Wrap(
      spacing: appInputSpacing,
      runSpacing: appInputSpacing,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(t.ui.catalogue.perPage),
            const SizedBox(width: appInputSpacing),
            AppMenuButton<int>(
              value: allowedPerPage.contains(perPage)
                  ? perPage
                  : allowedPerPage.first,
              options: [
                for (final value in allowedPerPage)
                  AppMenuOption(value, '$value'),
              ],
              onChanged: onPerPageChanged,
            ),
          ],
        ),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppIconButton(
              label: t.ui.catalogue.firstPage,
              onPressed: currentPage > 1 ? () => onPageChanged(1) : null,
              icon: CupertinoIcons.backward_end,
            ),
            AppIconButton(
              label: t.ui.catalogue.previousPage,
              onPressed: currentPage > 1
                  ? () => onPageChanged(currentPage - 1)
                  : null,
              icon: CupertinoIcons.chevron_left,
            ),
            Text(
              t.ui.catalogue.pageOf(current: currentPage, total: totalPages),
            ),
            AppIconButton(
              label: t.ui.catalogue.nextPage,
              onPressed: currentPage < totalPages
                  ? () => onPageChanged(currentPage + 1)
                  : null,
              icon: CupertinoIcons.chevron_right,
            ),
            AppIconButton(
              label: t.ui.catalogue.lastPage,
              onPressed: currentPage < totalPages
                  ? () => onPageChanged(totalPages)
                  : null,
              icon: CupertinoIcons.forward_end,
            ),
          ],
        ),
      ],
    );
  }
}
