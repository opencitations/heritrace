// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:go_router/go_router.dart';

import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../form/form_model.dart';
import '../form/widgets/boolean_field.dart';
import '../form/widgets/field_group_widget.dart';
import '../form/widgets/item_widgets.dart';
import '../i18n/translations.g.dart';
import '../navigation/entity_store.dart';
import 'edit_session.dart';
import 'entity_models.dart';

final _valueRowConstraints = BoxConstraints(
  minHeight: kCupertinoButtonMinSize[CupertinoButtonSize.medium]!,
);

/// Opens the page of an entity when its row is tapped.
class _EntityLink extends StatelessWidget {
  const _EntityLink({required this.uri, required this.child});

  final String uri;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return SelectionContainer.disabled(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => context.go(context.entityStore.entityPath(uri)),
        child: MouseRegion(cursor: SystemMouseCursors.click, child: child),
      ),
    );
  }
}

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
    return ListenableBuilder(
      listenable: group,
      builder: (context, _) {
        if (group.group.field?.isBoolean ?? false) {
          return BooleanFieldCard(
            label: group.group.displayName,
            description: group.group.field?.description,
            value: group.isSwitchedOn,
            onChanged: editing && group.canSwitch ? group.switchTo : null,
          );
        }
        final draggable = editing && group.group.isDraggable;
        return AppCard(
          footer: group.group.field?.description,
          header: PropertyHeading(
            label: group.group.displayName,
            style: AppTextStyles.of(context).groupHeader,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (draggable)
                ReorderableList(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: group.existing.length,
                  onReorderItem: group.move,
                  itemBuilder: (context, index) => Padding(
                    key: ObjectKey(group.existing[index]),
                    padding: listItemSpacing(index),
                    child: ExistingValueWidget(
                      value: group.existing[index],
                      view: view,
                      editing: editing,
                      dragHandle: DragHandle(index: index),
                    ),
                  ),
                )
              else
                for (final (index, value) in group.existing.indexed)
                  Padding(
                    key: ObjectKey(value),
                    padding: listItemSpacing(index),
                    child: ExistingValueWidget(
                      value: value,
                      view: view,
                      editing: editing,
                    ),
                  ),
              if (editing && group.formGroup != null) ...[
                if (group.existing.isNotEmpty)
                  const SizedBox(height: appInputSpacing),
                FieldGroupWidget(group: group.formGroup!),
              ],
            ],
          ),
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
    this.dragHandle,
    super.key,
  });

  final ExistingValue value;
  final EntityView view;
  final bool editing;
  final Widget? dragHandle;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final triple = value.triple;
    final deletable =
        editing &&
        view.shacl &&
        view.canBeDeleted.contains(triple.predicate) &&
        !triple.isMandatory;
    final linked =
        !editing && triple.externalEntity != null && triple.details == null;
    return ListenableBuilder(
      listenable: value,
      builder: (context, _) {
        final deleted = value.markedForDeletion;
        final row = ConstrainedBox(
          constraints: _valueRowConstraints,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              if (deletable && !deleted)
                RemoveButton(
                  label: t.ui.actions.delete,
                  onPressed: value.markForDeletion,
                ),
              if (deletable && deleted)
                RowLeadingButton(
                  icon: CupertinoIcons.arrow_uturn_left,
                  label: t.ui.entity.revert,
                  onPressed: value.undoDeletion,
                ),
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
              if (linked) const CupertinoListTileChevron(),
              if (dragHandle != null) ...[
                const SizedBox(width: appInputSpacing / 2),
                dragHandle!,
              ],
            ],
          ),
        );
        if (!linked) {
          return row;
        }
        return _EntityLink(uri: triple.externalEntity!, child: row);
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
    final triple = value.triple;
    if (triple.details case final details?) {
      return _Details(details: details, linked: !editable);
    }
    if (triple.externalEntity != null) {
      return Text(triple.value);
    }
    if (triple.isMandatory) {
      return MandatoryValueText(triple.value);
    }
    final options = view.optionalValues[triple.predicate];
    if (options != null && options.isNotEmpty) {
      if (!editable) {
        return Text(triple.label ?? value.newValue);
      }
      return AppMenuButton<String?>(
        value: options.any((o) => o.value == value.newValue)
            ? value.newValue
            : null,
        options: [
          for (final option in options)
            AppMenuOption(option.value, option.label),
        ],
        onChanged: (selected) => value.setValue(selected!),
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
            DateTypeMenu(
              value: allowed.contains(value.dateType)
                  ? value.dateType
                  : allowed.first,
              allowed: allowed,
              onChanged: value.setDateType,
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

/// The fields of a linked entity, shown in place of the link.
class _Details extends StatelessWidget {
  const _Details({required this.details, required this.linked});

  final List<EntityDetail> details;
  final bool linked;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      spacing: appCaptionSpacing,
      children: [
        for (final detail in details)
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (details.length > 1)
                Text(detail.name, style: AppTextStyles.of(context).caption),
              for (final value in detail.values)
                if (linked && value.uri != null)
                  _EntityLink(
                    uri: value.uri!,
                    child: ConstrainedBox(
                      constraints: _valueRowConstraints,
                      child: Row(
                        children: [
                          Expanded(child: Text(value.label)),
                          const CupertinoListTileChevron(),
                        ],
                      ),
                    ),
                  )
                else
                  Text(value.label),
            ],
          ),
      ],
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
    return AppTextField(
      controller: _controller,
      maxLines: widget.multiline ? 5 : 1,
      onChanged: widget.value.setValue,
    );
  }
}
