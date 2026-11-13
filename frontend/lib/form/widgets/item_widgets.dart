// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';

import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../design/date_time_sheet.dart';
import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../field_def.dart';
import '../form_model.dart';
import '../form_scope.dart';
import 'entity_autocomplete.dart';
import 'entity_form.dart';
import 'field_group_widget.dart';
import 'language_picker.dart';
import 'nested_dialog.dart';
import 'option_sheet.dart';

TextInputType valueKeyboardType(FieldDef def) => def.isInteger
    ? TextInputType.numberWithOptions(signed: def.acceptsNegative)
    : switch (def.inputType) {
        'number' => const TextInputType.numberWithOptions(
          decimal: true,
          signed: true,
        ),
        'url' => TextInputType.url,
        'textarea' => TextInputType.multiline,
        _ => TextInputType.text,
      };

List<TextInputFormatter>? valueInputFormatters(FieldDef def) => def.isInteger
    ? [
        def.acceptsNegative
            ? FilteringTextInputFormatter.allow(RegExp(r'^-|\d'))
            : FilteringTextInputFormatter.digitsOnly,
      ]
    : null;

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
      NestedItem(:final def) when def.detailsEditor => NestedFields(
        item: item as NestedItem,
      ),
      NestedItem(:final def) when def.autocomplete => EntityAutocompleteField(
        item: item as NestedItem,
      ),
      NestedItem() => NestedTile(item: item as NestedItem),
      OrItem() => OrSelector(item: item as OrItem),
    };
  }
}

String? itemErrorText(BuildContext context, FormItem item) {
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
    final field = AppTextField(
      controller: _controller,
      focusNode: widget.item.focusNode,
      maxLines: multiline ? 5 : 1,
      keyboardType: valueKeyboardType(def),
      inputFormatters: valueInputFormatters(def),
      placeholder: def.displayName,
      errorText: itemErrorText(context, widget.item),
      onChanged: widget.item.setValue,
    );
    if (!def.withLanguage) {
      return field;
    }
    final item = widget.item;
    return _WithLanguage(
      language: item.language,
      taken: item.group.usedLanguages(except: item),
      onChanged: item.setLanguage,
      child: field,
    );
  }
}

/// A value of a field with languages, followed by the button that picks its
/// language.
class _WithLanguage extends StatelessWidget {
  const _WithLanguage({
    required this.language,
    required this.taken,
    required this.onChanged,
    required this.child,
  });

