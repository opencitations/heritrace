// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../common/async_view.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import '../navigation/entity_store.dart';
import 'history_models.dart';
import 'history_repository.dart';
import 'history_widgets.dart';

class HistoryPage extends ConsumerWidget {
  const HistoryPage({required this.uri, super.key});

  final String uri;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final history = ref.watch(entityHistoryProvider(uri));
    return AsyncView(
      value: history,
      onRetry: () => ref.invalidate(entityHistoryProvider(uri)),
      builder: (data) => SingleChildScrollView(
        padding: pageMargin(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AppBreadcrumbs(
              crumbs: [
                AppBreadcrumb(
                  data.entityLabel,
                  onPressed: () =>
                      context.go(context.entityStore.entityPath(uri)),
                ),
                AppBreadcrumb(t.ui.history.title),
              ],
            ),
            const SizedBox(height: appInputSpacing),
            AppHeading(
              t.ui.history.title,
              style: AppTextStyles.of(context).pageTitle,
            ),
            const SizedBox(height: appSectionSpacing),
            for (final snapshot in data.snapshots.reversed)
              _SnapshotCard(
                snapshot: snapshot,
                entityUri: data.entityUri,
                isFirst: snapshot == data.snapshots.last,
                isLast: snapshot == data.snapshots.first,
              ),
          ],
        ),
      ),
    );
  }
}

class _SnapshotCard extends ConsumerWidget {
  const _SnapshotCard({
    required this.snapshot,
    required this.entityUri,
    required this.isFirst,
    required this.isLast,
  });

  static const _railWidth = 32.0;

  final Snapshot snapshot;
  final String entityUri;
  final bool isFirst;
  final bool isLast;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final styles = AppTextStyles.of(context);
    final colors = AppColors.of(context);
    final isCurrent = snapshot.endTimestamp == null;
    final titleStyle = styles.sectionTitle;
    final nodeCenter =
        appCardPadding +
        MediaQuery.textScalerOf(context).scale(titleStyle.fontSize!) *
            titleStyle.height! /
            2;
    return Stack(
      children: [
        if (!(isFirst && isLast))
          Positioned(
            left: _railWidth / 2 - 1,
            top: isFirst ? nodeCenter : 0,
            bottom: isLast ? null : 0,
            height: isLast ? nodeCenter : null,
            width: 2,
            child: ColoredBox(color: colors.separator),
          ),
        Positioned(
          top: nodeCenter - 10,
          left: _railWidth / 2 - 10,
          width: 20,
          height: 20,
          child: DecoratedBox(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isCurrent
                  ? AppColors.primary.withValues(alpha: 0.2)
                  : null,
            ),
            child: Center(
              child: Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: isCurrent ? AppColors.primary : colors.surface,
                  border: isCurrent
                      ? null
                      : Border.all(color: colors.inactive, width: 2),
                ),
              ),
            ),
          ),
        ),
        Padding(
          padding: EdgeInsets.only(
            left: _railWidth,
            bottom: isLast ? 0 : appSectionSpacing,
          ),
          child: AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppHeading(
                  t.ui.history.snapshot(index: snapshot.index),
                  style: titleStyle,
                ),
                const SizedBox(height: 4),
                Text(
                  isCurrent
                      ? t.ui.history.since(
                          start: formatTimestamp(snapshot.timestamp),
                        )
                      : t.ui.history.between(
                          start: formatTimestamp(snapshot.timestamp),
                          end: formatTimestamp(snapshot.endTimestamp!),
                        ),
                  style: styles.secondary,
                ),
                const SizedBox(height: appInputSpacing),
                AgentAndSource(
                  agent: snapshot.responsibleAgent,
                  source: snapshot.primarySource,
                ),
                MetadataRow(
                  label: t.ui.history.description,
                  child: Text(snapshot.description),
                ),
                if (snapshot.modifications != null &&
                    !snapshot.modifications!.isEmpty) ...[
                  const SizedBox(height: appInputSpacing),
                  ModificationsView(modifications: snapshot.modifications!),
                ],
                const SizedBox(height: appInputSpacing),
                Wrap(
                  spacing: appInputSpacing,
                  children: [
                    AppButton(
                      variant: AppButtonVariant.tinted,
                      onPressed: () => context.go(
                        context.entityStore.versionPath(
                          entityUri,
                          snapshot.timestamp,
                        ),
                      ),
                      label: t.ui.history.viewVersion,
                    ),
                    if (snapshot.canRestore)
                      AppButton(
                        variant: AppButtonVariant.filled,
                        onPressed: () => restoreVersion(
                          context,
                          ref,
                          uri: entityUri,
                          timestamp: snapshot.timestamp,
                        ),
                        icon: CupertinoIcons.arrow_counterclockwise,
                        label: t.ui.history.restore,
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
