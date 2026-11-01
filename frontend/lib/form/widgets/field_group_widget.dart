// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../../design/app_theme.dart';
import '../../design/controls.dart';
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
              ReorderableList(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: items.length,
                onReorderItem: group.move,
                itemBuilder: (context, index) => Padding(
                  key: ObjectKey(items[index]),
                  padding: listItemSpacing(index),
                  child: _ItemCard(
                    group: group,
                    item: items[index],
                    index: index,
                    dragHandle: DragHandle(index: index),
                  ),
                ),
              )
            else
              for (final (index, item) in items.indexed)
                Padding(
                  key: ObjectKey(item),
                  padding: listItemSpacing(index),
                  child: _ItemCard(
                    group: group,
                    item: item,
                    index: index,
                    showHeading: showHeading,
                  ),
                ),
            if (items.isNotEmpty && group.canAdd)
              const SizedBox(height: appInputSpacing),
            if (group.canAdd)
              Align(
                alignment: Alignment.centerLeft,
                child: AppButton(
                  onPressed: () => _add(context),
                  icon: CupertinoIcons.add_circled,
                  label: t.ui.form.addItem(name: def.displayName),
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
    final styles = AppTextStyles.of(context);
    final label = dragHandle == null
        ? def.displayName
        : '${def.displayName} ${index + 1}';
    if (!showHeading) {
      return ItemWidget(item: item);
    }
    final headingStyle = group.depth == 0 ? styles.heading : styles.subheading;
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
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Flexible(child: Text(label, style: headingStyle)),
                  if (def.isRequired)
                    AppTooltip(
                      message: t.ui.form.required,
                      child: Text(
                        ' *',
                        style: headingStyle.copyWith(color: AppColors.error),
                      ),
                    ),
                  if (def.hasValue != null) ...[
                    const SizedBox(width: appInputSpacing / 2),
                    AppTooltip(
                      message: t.ui.form.mandatoryValue,
                      child: TextIcon(
                        CupertinoIcons.question_circle,
                        style: headingStyle,
                        color: AppColors.primary,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            if (item is NestedItem && (item as NestedItem).isExisting) ...[
              ExistingEntityActions(item: item as NestedItem),
            ],
            if (group.canDelete(item))
              AppButton(
                destructive: true,
                onPressed: () => group.removeItem(item),
                icon: CupertinoIcons.delete,
                label: t.ui.actions.delete,
              ),
          ],
        ),
        const SizedBox(height: appInputSpacing / 2),
        ItemWidget(item: item),
      ],
    );
  }
}
