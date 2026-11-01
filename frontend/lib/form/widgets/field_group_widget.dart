// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';

import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../form_model.dart';
import 'item_widgets.dart';
import 'nested_dialog.dart';

class FieldGroupWidget extends StatelessWidget {
  const FieldGroupWidget({
    required this.group,
    this.showHeading = true,
    super.key,
  });

  final FieldGroup group;
  final bool showHeading;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return ListenableBuilder(
      listenable: group,
      builder: (context, _) {
        final def = group.def;
        final ordered = def.orderedBy != null;
        final items = group.items;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (ordered)
              ReorderableListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                buildDefaultDragHandles: false,
                itemCount: items.length,
                onReorderItem: group.move,
                itemBuilder: (context, index) => Padding(
                  key: ObjectKey(items[index]),
                  padding: const EdgeInsets.only(bottom: appInputSpacing),
                  child: _ItemCard(
                    group: group,
                    item: items[index],
                    index: index,
                    dragHandle: ReorderableDragStartListener(
                      index: index,
                      child: const Icon(Icons.drag_indicator),
                    ),
                  ),
                ),
              )
            else
              for (final (index, item) in items.indexed)
                Padding(
                  key: ObjectKey(item),
                  padding: const EdgeInsets.only(bottom: appInputSpacing),
                  child: _ItemCard(
                    group: group,
                    item: item,
                    index: index,
                    showHeading: showHeading,
                  ),
                ),
            if (group.canAdd)
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: () => _add(context),
                  icon: const Icon(Icons.add_circle_outline),
                  label: Text(t.ui.form.addItem(name: def.displayName)),
                ),
              ),
          ],
        );
      },
    );
  }

  void _add(BuildContext context) {
    final item = group.addItem();
    if (item is NestedItem) {
      item.discardIfUntouched = true;
      showNestedDialog(context, item);
    }
  }
}

class _ItemCard extends StatelessWidget {
  const _ItemCard({
    required this.group,
    required this.item,
    required this.index,
    this.dragHandle,
    this.showHeading = true,
  });

  final FieldGroup group;
  final FormItem item;
  final int index;
  final Widget? dragHandle;
  final bool showHeading;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final def = group.def;
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;
    final label = dragHandle == null
        ? def.displayName
        : '${def.displayName} ${index + 1}';
    if (!showHeading) {
      return ItemWidget(item: item);
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            if (dragHandle != null) ...[
              dragHandle!,
              const SizedBox(width: appInputSpacing / 2),
            ],
            Expanded(
              child: Row(
                children: [
                  Flexible(
                    child: Text(
                      label,
                      style: group.depth == 0
                          ? textTheme.titleMedium
                          : textTheme.titleSmall,
                    ),
                  ),
                  if (def.isRequired)
                    Tooltip(
                      message: t.ui.form.required,
                      child: Text(
                        ' *',
                        style: TextStyle(color: colorScheme.error),
                      ),
                    ),
                  if (def.hasValue != null)
                    Tooltip(
                      message: t.ui.form.mandatoryValue,
                      child: Padding(
                        padding: const EdgeInsets.only(left: 4),
                        child: Icon(
                          Icons.help_outline,
                          size: 16,
                          color: colorScheme.primary,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            if (item is NestedItem && (item as NestedItem).isExisting) ...[
              ExistingEntityActions(item: item as NestedItem),
            ],
            if (group.canDelete(item))
              TextButton.icon(
                style: TextButton.styleFrom(foregroundColor: colorScheme.error),
                onPressed: () => group.removeItem(item),
                icon: const Icon(Icons.delete_outline, size: 18),
                label: Text(t.ui.actions.delete),
              ),
          ],
        ),
        const SizedBox(height: appInputSpacing / 2),
        ItemWidget(item: item),
      ],
    );
  }
}
