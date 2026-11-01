// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../design/app_theme.dart';
import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../collector.dart';
import '../form_model.dart';
import '../form_repository.dart';
import '../form_scope.dart';
import 'entity_form.dart';

/// The chain of nested items from the root entity down to [item].
List<NestedItem> nestedChain(NestedItem item) {
  final chain = <NestedItem>[];
  NestedItem? current = item;
  while (current != null) {
    chain.insert(0, current);
    current = current.group.owner.parentItem;
  }
  return chain;
}

/// Hides an untouched item as soon as the dialog closes, but disposes it only
/// once the dialog is unmounted, because its widgets use the item's focus nodes
/// until the exit transition ends.
Future<void> showNestedDialog(BuildContext context, NestedItem item) async {
  final scope = FormScope.of(context);
  final route = CupertinoSheetRoute<void>(
    enableDrag: false,
    settings: RouteSettings(arguments: item),
    scrollableBuilder: (context, scrollController) => FormScope(
      notifier: scope,
      child: NestedEntityDialog(item: item, scrollController: scrollController),
    ),
  );
  unawaited(Navigator.of(context, rootNavigator: true).push(route));
  await route.popped;
  final discard = item.discardIfUntouched && !item.touched;
  item.discardIfUntouched = false;
  if (discard) {
    item.group.detachItem(item);
  }
  await route.completed;
  if (discard) {
    item.dispose();
  }
}

class NestedEntityDialog extends ConsumerStatefulWidget {
  const NestedEntityDialog({
    required this.item,
    required this.scrollController,
    super.key,
  });

  final NestedItem item;
  final ScrollController scrollController;

  @override
  ConsumerState<NestedEntityDialog> createState() => _NestedEntityDialogState();
}

class _NestedEntityDialogState extends ConsumerState<NestedEntityDialog> {
  Timer? _debounce;
  String? _fingerprint;
  int _revision = 0;

  @override
  void initState() {
    super.initState();
    widget.item.addListener(_schedulePreview);
    _schedulePreview();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    widget.item.removeListener(_schedulePreview);
    super.dispose();
  }

  void _schedulePreview() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 250), _updatePreview);
  }

  Future<void> _updatePreview() async {
    final item = widget.item;
    final revision = ++_revision;
    if (item.isExisting) {
      return;
    }
    final entity = nestedDetailsComplete(item) ? draftEntity(item) : null;
    if (entity == null) {
      _fingerprint = null;
      item.draftLabel.value = (label: null, failed: false);
      return;
    }
    final entry = {
      'parent_class': item.group.owner.entityType,
      'parent_shape': item.def.subjectShape,
      'predicate': item.def.uri,
      'entity': entity,
    };
    final fingerprint = entry.toString();
    if (fingerprint == _fingerprint) {
      return;
    }
    try {
      final label = await ref.read(formRepositoryProvider).draftLabel(entry);
      if (revision != _revision || !mounted) {
        return;
      }
      _fingerprint = fingerprint;
      item.draftLabel.value = (
        label: label ?? nestedFallbackLabel(item),
        failed: false,
      );
    } on Exception {
      if (revision != _revision || !mounted) {
        return;
      }
      item.draftLabel.value = (
        label: item.draftLabel.value.label,
        failed: true,
      );
    }
  }

  void _close() {
    final scope = FormScope.of(context);
    for (final group in widget.item.child.groups) {
      for (final nested in group.items) {
        scope.markChecked(nested);
      }
    }
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final scope = FormScope.of(context);
    final chain = nestedChain(widget.item);
    return CupertinoPageScaffold(
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: appInputSpacing),
            decoration: const BoxDecoration(
              color: AppColors.surface,
              border: Border(
                bottom: BorderSide(color: AppColors.separator, width: 0),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        CupertinoButton(
                          onPressed: () => _popTo(0),
                          child: SelectionContainer.disabled(
                            child: Text(scope.rootLabel),
                          ),
                        ),
                        for (final (index, entry) in chain.indexed) ...[
                          const Icon(
                            CupertinoIcons.chevron_right,
                            size: 16,
                            color: AppColors.secondaryText,
                          ),
                          if (entry == widget.item)
                            Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: appInputSpacing,
                              ),
                              child: Text(
                                entry.def.displayName,
                                style: AppTextStyles.of(context).heading,
                              ),
                            )
                          else
                            CupertinoButton(
                              onPressed: () => _popTo(index + 1),
                              child: SelectionContainer.disabled(
                                child: Text(entry.def.displayName),
                              ),
                            ),
                        ],
                      ],
                    ),
                  ),
                ),
                CupertinoButton(
                  onPressed: _close,
                  child: SelectionContainer.disabled(
                    child: Text(
                      t.ui.actions.done,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              controller: widget.scrollController,
              padding: EdgeInsets.all(
                MediaQuery.sizeOf(context).width < appCompactWidth
                    ? appCardPadding
                    : appPageMargin,
              ),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: appPageMaxWidth),
                  child: EntityForm(node: widget.item.child),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _popTo(int depth) {
    final chain = nestedChain(widget.item);
    final toClose = chain.length - depth;
    for (var i = 0; i < toClose; i++) {
      _close();
    }
  }
}

bool nestedDetailsComplete(NestedItem item) {
  final node = item.child;
  var hasValue = false;
  for (final group in node.groups) {
    for (final child in group.items) {
      switch (child) {
        case LiteralItem() || SelectItem() || DateItem():
          if (child.isEmpty) {
            if (group.def.isRequired) {
              return false;
            }
          } else {
            hasValue = true;
          }
        case MandatoryItem():
          hasValue = true;
        case NestedItem():
          if (child.isExisting || nestedDetailsComplete(child)) {
            hasValue = true;
          }
        case OrItem():
          if (child.selectedGroup != null) {
            hasValue = true;
          }
      }
    }
  }
  return hasValue;
}

String nestedFallbackLabel(NestedItem item) {
  final parts = <String>[];
  for (final group in item.child.groups) {
    for (final child in group.items) {
      final value = child.textValue;
      if (child is MandatoryItem || value == null || value.trim().isEmpty) {
        continue;
      }
      final shown = child is SelectItem
          ? child.def.optionalValueLabel(value)
          : value;
      parts.add('${group.def.displayName}: $shown');
      if (parts.length == 2) {
        return parts.join(' · ');
      }
    }
  }
  return parts.join(' · ');
}
