// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';

import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../form_model.dart';
import '../form_scope.dart';
import '../validator.dart';
import 'nested_dialog.dart';

class ValidationSummary extends StatelessWidget {
  const ValidationSummary({super.key});

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final scope = FormScope.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    if (!scope.validationStarted || scope.errors.isEmpty) {
      return const SizedBox.shrink();
    }
    final groups = <String, List<ValidationError>>{};
    for (final error in scope.errors) {
      groups.putIfAbsent(error.path.join(' › '), () => []).add(error);
    }
    // The summary sits outside the scrolling form, so that its changes never
    // move the fields under the pointer.
    return Container(
      margin: const EdgeInsets.only(top: appInputSpacing),
      constraints: BoxConstraints(
        maxHeight: MediaQuery.sizeOf(context).height * 0.3,
      ),
      decoration: BoxDecoration(
        color: colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(appCardPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              t.ui.form.errorsTitle(count: scope.errors.length),
              style: Theme.of(context).textTheme.titleMedium
                  ?.copyWith(color: colorScheme.onErrorContainer),
            ),
            for (final entry in groups.entries) ...[
              const SizedBox(height: appInputSpacing),
              Text(
                entry.key,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: colorScheme.onErrorContainer,
                ),
              ),
              for (final error in entry.value)
                error.item == null
                    ? Text(
                        error.fullMessage,
                        style: TextStyle(color: colorScheme.onErrorContainer),
                      )
                    : TextButton(
                        style: TextButton.styleFrom(
                          foregroundColor: colorScheme.onErrorContainer,
                          alignment: Alignment.centerLeft,
                        ),
                        onPressed: () => focusItem(context, error.item!),
                        child: Text(error.fullMessage),
                      ),
            ],
          ],
        ),
      ),
    );
  }
}

Future<void> focusItem(BuildContext context, FormItem item) async {
  final parent = item.group.owner.parentItem;
  if (parent != null) {
    for (final nested in nestedChain(parent)) {
      if (!context.mounted) {
        return;
      }
      // ignore: unawaited_futures
      showNestedDialog(context, nested);
      await Future<void>.delayed(Duration.zero);
    }
  }
  item.focusNode.requestFocus();
}
