// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../common/async_view.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
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
    final textTheme = Theme.of(context).textTheme;
    final uri = version.entityUri;
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              TextButton(
                onPressed: () => context.go(entityPath(uri)),
                child: Text(
                  version.entityLabel,
                  style: const TextStyle(fontStyle: FontStyle.italic),
                ),
              ),
              const Icon(Icons.chevron_right, size: 18),
              TextButton(
                onPressed: () => context.go(entityHistoryPath(uri)),
                child: Text(t.ui.history.breadcrumb),
              ),
              const Icon(Icons.chevron_right, size: 18),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: appInputSpacing,
                ),
                child: Text(
                  t.ui.version.breadcrumb(number: version.versionNumber),
                ),
              ),
            ],
          ),
          const SizedBox(height: appInputSpacing),
          Text(
            t.ui.version.title(
              number: version.versionNumber,
              label: version.entityLabel,
            ),
            style: textTheme.headlineMedium,
          ),
          const SizedBox(height: appSectionSpacing),
          Wrap(
            spacing: appInputSpacing,
            runSpacing: appInputSpacing,
            children: [
              OutlinedButton.icon(
                onPressed: () => context.go(entityHistoryPath(uri)),
                icon: const Icon(Icons.history),
                label: Text(t.ui.entity.timeMachine),
              ),
              if (version.nextTimestamp != null)
                FilledButton.icon(
                  onPressed: () => restoreVersion(
                    context,
                    ref,
                    uri: uri,
                    timestamp: version.timestamp,
                  ),
                  icon: const Icon(Icons.restore),
                  label: Text(t.ui.version.restore),
                ),
              OutlinedButton.icon(
                onPressed: version.prevTimestamp == null
                    ? null
                    : () => context.go(
                        entityVersionPath(uri, version.prevTimestamp!),
                      ),
                icon: const Icon(Icons.arrow_back),
                label: Text(t.ui.version.previous),
              ),
              OutlinedButton.icon(
                onPressed: version.nextTimestamp == null
                    ? null
                    : () => context.go(
                        entityVersionPath(uri, version.nextTimestamp!),
                      ),
                icon: const Icon(Icons.arrow_forward),
                label: Text(t.ui.version.next),
              ),
            ],
          ),
          const SizedBox(height: appSectionSpacing),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(appCardPadding),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    t.ui.version.metadata(number: version.versionNumber),
                    style: textTheme.titleMedium,
                  ),
                  const SizedBox(height: appInputSpacing),
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
          ),
          const SizedBox(height: appSectionSpacing),
          if (version.isDeletionSnapshot)
            Text(t.ui.version.deletionSnapshot)
          else
            for (final group in version.groups)
              Padding(
                padding: const EdgeInsets.only(bottom: appSectionSpacing),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(group.displayName, style: textTheme.titleMedium),
                    for (final value in group.values)
                      Padding(
                        padding: const EdgeInsets.only(
                          left: appInputSpacing,
                          top: appInputSpacing / 2,
                        ),
                        child: SelectableText(value),
                      ),
                  ],
                ),
              ),
        ],
      ),
    );
  }
}
