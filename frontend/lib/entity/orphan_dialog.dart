// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';

import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import 'entity_models.dart';

/// Asks whether the orphaned and intermediate entities should be deleted.
/// Returns null when the user cancels, otherwise whether to delete them.
Future<bool?> showOrphanDialog(BuildContext context, OrphanCheck check) {
  final t = Translations.of(context);
  final orphans = check.affectedEntities
      .where((e) => !e.isIntermediate)
      .toList();
  final proxies = check.affectedEntities
      .where((e) => e.isIntermediate)
      .toList();
  final showOrphans = orphans.isNotEmpty && check.orphanStrategy != 'delete';
  final showProxies = proxies.isNotEmpty && check.proxyStrategy != 'delete';
  if (!showOrphans && !showProxies) {
    final deleteOrphans =
        check.orphanStrategy == 'delete' && orphans.isNotEmpty;
    final deleteProxies = check.proxyStrategy == 'delete' && proxies.isNotEmpty;
    return Future.value(deleteOrphans || deleteProxies);
  }
  final colorScheme = Theme.of(context).colorScheme;
  return showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(t.ui.orphans.title),
      content: SizedBox(
        width: 520,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (showOrphans) ...[
                Text(t.ui.orphans.orphansIntro),
                const SizedBox(height: appInputSpacing),
                for (final entity in orphans)
                  _AffectedRow(
                    entity: entity,
                    icon: Icons.remove_circle_outline,
                    color: colorScheme.error,
                  ),
                const SizedBox(height: appSectionSpacing),
              ],
              if (showProxies) ...[
                Text(t.ui.orphans.proxiesIntro),
                const SizedBox(height: appInputSpacing),
                for (final entity in proxies)
                  _AffectedRow(
                    entity: entity,
                    icon: Icons.link,
                    color: colorScheme.tertiary,
                  ),
                const SizedBox(height: appSectionSpacing),
              ],
              Text(t.ui.orphans.question),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: Text(t.ui.orphans.keep),
        ),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: colorScheme.error),
          onPressed: () => Navigator.of(context).pop(true),
          child: Text(t.ui.orphans.delete),
        ),
      ],
    ),
  );
}

class _AffectedRow extends StatelessWidget {
  const _AffectedRow({
    required this.entity,
    required this.icon,
    required this.color,
  });

  final AffectedEntity entity;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: appInputSpacing / 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: appInputSpacing / 2),
          Expanded(
            child: Text.rich(
              TextSpan(
                children: [
                  TextSpan(text: entity.label),
                  TextSpan(
                    text: ' (${entity.type})',
                    style: textTheme.bodySmall,
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
