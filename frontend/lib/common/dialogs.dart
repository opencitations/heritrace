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
    builder: (context) => CupertinoAlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        CupertinoDialogAction(
          onPressed: () => Navigator.of(context).pop(false),
          child: Text(t.ui.actions.cancel),
        ),
        CupertinoDialogAction(
          isDefaultAction: !destructive,
          isDestructiveAction: destructive,
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
  return showCupertinoDialog<void>(
    context: context,
    builder: (context) => CupertinoAlertDialog(
      title: Text(title),
      content: AppSelectable(child: Text(message)),
      actions: [
        CupertinoDialogAction(
          isDefaultAction: true,
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
  showCupertinoDialog<void>(
    context: context,
    builder: (context) => PopScope(
      canPop: false,
      child: CupertinoAlertDialog(
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
