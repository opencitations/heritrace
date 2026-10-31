// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/i18n/translations.g.dart';
import 'package:heritrace/session/session_controller.dart';
import 'package:heritrace/session/session_models.dart';

const testConfig = AppConfig(
  appTitle: 'HERITRACE Test',
  appSubtitle: 'Test subtitle',
  allowedPerPage: [50, 100],
  shacl: true,
  datatypeOptions: [
    DatatypeOption(
      label: 'Text (string)',
      uri: 'http://www.w3.org/2001/XMLSchema#string',
    ),
  ],
);

const signedInSession = Session(
  isSignedIn: true,
  defaultPrimarySource: null,
  config: testConfig,
);

const anonymousSession = Session(
  isSignedIn: false,
  defaultPrimarySource: null,
  config: testConfig,
);

class FakeSessionController extends SessionController {
  FakeSessionController(this.session);

  final Session session;

  @override
  Future<Session> build() async => session;
}

Future<void> pumpApp(
  WidgetTester tester, {
  required Widget child,
  Session session = signedInSession,
  List<Override> overrides = const [],
}) async {
  LocaleSettings.setLocale(AppLocale.en);
  tester.view.physicalSize = const Size(1280, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    TranslationProvider(
      child: ProviderScope(
        overrides: [
          sessionProvider.overrideWith(() => FakeSessionController(session)),
          ...overrides,
        ],
        child: child,
      ),
    ),
  );
  await tester.pump();
}
