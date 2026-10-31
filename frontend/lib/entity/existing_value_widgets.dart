// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../common/reference_views.dart';
import '../design/spacing.dart';
import '../form/form_model.dart';
import '../form/widgets/field_group_widget.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
import 'edit_session.dart';
import 'entity_models.dart';

class EditableGroupWidget extends StatelessWidget {
  const EditableGroupWidget({
    required this.group,
    required this.view,
    required this.editing,
    super.key,
  });

  final EditableGroup group;
  final EntityView view;
  final bool editing;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return ListenableBuilder(
      listenable: group,
      builder: (context, _) {
        final draggable = editing && group.group.isDraggable;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(group.group.displayName, style: textTheme.titleMedium),
            const SizedBox(height: appInputSpacing / 2),
            if (draggable)
              ReorderableListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                buildDefaultDragHandles: false,
                itemCount: group.existing.length,
                onReorderItem: group.move,
                itemBuilder: (context, index) => Padding(
                  key: ObjectKey(group.existing[index]),
                  padding: const EdgeInsets.only(bottom: appInputSpacing),
                  child: ExistingValueWidget(
                    value: group.existing[index],
                    view: view,
                    editing: editing,
                    index: index,
                    dragHandle: ReorderableDragStartListener(
                      index: index,
                      child: const Icon(Icons.drag_indicator),
                    ),
                  ),
                ),
              )
            else
              for (final (index, value) in group.existing.indexed)
                Padding(
                  key: ObjectKey(value),
                  padding: const EdgeInsets.only(bottom: appInputSpacing),
                  child: ExistingValueWidget(
                    value: value,
                    view: view,
                    editing: editing,
                    index: group.group.isDraggable ? index : null,
                  ),
                ),
            if (editing && group.formGroup != null)
              FieldGroupWidget(group: group.formGroup!),
          ],
        );
      },
    );
  }
}

class ExistingValueWidget extends StatelessWidget {
  const ExistingValueWidget({
    required this.value,
    required this.view,
    required this.editing,
    required this.index,
    this.dragHandle,
    super.key,
  });

  final ExistingValue value;
  final EntityView view;
  final bool editing;
  final int? index;
  final Widget? dragHandle;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    final triple = value.triple;
    final deletable =
        editing &&
        view.shacl &&
        view.canBeDeleted.contains(triple.predicate) &&
        !triple.isMandatory;
    return ListenableBuilder(
      listenable: value,
      builder: (context, _) {
        final deleted = value.markedForDeletion;
        return Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            if (dragHandle != null) ...[
              dragHandle!,
              const SizedBox(width: appInputSpacing / 2),
            ],
            if (index != null) ...[
              Text('${index! + 1}.'),
              const SizedBox(width: appInputSpacing / 2),
            ],
            Expanded(
              child: DefaultTextStyle.merge(
                style: deleted
                    ? const TextStyle(decoration: TextDecoration.lineThrough)
                    : const TextStyle(),
                child: _ValueBody(
                  value: value,
                  view: view,
                  editable: editing && !deleted,
                ),
              ),
            ),
            if (triple.externalEntity != null)
              TextButton.icon(
                onPressed: () => context.go(entityPath(triple.externalEntity!)),
                icon: const Icon(Icons.arrow_forward, size: 16),
                label: Text(t.ui.actions.visit),
              ),
            if (deletable && !deleted)
              TextButton.icon(
                style: TextButton.styleFrom(foregroundColor: colorScheme.error),
                onPressed: value.markForDeletion,
                icon: const Icon(Icons.delete_outline, size: 18),
                label: Text(t.ui.actions.delete),
              ),
            if (deletable && deleted)
              TextButton.icon(
                onPressed: value.undoDeletion,
                icon: const Icon(Icons.undo, size: 18),
                label: Text(t.ui.entity.revert),
              ),
          ],
        );
      },
    );
  }
}

class _ValueBody extends StatelessWidget {
  const _ValueBody({
    required this.value,
    required this.view,
    required this.editable,
  });

  final ExistingValue value;
  final EntityView view;
  final bool editable;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final triple = value.triple;
    final colorScheme = Theme.of(context).colorScheme;
    if (triple.externalEntity != null) {
      return LinkText(
        label: triple.value,
        onTap: () => context.go(entityPath(triple.externalEntity!)),
      );
    }
    if (triple.isMandatory) {
      return Row(
        children: [
          Flexible(child: Text(triple.value)),
          const SizedBox(width: 4),
          Tooltip(
            message: t.ui.form.mandatoryValue,
            child: Icon(
              Icons.help_outline,
              size: 16,
              color: colorScheme.primary,
            ),
          ),
        ],
      );
    }
    final options = view.optionalValues[triple.predicate];
    if (options != null && options.isNotEmpty) {
      if (!editable) {
        return Text(triple.label ?? value.newValue);
      }
      return DropdownButtonFormField<String>(
        initialValue: options.any((o) => o.value == value.newValue)
            ? value.newValue
            : null,
        decoration: const InputDecoration(
          border: OutlineInputBorder(),
          isDense: true,
        ),
        items: [
          for (final option in options)
            DropdownMenuItem(value: option.value, child: Text(option.label)),
        ],
        onChanged: (selected) =>
            selected == null ? null : value.setValue(selected),
      );
    }
    if (!editable) {
      return Text(value.newValue);
    }
    final allowed = dateTypesFor(view.datatypes[triple.predicate] ?? const []);
    if (allowed.isNotEmpty) {
      return Row(
        children: [
          if (allowed.length > 1) ...[
            DropdownButton<DateType>(
              value: allowed.contains(value.dateType)
                  ? value.dateType
                  : allowed.first,
              items: [
                for (final type in allowed)
                  DropdownMenuItem(
                    value: type,
                    child: Text(switch (type) {
                      DateType.date => t.ui.form.dateTypeDate,
                      DateType.month => t.ui.form.dateTypeMonth,
                      DateType.year => t.ui.form.dateTypeYear,
                    }),
                  ),
              ],
              onChanged: (type) =>
                  type == null ? null : value.setDateType(type),
            ),
            const SizedBox(width: appInputSpacing),
          ],
          Expanded(child: _TextValueField(value: value, multiline: false)),
        ],
      );
    }
    final field = (view.groups.firstWhere(
      (g) => g.property == triple.predicate && g.field != null,
      orElse: () => value.group,
    )).field;
    return _TextValueField(
      value: value,
      multiline: field?.inputType == 'textarea',
    );
  }
}

class _TextValueField extends StatefulWidget {
  const _TextValueField({required this.value, required this.multiline});

  final ExistingValue value;
  final bool multiline;

  @override
  State<_TextValueField> createState() => _TextValueFieldState();
}

class _TextValueFieldState extends State<_TextValueField> {
  late final TextEditingController _controller = TextEditingController(
    text: widget.value.newValue,
  );

  @override
  void initState() {
    super.initState();
    widget.value.addListener(_sync);
  }

  void _sync() {
    if (_controller.text != widget.value.newValue) {
      _controller.text = widget.value.newValue;
    }
  }

  @override
  void dispose() {
    widget.value.removeListener(_sync);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: _controller,
      maxLines: widget.multiline ? 5 : 1,
      decoration: const InputDecoration(
        border: OutlineInputBorder(),
        isDense: true,
      ),
      onChanged: widget.value.setValue,
    );
  }
}
