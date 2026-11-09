// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../common/async_view.dart';
import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../form_model.dart';
import '../form_repository.dart';
import '../validator.dart';
import 'item_widgets.dart';
import 'nested_dialog.dart';

const _pageSize = 5;

/// A link to another entity, chosen among the existing ones or created through
/// the nested dialog.
class EntityAutocompleteField extends ConsumerStatefulWidget {
  const EntityAutocompleteField({required this.item, super.key});

  final NestedItem item;

  @override
  ConsumerState<EntityAutocompleteField> createState() =>
      _EntityAutocompleteFieldState();
}

class _EntityAutocompleteFieldState
    extends ConsumerState<EntityAutocompleteField> {
  final _controller = TextEditingController();
  Timer? _debounce;
  String _term = '';
  List<SearchResult>? _results;
  bool _hasMore = false;
  bool _loading = false;
  ({Object error, int offset})? _failure;
  int _offset = 0;

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String value) {
    final term = value.trim();
    if (term == _term) {
      return;
    }
    _debounce?.cancel();
    setState(() {
      _term = term;
      _results = null;
      _hasMore = false;
      _loading = false;
      _failure = null;
      _offset = 0;
    });
    if (term.isNotEmpty) {
      _debounce = Timer(const Duration(milliseconds: 300), () => _search(0));
    }
  }

  Future<void> _search(int offset) async {
    final term = _term;
    final child = widget.item.child;
    setState(() {
      _loading = true;
      _failure = null;
    });
    try {
      final page = await ref
          .read(formRepositoryProvider)
          .search(
            term: term,
            entityClass: child.entityType,
            shape: child.entityShape,
            offset: offset,
            limit: _pageSize,
          );
      if (!mounted || term != _term) {
        return;
      }
      setState(() {
        _results = offset == 0 ? page.results : [..._results!, ...page.results];
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
    _controller.clear();
    _onChanged('');
    widget.item.selectExisting(result.uri, result.label);
  }

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    return ListenableBuilder(
      listenable: item,
      builder: (context, _) {
        if (item.isExisting) {
          return _SelectedEntity(item: item);
        }
        if (hasAnyValue(item.child)) {
          return NestedTile(item: item);
        }
        return _buildSearch(context);
      },
    );
  }

  Widget _buildSearch(BuildContext context) {
    final t = Translations.of(context);
    final results = _results;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppTextField(
          controller: _controller,
          focusNode: widget.item.focusNode,
          placeholder: t.ui.form.searchExistingEntity,
          errorText: itemErrorText(context, widget.item),
          onChanged: _onChanged,
        ),
        const SizedBox(height: appInputSpacing / 2),
        AppSection(
          children: [
            AppListTile(
              leading: const Icon(CupertinoIcons.add_circled),
              title: TileText(t.ui.form.createNewEntity),
              onTap: () => showNestedDialog(context, widget.item),
            ),
            if (results != null && results.isEmpty)
              CupertinoListTile(
                leading: Icon(
                  CupertinoIcons.search,
                  color: AppColors.of(context).secondaryText,
                ),
                title: TileText(t.ui.form.noMatchingEntities),
              ),
            for (final result in results ?? const <SearchResult>[])
              AppListTile(
                title: TileText(result.label),
                onTap: () => _select(result),
              ),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(appInputSpacing),
                child: Center(child: CupertinoActivityIndicator()),
              )
            else if (_failure case (:final error, :final offset))
              Padding(
                padding: const EdgeInsets.all(appInputSpacing),
                child: ErrorView(error: error, onRetry: () => _search(offset)),
              )
            else if (_hasMore)
              AppListTile(
                leading: const Icon(CupertinoIcons.refresh),
                title: TileText(t.ui.form.moreResults),
                onTap: () => _search(_offset + _pageSize),
              ),
          ],
        ),
      ],
    );
  }
}

class _SelectedEntity extends StatelessWidget {
  const _SelectedEntity({required this.item});

  final NestedItem item;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final colors = AppColors.of(context);
    return Container(
      padding: const EdgeInsets.only(left: appInputSpacing),
      decoration: BoxDecoration(
        color: colors.fieldFill,
        borderRadius: BorderRadius.circular(appRadius),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              item.existingLabel!,
              style: TextStyle(color: colors.label),
            ),
          ),
          AppIconButton(
            label: t.ui.actions.close,
            onPressed: item.clearExisting,
            icon: CupertinoIcons.xmark,
          ),
        ],
      ),
    );
  }
}
