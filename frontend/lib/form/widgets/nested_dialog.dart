// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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

/// Discards an untouched item only once the dialog is unmounted, because its
/// widgets use the item's focus nodes until the exit transition ends.
Future<void> showNestedDialog(BuildContext context, NestedItem item) async {
  final scope = FormScope.of(context);
  final route = DialogRoute<void>(
    context: context,
    barrierDismissible: false,
    settings: RouteSettings(arguments: item),
    builder: (context) => FormScope(
      notifier: scope,
      child: NestedEntityDialog(item: item),
    ),
  );
  unawaited(Navigator.of(context).push(route));
  await route.completed;
  if (item.discardIfUntouched && !item.touched) {
    item.group.removeItem(item);
  }
  item.discardIfUntouched = false;
}

class NestedEntityDialog extends ConsumerStatefulWidget {
  const NestedEntityDialog({required this.item, super.key});

  final NestedItem item;

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
      item.setDraftLabel(null, failed: false);
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
      item.setDraftLabel(label ?? nestedFallbackLabel(item), failed: false);
    } on Exception {
      if (revision != _revision || !mounted) {
        return;
      }
      item.setDraftLabel(item.draftLabel, failed: true);
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
    return Dialog.fullscreen(
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(appCardPadding),
            child: Row(
              children: [
                Expanded(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        TextButton(
                          onPressed: () => _popTo(0),
                          child: Text(scope.rootLabel),
                        ),
                        for (final (index, entry) in chain.indexed) ...[
                          const Icon(Icons.chevron_right, size: 18),
                          if (entry == widget.item)
                            Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: appInputSpacing,
                              ),
                              child: Text(
                                entry.def.displayName,
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                            )
                          else
                            TextButton(
                              onPressed: () => _popTo(index + 1),
                              child: Text(entry.def.displayName),
                            ),
                        ],
                      ],
                    ),
                  ),
                ),
                IconButton(
                  tooltip: t.ui.actions.close,
                  onPressed: _close,
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: SingleChildScrollView(
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
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.all(appCardPadding),
            child: Align(
              alignment: Alignment.centerRight,
              child: FilledButton(
                onPressed: _close,
                child: Text(t.ui.actions.done),
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
