// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../../design/app_theme.dart';
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
        color: AppColors.of(context).errorTint,
        borderRadius: BorderRadius.circular(appRadius),
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(appCardPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              t.ui.form.errorsTitle(count: scope.errors.length),
              style: AppTextStyles.of(context).heading
                  .copyWith(color: AppColors.of(context).error),
            ),
            for (final entry in groups.entries) ...[
              const SizedBox(height: appInputSpacing),
              Text(
                entry.key,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              for (final error in entry.value)
                error.item == null
                    ? Text(error.fullMessage)
                    : CupertinoButton(
                        sizeStyle: CupertinoButtonSize.small,
                        minimumSize: const Size(
                          0,
                          kMinInteractiveDimensionCupertino,
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        alignment: Alignment.centerLeft,
                        foregroundColor: AppColors.of(context).error,
                        onPressed: () => focusItem(context, error.item!),
                        child: SelectionContainer.disabled(
                          child: Text(
                            error.fullMessage,
                            style: const TextStyle(
                              decoration: TextDecoration.underline,
                            ),
                          ),
                        ),
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
