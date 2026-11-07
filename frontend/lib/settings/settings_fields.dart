// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/date_time_sheet.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';

/// A labelled group of fields on the grey page background.
class SettingsGroup extends StatelessWidget {
  const SettingsGroup({required this.title, required this.children, super.key});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      header: AppHeading(title, style: AppTextStyles.of(context).groupHeader),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        spacing: appSectionSpacing,
        children: children,
      ),
    );
  }
}

/// A setting shown as text, outside edit mode.
class SettingsValue extends StatelessWidget {
  const SettingsValue({
    required this.label,
    required this.value,
    this.hint,
    this.link,
    super.key,
  });

  final String label;
  final String? value;
  final String? hint;
  final Widget? link;

  @override
  Widget build(BuildContext context) {
    final empty = value == null || value!.isEmpty;
    return AppLabeledField(
      label: label,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            empty ? Translations.of(context).ui.settings.system.notSet : value!,
            style: empty
                ? TextStyle(color: AppColors.of(context).secondaryText)
                : null,
          ),
          if (hint != null) FieldCaption(hint!),
          if (link != null)
            Padding(
              padding: const EdgeInsets.only(top: appCaptionSpacing),
              child: link,
            ),
        ],
      ),
    );
  }
}

/// A text field that keeps its own text, so the cursor stays put while the
/// value it reports is converted on every keystroke. Without [onChanged] it
/// shows the value as text.
class SettingsTextField extends StatefulWidget {
  const SettingsTextField({
    required this.label,
    required this.value,
    required this.onChanged,
    this.errorText,
    this.hint,
    this.keyboardType,
    this.validator,
    super.key,
  });

  final String label;
  final String value;
  final ValueChanged<String>? onChanged;
  final String? errorText;
  final String? hint;
  final TextInputType? keyboardType;

  /// Returns the error for a text, shown once the field loses focus so that
  /// half-typed text is not flagged.
  final String? Function(String text)? validator;

  @override
  State<SettingsTextField> createState() => _SettingsTextFieldState();
}

class _SettingsTextFieldState extends State<SettingsTextField> {
  late final _controller = TextEditingController(text: widget.value);
  final _focus = FocusNode();

  @override
  void initState() {
    super.initState();
    _focus.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _controller.dispose();
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.onChanged == null) {
      return SettingsValue(
        label: widget.label,
        value: widget.value,
        hint: widget.hint,
      );
    }
    return AppLabeledField(
      label: widget.label,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AppTextField(
            controller: _controller,
            focusNode: _focus,
            errorText:
                (_focus.hasFocus
                    ? null
                    : widget.validator?.call(widget.value)) ??
                widget.errorText,
            keyboardType: widget.keyboardType,
            onChanged: widget.onChanged,
          ),
          if (widget.hint != null) FieldCaption(widget.hint!),
        ],
      ),
    );
  }
}

/// A date and time typed by hand or picked on the wheels. A picked moment is
/// written with the time zone of the browser, so the text shows the time the
/// user chose.
class SettingsDateTimeField extends StatefulWidget {
  const SettingsDateTimeField({
    required this.label,
    required this.value,
    required this.onChanged,
    required this.onReadable,
    this.errorText,
    this.hint,
    super.key,
  });

  final String label;
  final String? value;
  final ValueChanged<String?>? onChanged;

  /// Tells whether the text can be read as a date and time.
  final ValueChanged<bool> onReadable;
  final String? errorText;
  final String? hint;

  @override
  State<SettingsDateTimeField> createState() => _SettingsDateTimeFieldState();
}

class _SettingsDateTimeFieldState extends State<SettingsDateTimeField> {
  late final _controller = TextEditingController(text: widget.value);
  bool _invalid = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _report(String text) {
    final trimmed = text.trim();
    final invalid = trimmed.isNotEmpty && DateTime.tryParse(trimmed) == null;
    setState(() => _invalid = invalid);
    widget.onReadable(!invalid);
    if (!invalid) {
      widget.onChanged!(trimmed.isEmpty ? null : trimmed);
    }
  }

