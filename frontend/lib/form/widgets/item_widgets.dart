// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';

import '../../common/reference_views.dart';
import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../../navigation/app_paths.dart';
import '../field_def.dart';
import '../form_model.dart';
import '../form_scope.dart';
import 'entity_search.dart';
import 'field_group_widget.dart';
import 'nested_dialog.dart';

class ItemWidget extends StatelessWidget {
  const ItemWidget({required this.item, super.key});

  final FormItem item;

  @override
  Widget build(BuildContext context) {
    return switch (item) {
      LiteralItem() => LiteralField(item: item as LiteralItem),
      DateItem() => DateField(item: item as DateItem),
      SelectItem() => SelectField(item: item as SelectItem),
      MandatoryItem() => MandatoryValueField(item: item as MandatoryItem),
      NestedItem() => NestedTile(item: item as NestedItem),
      OrItem() => OrSelector(item: item as OrItem),
    };
  }
}

String? _errorText(BuildContext context, FormItem item) {
  final scope = FormScope.of(context);
  if (!scope.showsErrorsFor(item)) {
    return null;
  }
  final errors = scope.errorsFor(item);
  if (errors.isEmpty) {
    return null;
  }
  return errors.map((error) => error.message).join(' ');
}

class LiteralField extends StatefulWidget {
  const LiteralField({required this.item, super.key});

  final LiteralItem item;

  @override
  State<LiteralField> createState() => _LiteralFieldState();
}

class _LiteralFieldState extends State<LiteralField> {
  late final TextEditingController _controller = TextEditingController(
    text: widget.item.value,
  );

  @override
  void initState() {
    super.initState();
    widget.item.addListener(_syncFromItem);
    widget.item.focusNode.addListener(_onFocusChanged);
  }

  void _syncFromItem() {
    if (_controller.text != widget.item.value) {
      _controller.text = widget.item.value;
    }
  }

  void _onFocusChanged() {
    if (!widget.item.focusNode.hasFocus) {
      FormScope.of(context).markChecked(widget.item);
    }
  }

  @override
  void dispose() {
    widget.item.removeListener(_syncFromItem);
    widget.item.focusNode.removeListener(_onFocusChanged);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final def = widget.item.def;
    final multiline = def.inputType == 'textarea';
    final field = TextField(
      controller: _controller,
      focusNode: widget.item.focusNode,
      maxLines: multiline ? 5 : 1,
      keyboardType: switch (def.inputType) {
        'number' => const TextInputType.numberWithOptions(
          decimal: true,
          signed: true,
        ),
        'url' => TextInputType.url,
        'textarea' => TextInputType.multiline,
        _ => TextInputType.text,
      },
      decoration: InputDecoration(
        border: const OutlineInputBorder(),
        isDense: true,
        hintText: def.displayName,
        errorText: _errorText(context, widget.item),
      ),
      onChanged: widget.item.setValue,
    );
    if (def.supportsSearch) {
      return EntitySearchField(item: widget.item, field: field);
    }
    return field;
  }
}

class DateField extends StatefulWidget {
  const DateField({required this.item, super.key});

  final DateItem item;

  @override
  State<DateField> createState() => _DateFieldState();
}

class _DateFieldState extends State<DateField> {
  late final TextEditingController _controller = TextEditingController(
    text: widget.item.value,
  );

  @override
  void initState() {
    super.initState();
    widget.item.addListener(_syncFromItem);
    widget.item.focusNode.addListener(_onFocusChanged);
  }

  void _syncFromItem() {
    if (_controller.text != widget.item.value) {
      _controller.text = widget.item.value;
    }
  }

  void _onFocusChanged() {
    if (!widget.item.focusNode.hasFocus) {
      FormScope.of(context).markChecked(widget.item);
    }
  }

