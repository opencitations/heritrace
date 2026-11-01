// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../common/dialogs.dart';
import '../common/reference_views.dart';
import '../common/references.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
import 'history_models.dart';
import 'history_repository.dart';

String formatTimestamp(String iso) {
  final parsed = DateTime.tryParse(iso);
  if (parsed == null) {
    return iso;
  }
  return DateFormat.yMMMMd().add_Hms().format(parsed.toLocal());
}

class MetadataRow extends StatelessWidget {
  const MetadataRow({required this.label, required this.child, super.key});

  final String label;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    const labelStyle = TextStyle(fontWeight: FontWeight.bold);
    return Padding(
      padding: const EdgeInsets.only(bottom: appInputSpacing / 2),
      child: MediaQuery.sizeOf(context).width < appCompactWidth
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: labelStyle),
                child,
              ],
            )
          : Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('$label: ', style: labelStyle),
                Expanded(child: child),
              ],
            ),
    );
  }
}

class ModificationsView extends StatelessWidget {
  const ModificationsView({required this.modifications, super.key});

  final Modifications modifications;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          t.ui.history.modifications,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        if (modifications.additions.isNotEmpty)
          _ModificationList(
            title: t.ui.history.additions,
            icon: CupertinoIcons.plus_circle_fill,
            color: CupertinoColors.systemGreen,
            entries: modifications.additions,
          ),
        if (modifications.deletions.isNotEmpty)
          _ModificationList(
            title: t.ui.history.deletions,
            icon: CupertinoIcons.minus_circle_fill,
            color: AppColors.error,
            entries: modifications.deletions,
          ),
      ],
    );
  }
}

class _ModificationList extends StatelessWidget {
  const _ModificationList({
    required this.title,
    required this.icon,
    required this.color,
    required this.entries,
  });

  final String title;
  final IconData icon;
  final Color color;
  final List<Modification> entries;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: appInputSpacing / 2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IconLabel(
            icon: icon,
            label: Text(title),
            color: color,
            style: const TextStyle(fontStyle: FontStyle.italic),
          ),
          for (final entry in entries)
            Padding(
              padding: const EdgeInsets.only(
                left: appInputSpacing,
                top: appInputSpacing / 2,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entry.position == null
                        ? entry.predicateLabel
                        : '${entry.predicateLabel} #${entry.position}',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  Text(entry.objectLabel),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class AgentAndSource extends StatelessWidget {
  const AgentAndSource({required this.agent, required this.source, super.key});

  final AgentRef agent;
  final SourceRef source;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MetadataRow(
          label: t.ui.history.responsibleAgent,
          child: AgentRefView(agent: agent),
        ),
        MetadataRow(
          label: t.ui.history.primarySource,
          child: SourceRefView(source: source),
        ),
      ],
    );
  }
}

Future<void> restoreVersion(
  BuildContext context,
  WidgetRef ref, {
  required String uri,
  required String timestamp,
}) async {
  final t = Translations.of(context);
  final ok = await runWithProgress(
    context,
    message: t.ui.history.restoring,
    action: () => ref.read(historyRepositoryProvider).restore(uri, timestamp),
  );
  if (ok && context.mounted) {
    context.go(entityPath(uri));
  }
}

class BreadcrumbSeparator extends StatelessWidget {
  const BreadcrumbSeparator({super.key});

  @override
  Widget build(BuildContext context) => const Icon(
    CupertinoIcons.chevron_right,
    size: 16,
    color: AppColors.secondaryText,
  );
}