  Future<void> _pick() async {
    final picked = await showDateTimeSheet(
      context,
      initial: DateTime.tryParse(_controller.text)?.toLocal() ?? DateTime.now(),
      doneLabel: Translations.of(context).ui.actions.done,
      withTime: true,
    );
    if (picked != null) {
      _controller.text = withTimeZone(picked);
      _report(_controller.text);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.onChanged == null) {
      return SettingsValue(
        label: widget.label,
        value: widget.value,
        hint: widget.hint,
      );
    }
    return AppLabeledField(
      label: widget.label,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AppTextField(
            controller: _controller,
            placeholder: 'YYYY-MM-DDThh:mm:ss+hh:mm',
            errorText: _invalid
                ? Translations.of(context).ui.settings.system.invalidDateTime
                : widget.errorText,
            keyboardType: TextInputType.datetime,
            suffix: AppIconButton(
              label: Translations.of(context).ui.settings.system.pickDateTime,
              icon: CupertinoIcons.calendar,
              onPressed: _pick,
            ),
            onChanged: _report,
          ),
          if (widget.hint != null) FieldCaption(widget.hint!),
        ],
      ),
    );
  }
}

String withTimeZone(DateTime local) {
  String twoDigits(int value) => value.toString().padLeft(2, '0');
  final offset = local.timeZoneOffset;
  final minutes = offset.inMinutes.abs();
  final sign = offset.isNegative ? '-' : '+';
  return '${local.toIso8601String().substring(0, 19)}'
      '$sign${twoDigits(minutes ~/ 60)}:${twoDigits(minutes % 60)}';
}

class SettingsNumberField extends StatefulWidget {
  const SettingsNumberField({
    required this.label,
    required this.value,
    required this.onChanged,
    required this.onReadable,
    this.errorText,
    this.hint,
    super.key,
  });

  final String label;
  final int value;
  final ValueChanged<int>? onChanged;

  /// Tells whether the text can be read as a whole number.
  final ValueChanged<bool> onReadable;
  final String? errorText;
  final String? hint;

  @override
  State<SettingsNumberField> createState() => _SettingsNumberFieldState();
}

class _SettingsNumberFieldState extends State<SettingsNumberField> {
  bool _invalid = false;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return SettingsTextField(
      label: widget.label,
      value: widget.value.toString(),
      hint: widget.hint,
      keyboardType: TextInputType.number,
      errorText: _invalid
          ? t.ui.settings.system.invalidNumber
          : widget.errorText,
      onChanged: widget.onChanged == null
          ? null
          : (text) {
              final number = int.tryParse(text.trim());
              setState(() => _invalid = number == null);
              widget.onReadable(number != null);
              if (number != null) {
                widget.onChanged!(number);
              }
            },
    );
  }
}

class SettingsMenu<T> extends StatelessWidget {
  const SettingsMenu({
    required this.label,
    required this.value,
    required this.options,
    required this.onChanged,
    this.errorText,
    this.hint,
    this.link,
    super.key,
  });

  final String label;
  final T value;
  final List<AppMenuOption<T>> options;
  final ValueChanged<T>? onChanged;
  final String? errorText;
  final String? hint;
  final Widget? link;

  @override
  Widget build(BuildContext context) {
    final onChanged = this.onChanged;
    if (onChanged == null) {
      return SettingsValue(
        label: label,
        value: options.firstWhere((option) => option.value == value).label,
        hint: hint,
        link: link,
      );
    }
    return AppLabeledField(
      label: label,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppMenuButton<T>(
            value: value,
            options: options,
            onChanged: onChanged,
            errorText: errorText,
          ),
          if (hint != null) FieldCaption(hint!),
          if (link != null)
            Padding(
              padding: const EdgeInsets.only(top: appCaptionSpacing),
              child: link,
            ),
        ],
      ),
    );
  }
}
