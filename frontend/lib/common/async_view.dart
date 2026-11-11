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
    this.header,
    super.key,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final VoidCallback? onRetry;

  /// Stays in place while the data loads, where [builder] draws it again.
  final Widget? header;

  @override
  Widget build(BuildContext context) {
    final margin = pageMargin(context);
    final pending = value.when(
      data: (_) => null,
      loading: () => const Center(child: CupertinoActivityIndicator()),
      error: (error, _) => Padding(
        padding: margin,
        child: ErrorView(error: error, onRetry: onRetry),
      ),
    );
    if (pending == null) {
      return builder(value.requireValue);
    }
    if (header == null) {
      return pending;
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: margin.copyWith(bottom: appInputSpacing),
          child: header,
        ),
        Expanded(child: pending),
      ],
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
          Icon(
            CupertinoIcons.exclamationmark_circle,
            color: AppColors.of(context).error,
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
