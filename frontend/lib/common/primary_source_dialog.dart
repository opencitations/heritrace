// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../design/controls.dart';
import '../design/spacing.dart';
import '../form/validator.dart';
import '../i18n/translations.g.dart';

class PrimarySourceChoice {
  const PrimarySourceChoice({required this.url, required this.saveAsDefault});

  final String? url;
  final bool saveAsDefault;
}

Future<PrimarySourceChoice?> showPrimarySourceDialog(
  BuildContext context, {
  required String? defaultPrimarySource,
  String? confirmLabel,
  String? description,
}) {
  return showCupertinoDialog<PrimarySourceChoice>(
    context: context,
    builder: (context) => _PrimarySourceDialog(
      defaultPrimarySource: defaultPrimarySource,
      confirmLabel: confirmLabel,
      description: description,
    ),
  );
}

class _PrimarySourceDialog extends StatefulWidget {
  const _PrimarySourceDialog({
    required this.defaultPrimarySource,
    required this.confirmLabel,
    required this.description,
  });

  final String? defaultPrimarySource;
  final String? confirmLabel;
  final String? description;

  @override
  State<_PrimarySourceDialog> createState() => _PrimarySourceDialogState();
}

class _PrimarySourceDialogState extends State<_PrimarySourceDialog> {
  late final TextEditingController _controller = TextEditingController(
    text: widget.defaultPrimarySource ?? '',
  );
  bool _saveAsDefault = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _confirm() {
    final t = Translations.of(context);
    final value = _controller.text.trim();
    if (value.isNotEmpty && !isValidUrl(value)) {
      setState(() => _error = t.ui.primarySource.invalidUrl);
      return;
    }
    Navigator.of(context).pop(
      PrimarySourceChoice(
        url: value.isEmpty ? null : value,
        saveAsDefault: _saveAsDefault,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return AppDialog(
      title: t.ui.primarySource.title,
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(widget.description ?? t.ui.primarySource.description),
          const SizedBox(height: appInputSpacing),
          AppTextField(
            controller: _controller,
            autofocus: true,
            keyboardType: TextInputType.url,
            placeholder: t.ui.primarySource.hint,
            errorText: _error,
            onSubmitted: (_) => _confirm(),
          ),
          const SizedBox(height: appInputSpacing),
          GestureDetector(
            onTap: () => setState(() => _saveAsDefault = !_saveAsDefault),
            child: Row(
              children: [
                CupertinoCheckbox(
                  value: _saveAsDefault,
                  onChanged: (value) => setState(() => _saveAsDefault = value!),
                ),
                const SizedBox(width: appInputSpacing / 2),
                Expanded(child: Text(t.ui.primarySource.saveAsDefault)),
              ],
            ),
          ),
        ],
      ),
      actions: [
        AppButton(
          variant: AppButtonVariant.tinted,
          onPressed: () => Navigator.of(context).pop(),
          label: t.ui.actions.cancel,
        ),
        AppButton(
          variant: AppButtonVariant.filled,
          onPressed: _confirm,
          label: widget.confirmLabel ?? t.ui.primarySource.confirm,
        ),
      ],
    );
  }
}
