// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../../i18n/translations.g.dart';
import '../field_def.dart';

/// Splits [fields], which arrive sorted by section, into runs of consecutive
/// fields of the same section.
List<({FieldSection? section, List<T> fields})> sectionRuns<T>(
  Iterable<T> fields,
  FieldSection? Function(T field) sectionOf,
) {
  final runs = <({FieldSection? section, List<T> fields})>[];
  for (final field in fields) {
    final section = sectionOf(field);
    if (runs.isEmpty || runs.last.section?.iri != section?.iri) {
      runs.add((section: section, fields: [field]));
    } else {
      runs.last.fields.add(field);
    }
  }
  return runs;
}

/// The fields of one `sh:group` under its name. While editing, the name opens
/// and closes the section, which opens on its own when one of its fields
/// shows an error. A closed section counts its fields under the name.
class FieldSectionView extends StatefulWidget {
  const FieldSectionView({
    required this.name,
    required this.children,
    this.collapsible = false,
    this.initiallyOpen = true,
    this.hasErrors = false,
    super.key,
  });

  final String name;
  final List<Widget> children;
  final bool collapsible;
  final bool initiallyOpen;
  final bool hasErrors;

  @override
  State<FieldSectionView> createState() => _FieldSectionViewState();
}

class _FieldSectionViewState extends State<FieldSectionView> {
  late bool _open = widget.initiallyOpen;

  @override
  void didUpdateWidget(FieldSectionView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.collapsible && !oldWidget.collapsible) {
      _open = widget.initiallyOpen;
    }
    if (widget.hasErrors && !oldWidget.hasErrors) {
      _open = true;
    }
  }

  @override
  Widget build(BuildContext context) {
    final open = !widget.collapsible || _open;
    final styles = AppTextStyles.of(context);
    final title = AppHeading(widget.name, style: styles.heading);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // The touch area of the button already leaves room around the name.
        if (widget.collapsible)
          Semantics(
            expanded: open,
            child: CupertinoButton(
              padding: EdgeInsets.zero,
              minimumSize: minTapTarget,
              onPressed: () => setState(() => _open = !_open),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        title,
                        if (!open)
                          Text(
                            Translations.of(context).ui.form
                                .fieldCount(n: widget.children.length),
                            style: styles.caption,
                          ),
                      ],
                    ),
                  ),
                  Icon(
                    open
                        ? CupertinoIcons.chevron_up
                        : CupertinoIcons.chevron_down,
                    size: 18,
                    color: AppColors.of(context).secondaryText,
                  ),
                ],
              ),
            ),
          )
        else
          Padding(
            padding: const EdgeInsets.symmetric(vertical: appInputSpacing),
            child: title,
          ),
        if (open)
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            spacing: appSectionSpacing,
            children: widget.children,
          ),
      ],
    );
  }
}
