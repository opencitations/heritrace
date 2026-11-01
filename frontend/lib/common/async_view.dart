// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_exception.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';

String describeError(BuildContext context, Object error) {
  final t = Translations.of(context);
  return switch (error) {
    ApiException(:final message) => message,
    NetworkException() => t.ui.errors.network,
    _ => error.toString(),
  };
}

class AsyncView<T> extends StatelessWidget {
  const AsyncView({
    required this.value,
    required this.builder,
    this.onRetry,
    super.key,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      data: builder,
      loading: () => const Center(child: CupertinoActivityIndicator()),
      error: (error, _) => ErrorView(error: error, onRetry: onRetry),
    );
  }
}

class ErrorView extends StatelessWidget {
  const ErrorView({required this.error, this.onRetry, super.key});

  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            CupertinoIcons.exclamationmark_circle,
            color: AppColors.error,
            size: 40,
          ),
          const SizedBox(height: appInputSpacing),
          Text(describeError(context, error), textAlign: TextAlign.center),
          if (onRetry != null) ...[
            const SizedBox(height: appInputSpacing),
            AppButton(
              variant: AppButtonVariant.tinted,
              onPressed: onRetry,
              label: t.ui.actions.retry,
            ),
          ],
        ],
      ),
    );
  }
}
