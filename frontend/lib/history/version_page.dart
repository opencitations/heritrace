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
import '../form/widgets/field_group_widget.dart';
import '../i18n/translations.g.dart';
import '../navigation/entity_store.dart';
import 'history_models.dart';
import 'history_repository.dart';
import 'history_widgets.dart';

class VersionPage extends ConsumerWidget {
  const VersionPage({required this.uri, required this.timestamp, super.key});

  final String uri;
  final String timestamp;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final key = (uri: uri, timestamp: timestamp);
    final version = ref.watch(entityVersionProvider(key));
    return AsyncView(
      value: version,
      onRetry: () => ref.invalidate(entityVersionProvider(key)),
      builder: (data) => _VersionBody(version: data),
    );
  }
}

class _VersionBody extends ConsumerWidget {
  const _VersionBody({required this.version});

  final EntityVersion version;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final styles = AppTextStyles.of(context);
    final uri = version.entityUri;
    return SingleChildScrollView(
      padding: pageMargin(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AppBreadcrumbs(
            crumbs: [
              AppBreadcrumb(
                version.entityLabel,
                onPressed: () =>
                    context.go(context.entityStore.entityPath(uri)),
              ),
              AppBreadcrumb(
                t.ui.history.title,
                onPressed: () =>
                    context.go(context.entityStore.historyPath(uri)),
              ),
              AppBreadcrumb(t.ui.version.title(number: version.versionNumber)),
            ],
          ),
          const SizedBox(height: appInputSpacing),
          AppHeading(
            t.ui.version.title(number: version.versionNumber),
            style: styles.pageTitle,
          ),
          const SizedBox(height: appSectionSpacing),
          Wrap(
            spacing: appInputSpacing,
            runSpacing: appInputSpacing,
            children: [
              AppButton(
                variant: AppButtonVariant.tinted,
                onPressed: () =>
                    context.go(context.entityStore.historyPath(uri)),
                icon: CupertinoIcons.clock,
                label: t.ui.history.title,
              ),
              if (version.nextTimestamp != null)
                AppButton(
                  variant: AppButtonVariant.filled,
                  onPressed: () => restoreVersion(
                    context,
                    ref,
                    uri: uri,
                    timestamp: version.timestamp,
                  ),
                  icon: CupertinoIcons.arrow_counterclockwise,
                  label: t.ui.version.restore,
                ),
              AppButton(
                variant: AppButtonVariant.tinted,
                onPressed: version.prevTimestamp == null
                    ? null
                    : () => Router.neglect(
                        context,
                        () => context.go(
                          context.entityStore.versionPath(
                            uri,
                            version.prevTimestamp!,
                          ),
                        ),
                      ),
                icon: CupertinoIcons.arrow_left,
                label: t.ui.version.previous,
              ),
              AppButton(
                variant: AppButtonVariant.tinted,
                onPressed: version.nextTimestamp == null
                    ? null
                    : () => Router.neglect(
                        context,
                        () => context.go(
                          context.entityStore.versionPath(
                            uri,
                            version.nextTimestamp!,
                          ),
                        ),
                      ),
                icon: CupertinoIcons.arrow_right,
                label: t.ui.version.next,
              ),
            ],
          ),
          const SizedBox(height: appSectionSpacing),
          AppCard(
            header: Text(
              t.ui.version.metadata(number: version.versionNumber),
              style: styles.groupHeader,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                MetadataRow(
                  label: t.ui.version.generationTime,
                  child: Text(formatTimestamp(version.generatedAt)),
                ),
                if (version.invalidatedAt != null)
                  MetadataRow(
                    label: t.ui.version.invalidationTime,
                    child: Text(formatTimestamp(version.invalidatedAt!)),
                  ),
                AgentAndSource(
                  agent: version.attributedTo,
                  source: version.primarySource,
                ),
                if (version.description != null)
                  MetadataRow(
                    label: t.ui.history.description,
                    child: Text(version.description!),
                  ),
                if (version.modifications != null &&
                    !version.modifications!.isEmpty) ...[
                  const SizedBox(height: appInputSpacing),
                  ModificationsView(modifications: version.modifications!),
                ],
              ],
            ),
          ),
          const SizedBox(height: appSectionSpacing),
          if (version.isDeletionSnapshot)
            Text(t.ui.version.deletionSnapshot)
          else
            for (final group in version.groups)
              Padding(
                padding: const EdgeInsets.only(bottom: appSectionSpacing),
                child: AppCard(
                  header: PropertyHeading(
                    label: group.displayName,
                    style: styles.groupHeader,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (final (index, value) in group.values.indexed)
                        Padding(
                          padding: listItemSpacing(index),
                          child: Text(value),
                        ),
                    ],
                  ),
                ),
              ),
        ],
      ),
    );
  }
}