  final String? language;
  final Set<String?> taken;
  final ValueChanged<String?> onChanged;
  final Widget child;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    spacing: appInputSpacing / 2,
    children: [
      Expanded(child: child),
      LanguageButton(language: language, taken: taken, onChanged: onChanged),
    ],
  );
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
            DateTypeMenu(
              value: item.dateType,
              allowed: allowed,
              onChanged: item.setDateType,
            ),
            const SizedBox(width: appInputSpacing),
          ],
          Expanded(
            child: AppTextField(
              controller: _controller,
              focusNode: item.focusNode,
              placeholder: switch (item.dateType) {
                DateType.date => 'YYYY-MM-DD',
                DateType.month => 'YYYY-MM',
                DateType.year => 'YYYY',
              },
              errorText: itemErrorText(context, item),
              suffix: item.dateType == DateType.date
                  ? AppIconButton(
                      label: t.ui.form.pickDate,
                      icon: CupertinoIcons.calendar,
                      onPressed: () => _pickDate(context),
                    )
                  : null,
              onChanged: item.setValue,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _pickDate(BuildContext context) async {
    final picked = await showDateTimeSheet(
      context,
      initial: DateTime.tryParse(widget.item.value) ?? DateTime.now(),
      doneLabel: Translations.of(context).ui.actions.done,
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
      builder: (context, _) => OptionsButton<String?>(
        title: def.displayName,
        value: item.value,
        focusNode: item.focusNode,
        errorText: itemErrorText(context, item),
        options: [
          AppMenuOption(null, t.ui.form.selectOption),
          for (final value in def.optionalValues)
            AppMenuOption(
              value,
              def.optionalValueLabel(value),
              description: def.optionalValueDescriptions[value],
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
    return MandatoryValueText(item.def.hasValueLabel ?? item.def.hasValue!);
  }
}

/// A fixed value with a mark that explains it cannot change. The whole row
/// opens the explanation, so the target is wider than the mark alone while
/// the row keeps the height of the other values.
class MandatoryValueText extends StatelessWidget {
  const MandatoryValueText(this.label, {super.key});

  final String label;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return AppTooltip(
      message: t.ui.form.mandatoryValue,
      child: SelectionContainer.disabled(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            minHeight: kCupertinoButtonMinSize[CupertinoButtonSize.medium]!,
          ),
          child: Align(
            alignment: AlignmentDirectional.centerStart,
            widthFactor: 1,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Flexible(child: Text(label)),
                const SizedBox(width: appInputSpacing / 2),
                const TextIcon(
                  CupertinoIcons.question_circle,
                  color: AppColors.primary,
                ),
              ],
            ),
          ),
        ),
      ),
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
          AppMenuButton<FieldDef?>(
            value: item.selected,
            focusNode: item.focusNode,
            errorText: itemErrorText(context, item),
            options: [
              AppMenuOption(null, t.ui.form.selectOption),
              for (final option in item.def.or!)
                AppMenuOption(option, option.displayName),
            ],
            onChanged: item.select,
          ),
          if (item.selectedItem != null) ...[
            const SizedBox(height: appInputSpacing),
            Padding(
              padding: const EdgeInsets.only(left: appInputSpacing),
              child: ItemWidget(item: item.selectedItem!),
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
    return ListenableBuilder(
      listenable: Listenable.merge([item, item.draftLabel]),
      builder: (context, _) {
        final draft = item.draftLabel.value;
        final scope = FormScope.of(context);
        final hasErrors =
            scope.validationStarted &&
            scope.errors.any((error) => _belongsTo(error.item, item));
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            CupertinoButton(
              focusNode: item.focusNode,
              padding: EdgeInsets.zero,
              minimumSize: Size.zero,
              onPressed: () => showNestedDialog(context, item),
              child: SelectionContainer.disabled(
                child: Container(
                  padding: const EdgeInsets.all(appInputSpacing),
                  decoration: BoxDecoration(
                    color: AppColors.of(context).fieldFill,
                    borderRadius: BorderRadius.circular(appRadius),
                    border: hasErrors
                        ? Border.all(color: AppColors.of(context).error)
                        : null,
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          item.existingLabel ??
                              draft.label ??
                              t.ui.form.fillInDetails,
                          style: TextStyle(
                            color: hasErrors
                                ? AppColors.of(context).error
                                : AppColors.of(context).label,
                          ),
                        ),
                      ),
                      Icon(
                        CupertinoIcons.chevron_right,
                        size: 18,
                        color: AppColors.of(context).secondaryText,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            if (draft.failed)
              Text(
                t.ui.form.draftLabelFailed,
                style: AppTextStyles.of(context).caption
                    .copyWith(color: AppColors.of(context).error),
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

class DateTypeMenu extends StatelessWidget {
  const DateTypeMenu({
    required this.value,
    required this.allowed,
    required this.onChanged,
    super.key,
  });

  final DateType value;
  final List<DateType> allowed;
  final ValueChanged<DateType> onChanged;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return AppMenuButton<DateType>(
      value: value,
      options: [
        for (final type in allowed)
          AppMenuOption(type, switch (type) {
            DateType.date => t.ui.form.dateTypeDate,
            DateType.month => t.ui.form.dateTypeMonth,
            DateType.year => t.ui.form.dateTypeYear,
          }),
      ],
      onChanged: onChanged,
    );
  }
}

/// The fields of a nested entity edited in place (`shui:DetailsEditor`). A
/// single field reads as the value itself, without a heading.
class NestedFields extends StatelessWidget {
  const NestedFields({required this.item, super.key});

  final NestedItem item;

  @override
  Widget build(BuildContext context) {
    final paths = item.def.detailPaths;
    final shown = item.child.shownGroups(paths).toList();
    if (shown.length == 1) {
      return FieldGroupWidget(group: shown.single);
    }
    return EntityForm(node: item.child, paths: paths);
  }
}
