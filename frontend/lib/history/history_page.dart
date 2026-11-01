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
import '../navigation/app_paths.dart';
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
                  style: const TextStyle(fontStyle: FontStyle.italic),
                  onPressed: () => context.go(entityPath(uri)),
                ),
                AppBreadcrumb(t.ui.history.title),
              ],
            ),
            const SizedBox(height: appInputSpacing),
            Text(
              t.ui.history.title,
              style: AppTextStyles.of(context).pageTitle,
            ),
            const SizedBox(height: appSectionSpacing),
            for (final snapshot in data.snapshots.reversed)
              _SnapshotCard(
                snapshot: snapshot,
                entityUri: data.entityUri,
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
    required this.isLast,
  });

  final Snapshot snapshot;
  final String entityUri;
  final bool isLast;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final styles = AppTextStyles.of(context);
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 32,
            child: Column(
              children: [
                Container(
                  width: 16,
                  height: 16,
                  margin: const EdgeInsets.only(top: appCardPadding),
                  decoration: BoxDecoration(
                    color: AppColors.primary,
                    shape: BoxShape.circle,
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(width: 2, color: AppColors.separator),
                  ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: appSectionSpacing),
              child: AppCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      t.ui.history.snapshot(index: snapshot.index),
                      style: styles.sectionTitle,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      snapshot.endTimestamp == null
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
                            entityVersionPath(entityUri, snapshot.timestamp),
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
          ),
        ],
      ),
    );
  }
}
