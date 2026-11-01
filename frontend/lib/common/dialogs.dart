// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../design/controls.dart';
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
  final result = await showCupertinoDialog<bool>(
    context: context,
    builder: (context) => AppDialog(
      title: title,
      content: Text(message),
      actions: [
        AppButton(
          variant: AppButtonVariant.tinted,
          onPressed: () => Navigator.of(context).pop(false),
          label: t.ui.actions.cancel,
        ),
        AppButton(
          variant: AppButtonVariant.filled,
          destructive: destructive,
          onPressed: () => Navigator.of(context).pop(true),
          label: confirmLabel,
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
  return showCupertinoDialog<void>(
    context: context,
    builder: (context) => AppDialog(
      title: title,
      content: AppSelectable(child: Text(message)),
      actions: [
        AppButton(
          variant: AppButtonVariant.filled,
          onPressed: () => Navigator.of(context).pop(),
          label: t.ui.actions.ok,
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
  showCupertinoDialog<void>(
    context: context,
    builder: (context) => PopScope(
      canPop: false,
      child: AppDialog(
        content: Row(
          children: [
            const CupertinoActivityIndicator(),
            const SizedBox(width: appInputSpacing),
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
