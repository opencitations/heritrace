// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../i18n/translations.g.dart';
import 'field_group_widget.dart';

/// A true-or-false property. While editing it is a settings row with the
/// switch beside the name; otherwise "Yes" or "No" under the name.
class BooleanFieldCard extends StatelessWidget {
  const BooleanFieldCard({
    required this.label,
    required this.value,
    this.onChanged,
    super.key,
  });

  final String label;
  final bool value;
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    if (onChanged != null) {
      return AppSection(
        children: [
          AppListTile(
            title: TileText(label),
            trailing: CupertinoSwitch(value: value, onChanged: onChanged),
          ),
        ],
      );
    }
    return AppCard(
      header: PropertyHeading(
        label: label,
        style: AppTextStyles.of(context).groupHeader,
      ),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          minHeight: kCupertinoButtonMinSize[CupertinoButtonSize.medium]!,
        ),
        child: Align(
          alignment: Alignment.centerLeft,
          child: Text(value ? t.ui.form.booleanTrue : t.ui.form.booleanFalse),
        ),
      ),
    );
  }
}
