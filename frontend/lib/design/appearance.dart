// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'appearance_storage.dart';

/// Light or dark, or whatever the system uses when [brightness] is null.
enum Appearance {
  system(null),
  light(Brightness.light),
  dark(Brightness.dark);

  const Appearance(this.brightness);

  final Brightness? brightness;
}

class AppearanceController extends Notifier<Appearance> {
  @override
  Appearance build() =>
      Appearance.values.asNameMap()[readAppearance()] ?? Appearance.system;

  void select(Appearance appearance) {
    writeAppearance(appearance.name);
    state = appearance;
  }
}

final appearanceProvider = NotifierProvider<AppearanceController, Appearance>(
  AppearanceController.new,
);
