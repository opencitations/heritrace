// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../design/app_theme.dart';
import '../design/controls.dart';
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
  return showCupertinoDialog<bool>(
    context: context,
    barrierDismissible: true,
    builder: (context) => AppDialog(
      title: t.ui.orphans.title,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (showOrphans) ...[
            Text(t.ui.orphans.orphansIntro),
            const SizedBox(height: appInputSpacing),
            for (final entity in orphans)
              _AffectedRow(
                entity: entity,
                icon: CupertinoIcons.minus_circle,
                color: AppColors.error,
              ),
            const SizedBox(height: appSectionSpacing),
          ],
          if (showProxies) ...[
            Text(t.ui.orphans.proxiesIntro),
            const SizedBox(height: appInputSpacing),
            for (final entity in proxies)
              _AffectedRow(
                entity: entity,
                icon: CupertinoIcons.link,
                color: AppColors.warning,
              ),
            const SizedBox(height: appSectionSpacing),
          ],
          Text(t.ui.orphans.question),
        ],
      ),
      actions: [
        AppButton(
          variant: AppButtonVariant.tinted,
          onPressed: () => Navigator.of(context).pop(false),
          label: t.ui.orphans.keep,
        ),
        AppButton(
          variant: AppButtonVariant.filled,
          destructive: true,
          onPressed: () => Navigator.of(context).pop(true),
          label: t.ui.orphans.delete,
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
    return Padding(
      padding: const EdgeInsets.only(bottom: appInputSpacing / 2),
      child: IconLabel(
        icon: icon,
        color: color,
        expand: true,
        label: Text.rich(
          TextSpan(
            children: [
              TextSpan(text: entity.label),
              TextSpan(
                text: ' (${entity.type})',
                style: AppTextStyles.of(context).caption,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
