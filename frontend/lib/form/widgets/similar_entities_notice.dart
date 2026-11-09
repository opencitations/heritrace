// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';
import 'dart:convert';

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../common/async_view.dart';
import '../../common/reference_views.dart';
import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../../navigation/entity_store.dart';
import '../field_def.dart';
import '../form_model.dart';
import '../form_repository.dart';

Map<String, Object?> _textTerm(FormItem item) => {
  'value': item.textValue!.trim(),
  if (item is DateItem)
    'datatype': item.datatype
  else if (item.def.datatypes.isNotEmpty)
    'datatype': item.def.datatypes.first,
};

List<Map<String, Object?>> _nestedFields(EntityNode node) {
  final fields = <Map<String, Object?>>[];
  var hasEnteredValue = false;
  for (final group in node.groups) {
    if (group.def.uri == rdfType) {
      continue;
    }
    for (final item in group.items) {
      switch (item) {
        case MandatoryItem():
          fields.add({'predicate': group.def.uri, 'uri': item.textValue});
        case SelectItem() || LiteralItem() || DateItem() when !item.isEmpty:
          hasEnteredValue = true;
          fields.add({
            'predicate': group.def.uri,
            if (item is SelectItem && item.def.datatypes.isEmpty)
              'uri': item.textValue
            else
              ..._textTerm(item),
          });
        default:
          break;
      }
    }
  }
  return hasEnteredValue ? fields : const [];
}

Map<String, Object?>? _draftTerm(FormItem item) {
  switch (item) {
    case OrItem(:final selectedItem):
      return selectedItem == null ? null : _draftTerm(selectedItem);
    case NestedItem(:final existingUri?):
      return {'uri': existingUri};
    case NestedItem(:final child):
      final fields = _nestedFields(child);
      return fields.isEmpty ? null : {'fields': fields};
    case MandatoryItem():
      return null;
    case SelectItem() when item.def.datatypes.isEmpty && !item.isEmpty:
      return {'uri': item.textValue};
    default:
      return item.isEmpty ? null : _textTerm(item);
  }
}

/// The values of a draft, in the form the similarity check expects.
Map<String, List<Map<String, Object?>>> draftSimilarityValues(EntityNode root) {
  final values = <String, List<Map<String, Object?>>>{};
  for (final group in root.groups) {
    for (final item in group.items) {
      final term = _draftTerm(item);
      if (term != null) {
        values.putIfAbsent(group.def.uri, () => []).add(term);
      }
    }
  }
  return values;
}

/// Warns that the entity being created may already exist.
class SimilarEntitiesNotice extends ConsumerStatefulWidget {
  const SimilarEntitiesNotice({required this.root, super.key});

  final EntityNode root;

  @override
  ConsumerState<SimilarEntitiesNotice> createState() =>
      _SimilarEntitiesNoticeState();
}

class _SimilarEntitiesNoticeState extends ConsumerState<SimilarEntitiesNotice> {
  Timer? _debounce;
  String _fingerprint = '{}';
  List<SearchResult> _results = const [];
  Object? _failure;

  @override
  void initState() {
    super.initState();
    widget.root.addListener(_onDraftChanged);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    widget.root.removeListener(_onDraftChanged);
    super.dispose();
  }

  void _onDraftChanged() {
    final values = draftSimilarityValues(widget.root);
    final fingerprint = jsonEncode(values);
    if (fingerprint == _fingerprint) {
      return;
    }
    _fingerprint = fingerprint;
    _debounce?.cancel();
    if (_results.isNotEmpty || _failure != null) {
      setState(() {
        _results = const [];
        _failure = null;
      });
    }
    if (values.isNotEmpty) {
      _debounce = Timer(
        const Duration(milliseconds: 500),
        () => _check(values, fingerprint),
      );
    }
  }

  Future<void> _check(
    Map<String, List<Map<String, Object?>>> values,
    String fingerprint,
  ) async {
    try {
      final page = await ref
          .read(formRepositoryProvider)
          .similarToDraft(
            entityType: widget.root.entityType,
            shape: widget.root.entityShape,
            values: values,
          );
      if (mounted && fingerprint == _fingerprint) {
        setState(() {
          _results = page.results;
          _failure = null;
        });
      }
    } on Exception catch (error) {
      if (mounted && fingerprint == _fingerprint) {
        setState(() => _failure = error);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_failure case final failure?) {
      return Padding(
        padding: const EdgeInsets.only(bottom: appSectionSpacing),
        child: ErrorView(
          error: failure,
          onRetry: () =>
              _check(draftSimilarityValues(widget.root), _fingerprint),
        ),
      );
    }
    if (_results.isEmpty) {
      return const SizedBox.shrink();
    }
    final t = Translations.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: appSectionSpacing),
      child: AppSection(
        children: [
          CupertinoListTile(
            leading: const Icon(
              CupertinoIcons.info_circle,
              color: AppColors.primary,
            ),
            title: Text(t.ui.form.similarEntities),
            trailing: AppIconButton(
              label: t.ui.actions.close,
              onPressed: () => setState(() => _results = const []),
              icon: CupertinoIcons.xmark,
            ),
          ),
          for (final result in _results)
            AppListTile(
              title: TileText(result.label),
              trailing: const CupertinoListTileChevron(),
              onTap: () =>
                  openExternal(context.entityStore.entityPath(result.uri)),
            ),
        ],
      ),
    );
  }
}