  @override
  void dispose() {
    widget.item.removeListener(_syncFromItem);
    widget.item.focusNode.removeListener(_onFocusChanged);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final item = widget.item;
    final allowed = dateTypesFor(item.def.datatypes);
    return ListenableBuilder(
      listenable: item,
      builder: (context, _) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (allowed.length > 1) ...[
            DropdownButton<DateType>(
              value: item.dateType,
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
              onChanged: (type) => type == null ? null : item.setDateType(type),
            ),
            const SizedBox(width: appInputSpacing),
          ],
          Expanded(
            child: TextField(
              controller: _controller,
              focusNode: item.focusNode,
              decoration: InputDecoration(
                border: const OutlineInputBorder(),
                isDense: true,
                hintText: switch (item.dateType) {
                  DateType.date => 'YYYY-MM-DD',
                  DateType.month => 'YYYY-MM',
                  DateType.year => 'YYYY',
                },
                errorText: _errorText(context, item),
                suffixIcon: item.dateType == DateType.date
                    ? IconButton(
                        tooltip: t.ui.form.pickDate,
                        icon: const Icon(Icons.calendar_today),
                        onPressed: () => _pickDate(context),
                      )
                    : null,
              ),
              onChanged: item.setValue,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _pickDate(BuildContext context) async {
    final initial = DateTime.tryParse(widget.item.value) ?? DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(1000),
      lastDate: DateTime(9999),
    );
    if (picked != null) {
      widget.item.setValue(picked.toIso8601String().substring(0, 10));
    }
  }
}

class SelectField extends StatelessWidget {
  const SelectField({required this.item, super.key});

  final SelectItem item;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final def = item.def;
    return ListenableBuilder(
      listenable: item,
      builder: (context, _) => DropdownButtonFormField<String?>(
        initialValue: item.value,
        focusNode: item.focusNode,
        decoration: InputDecoration(
          border: const OutlineInputBorder(),
          isDense: true,
          errorText: _errorText(context, item),
        ),
        items: [
          DropdownMenuItem<String?>(
            value: null,
            child: Text(t.ui.form.selectOption),
          ),
          for (final value in def.optionalValues)
            DropdownMenuItem<String?>(
              value: value,
              child: Text(def.optionalValueLabel(value)),
            ),
        ],
        onChanged: (value) {
          item.setValue(value);
          FormScope.of(context).markChecked(item);
        },
      ),
    );
  }
}

class MandatoryValueField extends StatelessWidget {
  const MandatoryValueField({required this.item, super.key});

  final MandatoryItem item;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: appInputSpacing),
      child: Text(item.def.hasValueLabel ?? item.def.hasValue!),
    );
  }
}

class OrSelector extends StatelessWidget {
  const OrSelector({required this.item, super.key});

  final OrItem item;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return ListenableBuilder(
      listenable: item,
      builder: (context, _) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DropdownButtonFormField<FieldDef?>(
            initialValue: item.selected,
            focusNode: item.focusNode,
            decoration: InputDecoration(
              border: const OutlineInputBorder(),
              isDense: true,
              errorText: _errorText(context, item),
            ),
            items: [
              DropdownMenuItem<FieldDef?>(
                value: null,
                child: Text(t.ui.form.selectOption),
              ),
              for (final option in item.def.or!)
                DropdownMenuItem<FieldDef?>(
                  value: option,
                  child: Text(option.displayName),
                ),
            ],
            onChanged: item.select,
          ),
          if (item.selectedGroup != null) ...[
            const SizedBox(height: appInputSpacing),
            Padding(
              padding: const EdgeInsets.only(left: appInputSpacing),
              child: FieldGroupWidget(group: item.selectedGroup!),
            ),
          ],
        ],
      ),
    );
  }
}

class NestedTile extends StatelessWidget {
  const NestedTile({required this.item, super.key});

  final NestedItem item;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    return ListenableBuilder(
      listenable: item,
      builder: (context, _) {
        if (item.isExisting) {
          return Container(
            padding: const EdgeInsets.all(appInputSpacing),
            decoration: BoxDecoration(
              border: Border.all(color: colorScheme.outline),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(item.existingLabel!),
          );
        }
        final scope = FormScope.of(context);
        final hasErrors =
            scope.validationStarted &&
            scope.errors.any((error) => _belongsTo(error.item, item));
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            OutlinedButton(
              focusNode: item.focusNode,
              style: OutlinedButton.styleFrom(
                alignment: Alignment.centerLeft,
                foregroundColor: hasErrors
                    ? colorScheme.error
                    : colorScheme.onSurface,
              ),
              onPressed: () => showNestedDialog(context, item),
              child: Row(
                children: [
                  Expanded(
                    child: Text(item.draftLabel ?? t.ui.form.fillInDetails),
                  ),
                  const Icon(Icons.chevron_right),
                ],
              ),
            ),
            if (item.draftLabelFailed)
              Text(
                t.ui.form.draftLabelFailed,
                style: TextStyle(color: colorScheme.error, fontSize: 12),
              ),
          ],
        );
      },
    );
  }

  bool _belongsTo(FormItem? errorItem, NestedItem ancestor) {
    var node = errorItem?.group.owner;
    while (node != null) {
      if (node.parentItem == ancestor) {
        return true;
      }
      node = node.parentItem?.group.owner;
    }
    return false;
  }
}

class ExistingEntityActions extends StatelessWidget {
  const ExistingEntityActions({required this.item, super.key});

  final NestedItem item;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return Wrap(
      spacing: appInputSpacing / 2,
      children: [
        OutlinedButton.icon(
          onPressed: () => openExternal(entityPath(item.existingUri!)),
          icon: const Icon(Icons.open_in_new, size: 16),
          label: Text(t.ui.actions.visit),
        ),
        OutlinedButton.icon(
          onPressed: item.clearExisting,
          icon: const Icon(Icons.edit, size: 16),
          label: Text(t.ui.actions.change),
        ),
      ],
    );
  }
}
