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
  const FieldGroupWidget({required this.group, super.key});

  final FieldGroup group;

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
                  child: _ItemRow(
                    group: group,
                    item: items[index],
                    dragHandle: DragHandle(index: index),
                  ),
                ),
              )
            else
              for (final (index, item) in items.indexed)
                Padding(
                  key: ObjectKey(item),
                  padding: listItemSpacing(index),
                  child: _ItemRow(group: group, item: item),
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
    } else {
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => item.focusNode.requestFocus(),
      );
    }
  }
}

/// One value of a group: the minus that removes it, the value, and the handle
/// that reorders it, as the rows of an iOS list in edit mode.
class _ItemRow extends StatelessWidget {
  const _ItemRow({required this.group, required this.item, this.dragHandle});

  final FieldGroup group;
  final FormItem item;
  final Widget? dragHandle;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return Row(
      children: [
        if (group.canDelete(item))
          RemoveButton(
            label: t.ui.actions.delete,
            onPressed: () => group.removeItem(item),
          ),
        Expanded(child: ItemWidget(item: item)),
        if (dragHandle != null) ...[
          const SizedBox(width: appInputSpacing / 2),
          dragHandle!,
        ],
      ],
    );
  }
}

/// The name of a property, marked when a value is required.
class PropertyHeading extends StatelessWidget {
  const PropertyHeading({
    required this.label,
    required this.style,
    this.required = false,
    super.key,
  });

  final String label;
  final TextStyle style;
  final bool required;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.baseline,
      textBaseline: TextBaseline.alphabetic,
      children: [
        Flexible(child: Text(label, style: style)),
        if (required)
          AppTooltip(
            message: t.ui.form.required,
            child: Text(
              ' *',
              style: style.copyWith(color: AppColors.of(context).error),
            ),
          ),
      ],
    );
  }
}
