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
import '../history/history_repository.dart';
import '../history/history_widgets.dart';
import 'catalogue_models.dart' as models;
import 'catalogue_repository.dart';

class CataloguePage extends ConsumerWidget {
  const CataloguePage({
    required this.recycleBin,
    required this.query,
    super.key,
  });

  final bool recycleBin;
  final Map<String, String> query;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final catalogueQuery = CatalogueQuery.fromParams(
      recycleBin: recycleBin,
      params: query,
    );
    final page = ref.watch(cataloguePageProvider(catalogueQuery));

    String location(CatalogueQuery next) => Uri(
      path: recycleBin ? recycleBinPath : cataloguePath,
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
          child: AppHeading(
            recycleBin ? t.ui.catalogue.recycleBinTitle : t.ui.catalogue.title,
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
                recycleBin: recycleBin,
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
    required this.recycleBin,
    required this.onQueryChanged,
    required this.query,
  });

  final models.CataloguePage data;
  final bool recycleBin;
  final ValueChanged<CatalogueQuery> onQueryChanged;
  final CatalogueQuery query;

  @override
  ConsumerState<_CatalogueBody> createState() => _CatalogueBodyState();
}

/// Shows the first page and loads the next ones as the list nears its end.
class _CatalogueBodyState extends ConsumerState<_CatalogueBody> {
  bool _classesAscending = true;
  final _scroll = ScrollController();
  late List<models.CatalogueEntity> _entities = [...widget.data.entities];
  late int _loadedPage = widget.data.currentPage;
  bool _loadingMore = false;
  Object? _loadError;

  bool get _hasMore => _loadedPage < widget.data.totalPages;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_maybeLoadMore);
    WidgetsBinding.instance.addPostFrameCallback((_) => _maybeLoadMore());
  }

  @override
  void didUpdateWidget(_CatalogueBody oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data != widget.data) {
      _entities = [...widget.data.entities];
      _loadedPage = widget.data.currentPage;
      _loadError = null;
      WidgetsBinding.instance.addPostFrameCallback((_) => _maybeLoadMore());
    }
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  void _maybeLoadMore() {
    if (!mounted ||
        _loadingMore ||
        _loadError != null ||
        !_hasMore ||
        !_scroll.hasClients ||
        _scroll.position.extentAfter > 600) {
      return;
    }
    _loadMore();
  }

  Future<void> _loadMore() async {
    final data = widget.data;
    setState(() {
      _loadingMore = true;
      _loadError = null;
    });
    try {
      final next = await ref
          .read(catalogueRepositoryProvider)
          .fetch(
            widget.query.copyWith(
              entityClass: data.selectedClass,
              shape: data.selectedShape,
              page: _loadedPage + 1,
            ),
          );
      if (mounted && data == widget.data) {
        _entities.addAll(next.entities);
        _loadedPage = next.currentPage;
      }
    } on Exception catch (error) {
      if (mounted && data == widget.data) {
        _loadError = error;
      }
    }
    if (!mounted) {
      return;
    }
    setState(() => _loadingMore = false);
    WidgetsBinding.instance.addPostFrameCallback((_) => _maybeLoadMore());
  }

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
      ),
    );
    final selectedIndex = classes.indexWhere(
      (item) =>
          item.uri == data.selectedClass &&
          (item.shape ?? '') == (data.selectedShape ?? ''),
    );
    final entities = _EntityList(
      data: data,
      entities: _entities,
      loadingMore: _loadingMore,
      loadError: _loadError,
      onRetry: _loadMore,
      recycleBin: widget.recycleBin,
      query: widget.query,
      onQueryChanged: widget.onQueryChanged,
    );
    final margin = pageMargin(context).copyWith(top: 0);
    if (data.availableClasses.isEmpty) {
      return Padding(
        padding: margin,
        child: Text(
          widget.recycleBin ? t.ui.recycleBin.empty : t.ui.catalogue.noClasses,
        ),
      );
    }
    if (!wide) {
      return ListView(
        controller: _scroll,
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
            controller: _scroll,
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
    required this.entities,
    required this.loadingMore,
    required this.loadError,
    required this.onRetry,
    required this.recycleBin,
    required this.query,
    required this.onQueryChanged,
  });

  final models.CataloguePage data;
  final List<models.CatalogueEntity> entities;
  final bool loadingMore;
  final Object? loadError;
  final VoidCallback onRetry;
  final bool recycleBin;
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
              query.copyWith(sortProperty: property, sortDirection: direction),
            ),
          ),
          const SizedBox(height: appInputSpacing),
        ],
        if (entities.isEmpty)
          Padding(
            padding: const EdgeInsets.all(appCardPadding),
            child: Text(t.ui.catalogue.noEntities),
          )
        else
          AppSection(
            children: [
              for (final entity in entities)
                recycleBin
                    ? _RecycleBinTile(entity: entity)
                    : AppListTile(
                        title: TileText(entity.label),
                        trailing: const CupertinoListTileChevron(),
                        onTap: () => context.go(entityPath(entity.uri)),
                      ),
            ],
          ),
        if (loadingMore)
          const Padding(
            padding: EdgeInsets.all(appSectionSpacing),
            child: Center(child: CupertinoActivityIndicator()),
          )
        else if (loadError != null)
          Padding(
            padding: const EdgeInsets.all(appSectionSpacing),
            child: ErrorView(error: loadError!, onRetry: onRetry),
          ),
      ],
    );
  }
}

class _RecycleBinTile extends ConsumerWidget {
  const _RecycleBinTile({required this.entity});

  final models.CatalogueEntity entity;

  models.Deletion get deletion => entity.deletion!;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final styles = AppTextStyles.of(context);
    return SizedBox(
      width: double.infinity,
      child: Padding(
        padding: const EdgeInsets.all(appCardPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(entity.label, style: styles.heading),
            const SizedBox(height: 4),
            Text(deletion.type, style: styles.secondary),
            const SizedBox(height: appInputSpacing),
            Text(
              t.ui.recycleBin.deletedOn(time: formatTimestamp(deletion.time)),
              style: styles.secondary,
            ),
            const SizedBox(height: 4),
            Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(t.ui.recycleBin.deletedBy, style: styles.secondary),
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
                    entityVersionPath(
                      entity.uri,
                      deletion.lastValidSnapshotTime,
                    ),
                  ),
                  label: t.ui.recycleBin.viewLastVersion,
                ),
                AppButton(
                  variant: AppButtonVariant.filled,
                  icon: CupertinoIcons.arrow_counterclockwise,
                  label: t.ui.recycleBin.restore,
                  onPressed: () => _restore(context, ref),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _restore(BuildContext context, WidgetRef ref) async {
    final t = Translations.of(context);
    final confirmed = await showConfirmDialog(
      context,
      title: t.ui.recycleBin.restoreTitle,
      message: t.ui.recycleBin.restoreMessage(label: entity.label),
      confirmLabel: t.ui.recycleBin.restore,
    );
    if (!confirmed || !context.mounted) {
      return;
    }
    final ok = await runWithProgress(
      context,
      message: t.ui.recycleBin.restoring,
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
