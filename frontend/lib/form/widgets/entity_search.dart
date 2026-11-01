// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../common/async_view.dart';
import '../../common/reference_views.dart';
import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../../navigation/app_paths.dart';
import '../field_def.dart';
import '../form_model.dart';
import '../form_repository.dart';

List<ContextConstraint> contextConstraints(EntityNode node, FormItem current) =>
    [
      for (final group in node.groups)
        if (group.def.uri != rdfType)
          for (final item in group.items)
            if (item != current &&
                item is! NestedItem &&
                item is! OrItem &&
                !item.isEmpty)
              ContextConstraint(
                predicate: group.def.uri,
                value: item.textValue!,
                datatype: item is DateItem
                    ? item.datatype
                    : group.def.datatypes.firstOrNull,
              ),
    ];

/// Decorates a literal field with entity search. Inside a nested entity the
/// results can replace the entity with an existing one; at the top level they
/// only warn about similar entities.
class EntitySearchField extends ConsumerStatefulWidget {
  const EntitySearchField({required this.item, required this.field, super.key});

  final LiteralItem item;
  final Widget field;

  @override
  ConsumerState<EntitySearchField> createState() => _EntitySearchFieldState();
}

class _EntitySearchFieldState extends ConsumerState<EntitySearchField> {
  Timer? _debounce;
  String _term = '';
  List<SearchResult> _results = [];
  bool _hasMore = false;
  bool _loading = false;
  ({Object error, int offset})? _failure;
  bool _dismissed = false;
  int _offset = 0;

  EntityNode get _node => widget.item.group.owner;

  bool get _suggestionsOnly =>
      _node.depth == 0 ||
      (_node.depth == 1 && widget.item.def.searchTarget == 'parent');

  bool get _parentTarget =>
      widget.item.def.searchTarget == 'parent' && _node.depth >= 1;

  @override
  void initState() {
    super.initState();
    widget.item.addListener(_onChanged);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    widget.item.removeListener(_onChanged);
    super.dispose();
  }

  void _onChanged() {
    final term = widget.item.value.trim();
    if (term == _term) {
      return;
    }
    _term = term;
    _debounce?.cancel();
    setState(() {
      _results = [];
      _hasMore = false;
      _loading = false;
      _failure = null;
      _dismissed = false;
      _offset = 0;
    });
    if (term.length < widget.item.def.minCharsForSearch) {
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 300), () => _search(0));
  }

  Future<void> _search(int offset) async {
    final term = _term;
    final node = _node;
    final parent = _parentTarget;
    setState(() {
      _loading = true;
      _failure = null;
    });
    try {
      final page = await ref
          .read(formRepositoryProvider)
          .search(
            term: term,
            entityClass: parent ? node.parentEntityType : node.entityType,
            predicate: widget.item.def.uri,
            searchTarget: parent ? 'parent' : 'self',
            connectingPredicate: parent ? node.parentPredicate : null,
            context: contextConstraints(node, widget.item),
            offset: offset,
          );
      if (!mounted || term != _term) {
        return;
      }
      setState(() {
        _results = offset == 0 ? page.results : [..._results, ...page.results];
        _hasMore = page.hasMore;
        _offset = offset;
        _loading = false;
      });
    } on Exception catch (error) {
      if (mounted && term == _term) {
        setState(() {
          _loading = false;
          _failure = (error: error, offset: offset);
        });
      }
    }
  }

  void _select(SearchResult result) {
    final node = _node;
    final target = _parentTarget
        ? node.parentItem?.group.owner.parentItem
        : node.parentItem;
    target?.selectExisting(result.uri, result.label);
    if (target != null) {
      Navigator.of(context).popUntil((route) {
        final dialogItem = _dialogItemOf(route);
        return dialogItem == null || !_isWithin(dialogItem, target);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final showResults =
        !_dismissed && (_loading || _failure != null || _results.isNotEmpty);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        widget.field,
        if (showResults)
          Padding(
            padding: const EdgeInsets.only(top: appInputSpacing / 2),
            child: AppSection(
              children: [
                if (_suggestionsOnly)
                  CupertinoListTile(
                    leading: const Icon(
                      CupertinoIcons.info_circle,
                      color: AppColors.primary,
                    ),
                    title: Text(
                      t.ui.form.similarEntities(count: _results.length),
                    ),
                    trailing: AppIconButton(
                      label: t.ui.actions.close,
                      onPressed: () => setState(() => _dismissed = true),
                      icon: CupertinoIcons.xmark,
                    ),
                  )
                else
                  CupertinoListTile(
                    leading: const Icon(CupertinoIcons.add_circled),
                    title: Text(t.ui.form.createNewEntity),
                    onTap: () => setState(() => _dismissed = true),
                  ),
                for (final result in _results)
                  AppListTile(
                    title: TileText(result.label),
                    subtitle: Text(result.uri),
                    trailing: _suggestionsOnly
                        ? CupertinoButton(
                            sizeStyle: CupertinoButtonSize.small,
                            onPressed: () =>
                                openExternal(entityPath(result.uri)),
                            child: Text(t.ui.form.view),
                          )
                        : const CupertinoListTileChevron(),
                    onTap: _suggestionsOnly ? null : () => _select(result),
                  ),
                if (_loading)
                  const Padding(
                    padding: EdgeInsets.all(appInputSpacing),
                    child: Center(child: CupertinoActivityIndicator()),
                  )
                else if (_failure case (:final error, :final offset))
                  Padding(
                    padding: const EdgeInsets.all(appInputSpacing),
                    child: ErrorView(
                      error: error,
                      onRetry: () => _search(offset),
                    ),
                  )
                else if (_hasMore && !_suggestionsOnly)
                  CupertinoListTile(
                    leading: const Icon(CupertinoIcons.refresh),
                    title: Text(t.ui.form.moreResults),
                    onTap: () => _search(_offset + 5),
                  ),
              ],
            ),
          ),
      ],
    );
  }
}

NestedItem? _dialogItemOf(Route<dynamic> route) {
  final settings = route.settings;
  return settings.arguments is NestedItem
      ? settings.arguments as NestedItem
      : null;
}

bool _isWithin(NestedItem candidate, NestedItem ancestor) {
  NestedItem? current = candidate;
  while (current != null) {
    if (current == ancestor) {
      return true;
    }
    current = current.group.owner.parentItem;
  }
  return false;
}
