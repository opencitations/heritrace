// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';

import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import 'async_view.dart';

Future<bool> showConfirmDialog(
  BuildContext context, {
  required String title,
  required String message,
  required String confirmLabel,
  bool destructive = false,
}) async {
  final t = Translations.of(context);
  final colorScheme = Theme.of(context).colorScheme;
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: Text(t.ui.actions.cancel),
        ),
        FilledButton(
          style: destructive
              ? FilledButton.styleFrom(backgroundColor: colorScheme.error)
              : null,
          onPressed: () => Navigator.of(context).pop(true),
          child: Text(confirmLabel),
        ),
      ],
    ),
  );
  return result ?? false;
}

Future<void> showMessageDialog(
  BuildContext context, {
  required String title,
  required String message,
}) {
  final t = Translations.of(context);
  return showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(child: SelectableText(message)),
      actions: [
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(t.ui.actions.ok),
        ),
      ],
    ),
  );
}

Future<void> showErrorDialog(BuildContext context, Object error) {
  final t = Translations.of(context);
  return showMessageDialog(
    context,
    title: t.ui.errors.title,
    message: describeError(context, error),
  );
}

Future<bool> runWithProgress(
  BuildContext context, {
  required String message,
  required Future<void> Function() action,
}) async {
  final navigator = Navigator.of(context, rootNavigator: true);
  showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (context) => PopScope(
      canPop: false,
      child: AlertDialog(
        content: Row(
          children: [
            const CircularProgressIndicator(),
            const SizedBox(width: appSectionSpacing),
            Expanded(child: Text(message)),
          ],
        ),
      ),
    ),
  );
  try {
    await action();
    navigator.pop();
    return true;
  } on Exception catch (error) {
    navigator.pop();
    if (context.mounted) {
      await showErrorDialog(context, error);
    }
    return false;
  }
}
