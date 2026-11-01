// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../common/async_view.dart';
import '../common/dialogs.dart';
import '../common/primary_source_dialog.dart';
import '../common/reference_views.dart';
import '../design/app_theme.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../form/widgets/field_group_widget.dart';
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
      return Padding(
        padding: pageMargin(context),
        child: Center(child: Text(t.ui.merge.missingEntities)),
      );
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
    Router.neglect(context, () => context.go(entityPath(comparison.keep.uri)));
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context);
    final styles = AppTextStyles.of(context);
    final wide = MediaQuery.sizeOf(context).width > 900;
    final cards = [
      _MergeCard(
        entity: comparison.delete,
        title: t.ui.merge.deleteCard,
        icon: CupertinoIcons.trash_fill,
        color: AppColors.of(context).error,
      ),
      _MergeCard(
        entity: comparison.keep,
        title: t.ui.merge.keepCard,
        icon: CupertinoIcons.checkmark_circle_fill,
        color: AppColors.primary,
      ),
    ];
    Widget mergeInto(IconData icon) => Center(
      child: Column(
        children: [
          Icon(icon, size: 28, color: AppColors.of(context).secondaryText),
          Text(t.ui.merge.mergeInto, style: styles.caption),
        ],
      ),
    );
    return SingleChildScrollView(
      padding: pageMargin(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AppHeading(t.ui.merge.title, style: styles.pageTitle),
          const SizedBox(height: appSectionSpacing),
          if (wide) ...[
            mergeInto(CupertinoIcons.arrow_right),
            const SizedBox(height: appInputSpacing),
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(child: cards[0]),
                  const SizedBox(width: appSectionSpacing),
                  Expanded(child: cards[1]),
                ],
              ),
            ),
          ] else ...[
            cards[0],
            const SizedBox(height: appInputSpacing),
            mergeInto(CupertinoIcons.arrow_down),
            const SizedBox(height: appInputSpacing),
            cards[1],
          ],
          const SizedBox(height: appSectionSpacing),
          _Explanation(
            icon: CupertinoIcons.square_arrow_down,
            color: AppColors.primary,
            title: t.ui.merge.propertiesTitle,
            text: t.ui.merge.propertiesText,
          ),
          _Explanation(
            icon: CupertinoIcons.link,
            color: AppColors.primary,
            title: t.ui.merge.referencesTitle,
            text: t.ui.merge.referencesText,
          ),
          _Explanation(
            icon: CupertinoIcons.trash,
            color: AppColors.of(context).error,
            title: t.ui.merge.deletionTitle,
            text: t.ui.merge.deletionText,
          ),
          const SizedBox(height: appSectionSpacing),
          Wrap(
            alignment: WrapAlignment.spaceBetween,
            spacing: appInputSpacing,
            runSpacing: appInputSpacing,
            children: [
              AppButton(
                variant: AppButtonVariant.tinted,
                onPressed: () => context.go(entityPath(comparison.keep.uri)),
                icon: CupertinoIcons.xmark,
                label: t.ui.actions.cancel,
              ),
              AppButton(
                variant: AppButtonVariant.filled,
                destructive: true,
                onPressed: () => _confirm(context, ref),
                icon: CupertinoIcons.check_mark,
                label: t.ui.merge.confirm,
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
    final styles = AppTextStyles.of(context);
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          IconLabel(
            icon: icon,
            label: Text(title),
            color: color,
            style: styles.heading.copyWith(color: color),
          ),
          const SizedBox(height: appInputSpacing / 2),
          Text(entity.label),
          const SizedBox(height: appInputSpacing / 2),
          _TypeBadge(label: entity.typeLabel),
          if (entity.properties.isEmpty) ...[
            const SizedBox(height: appInputSpacing),
            Text(
              t.ui.merge.noProperties,
              style: const TextStyle(fontStyle: FontStyle.italic),
            ),
          ],
          for (final property in entity.properties) ...[
            Container(
              height: 0.5,
              margin: const EdgeInsets.symmetric(vertical: appInputSpacing),
              color: AppColors.of(context).separator,
            ),
            AppTooltip(
              message: property.predicate,
              child: PropertyHeading(
                label: property.label,
                style: styles.subheading,
              ),
            ),
            const SizedBox(height: appInputSpacing / 2),
            for (final (index, value) in property.values.indexed)
              Padding(
                padding: listItemSpacing(index),
                child: Text(value.readableLabel),
              ),
          ],
          const SizedBox(height: appInputSpacing),
          Align(
            alignment: Alignment.centerRight,
            child: AppButton(
              variant: AppButtonVariant.tinted,
              onPressed: () => openExternal(entityPath(entity.uri)),
              icon: CupertinoIcons.arrow_up_right_square,
              label: t.ui.merge.viewDetails,
            ),
          ),
        ],
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
      child: IconLabel(
        icon: icon,
        color: color,
        expand: true,
        label: Text.rich(
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
    );
  }
}

class _TypeBadge extends StatelessWidget {
  const _TypeBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: appInputSpacing,
        vertical: 4,
      ),
      decoration: BoxDecoration(
        color: AppColors.of(context).fieldFill,
        borderRadius: BorderRadius.circular(appRadius * 2),
      ),
      child: Text(label, style: AppTextStyles.of(context).caption),
    );
  }
}
