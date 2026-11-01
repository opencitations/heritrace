// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';

import 'spacing.dart';

const brandColor = Color(0xFF4582EC);

CupertinoThemeData buildAppTheme() => const CupertinoThemeData(
  brightness: Brightness.light,
  primaryColor: brandColor,
  scaffoldBackgroundColor: CupertinoColors.systemGroupedBackground,
);

abstract final class AppColors {
  static const primary = brandColor;
  static const error = CupertinoColors.systemRed;
  static const warning = CupertinoColors.systemOrange;
  static const secondaryText = CupertinoColors.secondaryLabel;
  static const separator = CupertinoColors.separator;
  static const fieldFill = CupertinoColors.tertiarySystemFill;
  static const surface = CupertinoColors.secondarySystemGroupedBackground;
  static const tooltip = CupertinoColors.darkBackgroundGray;
  static const onTooltip = CupertinoColors.white;
  static final primaryTint = brandColor.withValues(alpha: 0.12);
  static final errorTint = CupertinoColors.systemRed.color.withValues(
    alpha: 0.12,
  );
}

class AppTextStyles {
  AppTextStyles.of(BuildContext context)
    : body = CupertinoTheme.of(context).textTheme.textStyle,
      _compact = MediaQuery.sizeOf(context).width < appCompactWidth;

  final TextStyle body;
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

  TextStyle get secondary =>
      body.copyWith(fontSize: 15, color: AppColors.secondaryText);

  TextStyle get caption =>
      body.copyWith(fontSize: 13, color: AppColors.secondaryText);
}
