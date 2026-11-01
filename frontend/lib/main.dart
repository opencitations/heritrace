// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/semantics.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';
import 'i18n/language.dart';
import 'i18n/translations.g.dart';
import 'navigation/url_strategy.dart';

void main() {
  useAppUrlStrategy();
  WidgetsFlutterBinding.ensureInitialized();
  // Flutter web builds its accessibility tree only after a screen reader user
  // finds and presses a hidden button; building it from the start lets
  // VoiceOver read the app right away.
  SemanticsBinding.instance.ensureSemantics();
  applyLanguage(readLanguage());
  runApp(TranslationProvider(child: const ProviderScope(child: App())));
}
