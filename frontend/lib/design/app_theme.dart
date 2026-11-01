// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import 'spacing.dart';

const brandColor = Color(0xFF4582EC);

CupertinoThemeData buildAppTheme(Brightness? brightness) => CupertinoThemeData(
  brightness: brightness,
  primaryColor: brandColor,
  scaffoldBackgroundColor: CupertinoColors.systemGroupedBackground,
);

/// The app's colors resolved for the current brightness and contrast, since
/// iOS system colors only adapt once resolved against a context.
class AppColors {
  AppColors.of(BuildContext context)
    : error = CupertinoColors.systemRed.resolveFrom(context),
      warning = CupertinoColors.systemOrange.resolveFrom(context),
      success = CupertinoColors.systemGreen.resolveFrom(context),
      label = CupertinoColors.label.resolveFrom(context),
      secondaryText = CupertinoColors.secondaryLabel.resolveFrom(context),
      disabled = CupertinoColors.systemGrey.resolveFrom(context),
      inactive = CupertinoColors.inactiveGray.resolveFrom(context),
      separator = CupertinoColors.separator.resolveFrom(context),
      fieldFill = CupertinoColors.tertiarySystemFill.resolveFrom(context),
      surface = CupertinoColors.secondarySystemGroupedBackground.resolveFrom(
        context,
      ),
      tooltip = CupertinoColors.label.resolveFrom(context),
      onTooltip = CupertinoColors.systemBackground.resolveFrom(context);

  static const primary = brandColor;
  static final primaryTint = brandColor.withValues(alpha: 0.12);

  final Color error;
  final Color warning;
  final Color success;
  final Color label;
  final Color secondaryText;
  final Color disabled;
  final Color inactive;
  final Color separator;
  final Color fieldFill;
  final Color surface;
  final Color tooltip;
  final Color onTooltip;

  Color get errorTint => error.withValues(alpha: 0.12);
}

class AppTextStyles {
  AppTextStyles.of(BuildContext context)
    : body = CupertinoTheme.of(context).textTheme.textStyle,
      _secondaryText = AppColors.of(context).secondaryText,
      _compact = MediaQuery.sizeOf(context).width < appCompactWidth;

  final TextStyle body;
  final Color _secondaryText;
  final bool _compact;

  TextStyle get display =>
      body.copyWith(fontSize: _compact ? 30 : 36, fontWeight: FontWeight.w700);

  TextStyle get pageTitle =>
      body.copyWith(fontSize: _compact ? 24 : 28, fontWeight: FontWeight.w700);

  TextStyle get sectionTitle =>
      body.copyWith(fontSize: 20, fontWeight: FontWeight.w600);

  TextStyle get heading =>
      body.copyWith(fontSize: 17, fontWeight: FontWeight.w600);

  TextStyle get subheading =>
      body.copyWith(fontSize: 15, fontWeight: FontWeight.w600);

  TextStyle get groupHeader => body.copyWith(
    fontSize: 15,
    fontWeight: FontWeight.w600,
    color: _secondaryText,
  );

  TextStyle get secondary => body.copyWith(fontSize: 15, color: _secondaryText);

  TextStyle get caption => body.copyWith(fontSize: 13, color: _secondaryText);
}
