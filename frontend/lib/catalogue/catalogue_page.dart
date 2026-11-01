// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../common/async_view.dart';
import '../common/dialogs.dart';
import '../common/reference_views.dart';
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
        Text(
          timeVault ? t.ui.catalogue.timeVaultTitle : t.ui.catalogue.title,
          style: Theme.of(context).textTheme.headlineMedium,
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
    if (data.availableClasses.isEmpty) {
      return Text(
        widget.timeVault ? t.ui.timeVault.empty : t.ui.catalogue.noClasses,
      );
    }
    if (!wide) {
      return ListView(
        children: [
          DropdownButtonFormField<int>(
            key: ValueKey(selectedIndex),
            initialValue: selectedIndex < 0 ? null : selectedIndex,
            isExpanded: true,
            decoration: InputDecoration(
              labelText: t.ui.catalogue.categories,
              border: const OutlineInputBorder(),
            ),
            items: [
              for (final (index, item) in classes.indexed)
                DropdownMenuItem(
                  value: index,
                  child: Text('${item.label} (${item.count})'),
                ),
            ],
            onChanged: (index) => select(classes[index!]),
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
          width: 320,
          child: SingleChildScrollView(
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
        const SizedBox(width: appSectionSpacing),
        Expanded(child: SingleChildScrollView(child: entities)),
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
    final colorScheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(appCardPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  t.ui.catalogue.categories,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                IconButton(
                  tooltip: ascending
                      ? t.ui.catalogue.sortDescending
                      : t.ui.catalogue.sortAscending,
                  onPressed: onToggleOrder,
                  icon: Icon(
                    ascending ? Icons.arrow_downward : Icons.arrow_upward,
                  ),
                ),
              ],
            ),
            for (final (index, item) in classes.indexed)
              ListTile(
                dense: true,
                selected: index == selectedIndex,
                selectedTileColor: colorScheme.primaryContainer,
                title: Text(item.label),
                trailing: Text(item.count),
                onTap: () => onSelect(item),
              ),
          ],
        ),
      ),
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
        if (data.entities.isEmpty)
          Padding(
            padding: const EdgeInsets.all(appCardPadding),
            child: Text(t.ui.catalogue.noEntities),
          )
        else
          Card(
            child: Column(
              children: [
                for (final entity in data.entities)
                  timeVault
                      ? _TimeVaultTile(entity: entity)
                      : ListTile(
                          title: Text(entity.label),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => context.go(entityPath(entity.uri)),
                        ),
              ],
            ),
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
    final textTheme = Theme.of(context).textTheme;
    return ListTile(
      title: Text(entity.label),
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(deletion.type),
          Text(
            t.ui.timeVault.deletedOn(time: formatTimestamp(deletion.time)),
            style: textTheme.bodySmall,
          ),
          Row(
            children: [
              Text(t.ui.timeVault.deletedBy, style: textTheme.bodySmall),
              const SizedBox(width: 4),
              AgentRefView(agent: deletion.deletedBy),
            ],
          ),
        ],
      ),
      trailing: Wrap(
        spacing: appInputSpacing / 2,
        children: [
          OutlinedButton(
            onPressed: () => context.go(
              entityVersionPath(entity.uri, deletion.lastValidSnapshotTime),
            ),
            child: Text(t.ui.timeVault.viewLastVersion),
          ),
          FilledButton.icon(
            icon: const Icon(Icons.restore),
            label: Text(t.ui.timeVault.restore),
            onPressed: () => _restore(context, ref),
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
    if (properties.isEmpty) {
      return const SizedBox.shrink();
    }
    final current = currentProperty!;
    return Row(
      children: [
        Text(t.ui.catalogue.sortBy),
        const SizedBox(width: appInputSpacing),
        DropdownButton<String>(
          value: current,
          items: [
            for (final property in properties)
              DropdownMenuItem(
                value: property.property,
                child: Text(property.displayName),
              ),
          ],
          onChanged: (value) => onChanged(value!, currentDirection),
        ),
        const SizedBox(width: appInputSpacing),
        IconButton(
          tooltip: currentDirection == 'ASC'
              ? t.ui.catalogue.sortAscending
              : t.ui.catalogue.sortDescending,
          onPressed: () =>
              onChanged(current, currentDirection == 'ASC' ? 'DESC' : 'ASC'),
          icon: Icon(
            currentDirection == 'ASC'
                ? Icons.arrow_upward
                : Icons.arrow_downward,
          ),
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
            DropdownButton<int>(
              value: allowedPerPage.contains(perPage)
                  ? perPage
                  : allowedPerPage.first,
              items: [
                for (final value in allowedPerPage)
                  DropdownMenuItem(value: value, child: Text('$value')),
              ],
              onChanged: (value) =>
                  value == null ? null : onPerPageChanged(value),
            ),
          ],
        ),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              tooltip: t.ui.catalogue.firstPage,
              onPressed: currentPage > 1 ? () => onPageChanged(1) : null,
              icon: const Icon(Icons.first_page),
            ),
            IconButton(
              tooltip: t.ui.catalogue.previousPage,
              onPressed: currentPage > 1
                  ? () => onPageChanged(currentPage - 1)
                  : null,
              icon: const Icon(Icons.chevron_left),
            ),
            Text(
              t.ui.catalogue.pageOf(current: currentPage, total: totalPages),
            ),
            IconButton(
              tooltip: t.ui.catalogue.nextPage,
              onPressed: currentPage < totalPages
                  ? () => onPageChanged(currentPage + 1)
                  : null,
              icon: const Icon(Icons.chevron_right),
            ),
            IconButton(
              tooltip: t.ui.catalogue.lastPage,
              onPressed: currentPage < totalPages
                  ? () => onPageChanged(totalPages)
                  : null,
              icon: const Icon(Icons.last_page),
            ),
          ],
        ),
      ],
    );
  }
}
