// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';

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
  return showDialog<PrimarySourceChoice>(
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
    return AlertDialog(
      title: Text(t.ui.primarySource.title),
      content: SizedBox(
        width: 480,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.description ?? t.ui.primarySource.description),
            const SizedBox(height: appInputSpacing),
            TextField(
              controller: _controller,
              autofocus: true,
              keyboardType: TextInputType.url,
              decoration: InputDecoration(
                border: const OutlineInputBorder(),
                hintText: t.ui.primarySource.hint,
                errorText: _error,
              ),
              onSubmitted: (_) => _confirm(),
            ),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              value: _saveAsDefault,
              onChanged: (value) =>
                  setState(() => _saveAsDefault = value ?? false),
              title: Text(t.ui.primarySource.saveAsDefault),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(t.ui.actions.cancel),
        ),
        FilledButton(
          onPressed: _confirm,
          child: Text(widget.confirmLabel ?? t.ui.primarySource.confirm),
        ),
      ],
    );
  }
}
