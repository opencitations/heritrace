// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../common/async_view.dart';
import '../common/dialogs.dart';
import '../common/primary_source_dialog.dart';
import '../common/reference_views.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
import '../session/session_controller.dart';
import 'merge_repository.dart';

class MergePage extends ConsumerWidget {
  const MergePage({
    required this.subject,
    required this.otherSubject,
    super.key,
  });

  final String? subject;
  final String? otherSubject;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    if (subject == null || otherSubject == null) {
      return Center(child: Text(t.ui.merge.missingEntities));
    }
    final key = (subject: subject!, otherSubject: otherSubject!);
    final comparison = ref.watch(mergeComparisonProvider(key));
    return AsyncView(
      value: comparison,
      onRetry: () => ref.invalidate(mergeComparisonProvider(key)),
      builder: (data) => _MergeBody(comparison: data),
    );
  }
}

class _MergeBody extends ConsumerWidget {
  const _MergeBody({required this.comparison});

  final MergeComparison comparison;

  Future<void> _confirm(BuildContext context, WidgetRef ref) async {
    final t = Translations.of(context);
    final choice = await showPrimarySourceDialog(
      context,
      defaultPrimarySource: ref
          .read(sessionProvider)
          .value!
          .defaultPrimarySource,
      confirmLabel: t.ui.merge.confirm,
    );
    if (choice == null || !context.mounted) {
      return;
    }
    final ok = await runWithProgress(
      context,
      message: t.ui.merge.merging,
      action: () => ref
          .read(mergeRepositoryProvider)
          .merge(
            keepUri: comparison.keep.uri,
            deleteUri: comparison.delete.uri,
            primarySource: choice.url,
            saveDefaultSource: choice.saveAsDefault,
          ),
    );
    if (!ok || !context.mounted) {
      return;
    }
    if (choice.saveAsDefault) {
      ref.read(sessionProvider.notifier).setDefaultPrimarySource(choice.url);
    }
    context.go(entityPath(comparison.keep.uri));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final colorScheme = Theme.of(context).colorScheme;
    final wide = MediaQuery.sizeOf(context).width > 900;
    final cards = [
      _MergeCard(
        entity: comparison.delete,
        title: t.ui.merge.deleteCard,
        icon: Icons.delete,
        color: colorScheme.error,
      ),
      _MergeCard(
        entity: comparison.keep,
        title: t.ui.merge.keepCard,
        icon: Icons.check_circle,
        color: colorScheme.primary,
      ),
    ];
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            t.ui.merge.title,
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: appSectionSpacing),
          Center(
            child: Column(
              children: [
                Icon(
                  Icons.arrow_circle_right,
                  size: 40,
                  color: colorScheme.primary,
                ),
                Text(
                  t.ui.merge.mergeInto,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(height: appInputSpacing),
          if (wide)
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(child: cards[0]),
                  const SizedBox(width: appSectionSpacing),
                  Expanded(child: cards[1]),
                ],
              ),
            )
          else ...[
            cards[0],
            const SizedBox(height: appSectionSpacing),
            cards[1],
          ],
          const SizedBox(height: appSectionSpacing),
          _Explanation(
            icon: Icons.input,
            color: colorScheme.primary,
            title: t.ui.merge.propertiesTitle,
            text: t.ui.merge.propertiesText,
          ),
          _Explanation(
            icon: Icons.link,
            color: colorScheme.primary,
            title: t.ui.merge.referencesTitle,
            text: t.ui.merge.referencesText,
          ),
          _Explanation(
            icon: Icons.delete,
            color: colorScheme.error,
            title: t.ui.merge.deletionTitle,
            text: t.ui.merge.deletionText,
          ),
          const SizedBox(height: appSectionSpacing),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              OutlinedButton.icon(
                onPressed: () => context.go(entityPath(comparison.keep.uri)),
                icon: const Icon(Icons.close),
                label: Text(t.ui.actions.cancel),
              ),
              FilledButton.icon(
                onPressed: () => _confirm(context, ref),
                icon: const Icon(Icons.check),
                label: Text(t.ui.merge.confirm),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MergeCard extends StatelessWidget {
  const _MergeCard({
    required this.entity,
    required this.title,
    required this.icon,
    required this.color,
  });

  final MergeEntity entity;
  final String title;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    final textTheme = Theme.of(context).textTheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(appCardPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: color),
                const SizedBox(width: appInputSpacing / 2),
                Expanded(
                  child: Text(
                    title,
                    style: textTheme.titleMedium?.copyWith(color: color),
                  ),
                ),
              ],
            ),
            const SizedBox(height: appInputSpacing / 2),
            Tooltip(message: entity.uri, child: Text(entity.label)),
            const SizedBox(height: appInputSpacing / 2),
            Chip(label: Text(entity.typeLabel)),
            const SizedBox(height: appInputSpacing),
            Text(t.ui.merge.properties, style: textTheme.titleSmall),
            if (entity.properties.isEmpty)
              Text(
                t.ui.merge.noProperties,
                style: const TextStyle(fontStyle: FontStyle.italic),
              ),
            for (final property in entity.properties) ...[
              const Divider(),
              Tooltip(
                message: property.predicate,
                child: Text(
                  property.label,
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
              for (final value in property.values)
                Padding(
                  padding: const EdgeInsets.only(left: appInputSpacing, top: 2),
                  child: value.isUri
                      ? LinkText(
                          label: value.readableLabel,
                          onTap: () => openExternal(entityPath(value.value)),
                        )
                      : Text(value.readableLabel),
                ),
            ],
            const SizedBox(height: appInputSpacing),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                onPressed: () => openExternal(entityPath(entity.uri)),
                icon: const Icon(Icons.open_in_new, size: 16),
                label: Text(t.ui.merge.viewDetails),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Explanation extends StatelessWidget {
  const _Explanation({
    required this.icon,
    required this.color,
    required this.title,
    required this.text,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: appInputSpacing),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color),
          const SizedBox(width: appInputSpacing),
          Expanded(
            child: Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: '$title ',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  TextSpan(text: text),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
