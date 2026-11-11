// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:heritrace/app.dart';
import 'package:heritrace/design/controls.dart';
import 'package:heritrace/entity/entity_page.dart';
import 'package:heritrace/entity/entity_repository.dart';
import 'package:heritrace/navigation/app_paths.dart';
import 'package:heritrace/navigation/app_router.dart';
import 'package:heritrace/navigation/entity_store.dart';
import 'package:heritrace/session/session_models.dart';
import 'package:heritrace/settings/orcid.dart';
import 'package:heritrace/settings/settings_models.dart';
import 'package:heritrace/settings/settings_fields.dart';
import 'package:heritrace/settings/settings_repository.dart';

import '../helpers.dart';
import 'fixtures.dart';

class _FakeSettingsRepository extends SettingsRepository {
  _FakeSettingsRepository(this.result, {this.holder}) : super(Dio());

  final SaveResult result;
  final LockHolder? holder;
  Json? saved;
  int unlocks = 0;

  @override
  Future<LockHolder?> lock() async => holder;

  @override
  Future<void> unlock() async => unlocks++;

  @override
  Future<StoredSettings> load() async => StoredSettings.fromJson(storedJson());

  @override
  Future<SaveResult> save(SystemSettings settings) async {
    saved = settings.toJson();
    return result;
  }

  @override
  Future<OrcidLookup> lookUpOrcid(String orcidId) async => switch (orcidId) {
    '0000-0002-1825-0097' => const OrcidFound('Josiah Carberry'),
    _ => const OrcidMissing(),
  };
}

const _admin = Session(
  userName: 'Admin',
  defaultPrimarySource: null,
  config: testConfig,
  isAdmin: true,
);

Future<GoRouter> _openSettings(
  WidgetTester tester,
  _FakeSettingsRepository repository, {
  Session session = _admin,
}) async {
  await pumpApp(
    tester,
    child: const App(),
    session: session,
    overrides: [
      settingsRepositoryProvider.overrideWithValue(repository),
      entityViewProvider.overrideWith((ref, uri) => Completer<Never>().future),
    ],
  );
  final router = ProviderScope.containerOf(tester.element(find.byType(App)))
      .read(routerProvider);
  router.go(settingsPath);
  await tester.pumpAndSettle();
  if (!session.setupRequired) {
    await tester.tap(find.text('Edit'));
    await tester.pumpAndSettle();
  }
  return router;
}

Finder _field(String label) {
  return find.descendant(
    of: find
        .ancestor(of: find.text(label), matching: find.byType(Column))
        .first,
    matching: find.byType(CupertinoTextField),
  );
}

Future<void> _save(WidgetTester tester) async {
  await tester.pumpAndSettle();
  await tester.tap(find.text('Save'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('saving sends the edited settings to the server', (tester) async {
    final repository = _FakeSettingsRepository(
      const Saved(revision: 'r1', reloading: false),
    );
    await _openSettings(tester, repository);

    await tester.enterText(_field('Large title'), 'Paratext 2');
    await _save(tester);

    expect(repository.saved!['appTitle'], 'Paratext 2');
    expect(
      find.text('The configuration is saved. Restart HERITRACE to apply it.'),
      findsOneWidget,
    );
  });

  test('a picked moment keeps the time zone of the browser', () {
    final moment = DateTime(2024, 12, 25, 10, 30);
    final text = withTimeZone(moment);

    expect(text, startsWith('2024-12-25T10:30:00'));
    expect(DateTime.parse(text).isAtSameMomentAs(moment), isTrue);
  });

  testWidgets('the generation time is picked on the wheels or cleared', (
    tester,
  ) async {
    final repository = _FakeSettingsRepository(
      const Saved(revision: 'r1', reloading: false),
    );
    await _openSettings(tester, repository);

    final pick = find.byIcon(CupertinoIcons.calendar);
    await tester.ensureVisible(pick);
    await tester.pumpAndSettle();
    await tester.tap(pick);
    await tester.pumpAndSettle();
    expect(find.byType(CupertinoDatePicker), findsNWidgets(2));
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();
    await _save(tester);

    final picked = withTimeZone(
      DateTime.parse(settingsJson()['datasetGenerationTime'] as String)
          .toLocal(),
    );
    expect(repository.saved!['datasetGenerationTime'], picked);
    expect(find.text(picked), findsOneWidget);

    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    await tester.dragUntilVisible(
      find.text('Edit'),
      find.byType(CustomScrollView),
      const Offset(0, 300),
    );
    await tester.tap(find.text('Edit'));
    await tester.pumpAndSettle();
    await tester.enterText(_field('Dataset generation time'), '');
    await _save(tester);

    expect(repository.saved!['datasetGenerationTime'], isNull);
  });

  testWidgets('a mouse drags the wheels', (tester) async {
    final repository = _FakeSettingsRepository(
      const Saved(revision: 'r1', reloading: false),
    );
    await _openSettings(tester, repository);

    final pick = find.byIcon(CupertinoIcons.calendar);
    await tester.ensureVisible(pick);
    await tester.pumpAndSettle();
    await tester.tap(pick);
    await tester.pumpAndSettle();
    await tester.drag(
      find.text('2024'),
      const Offset(0, -120),
      kind: PointerDeviceKind.mouse,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Done'));
    await tester.pumpAndSettle();
    await _save(tester);

    final saved = repository.saved!['datasetGenerationTime'] as String;
    expect(DateTime.parse(saved).year, greaterThan(2024));
  });

  testWidgets('the count limit hint shows the count the catalogue will show', (
    tester,
  ) async {
    await _openSettings(
      tester,
      _FakeSettingsRepository(const Saved(revision: 'r1', reloading: false)),
    );

    expect(find.textContaining('for example, "10,000+"'), findsOneWidget);

    await tester.enterText(_field('Maximum count per category'), '500');
    await tester.pump();

    expect(find.textContaining('shows "500+"'), findsOneWidget);
    expect(find.textContaining('for example'), findsNothing);
  });

  testWidgets('each ORCID iD is checked and shown with its account name', (
    tester,
  ) async {
    final repository = _FakeSettingsRepository(
      const Saved(revision: 'r1', reloading: false),
    );
    await _openSettings(tester, repository);
    final rows = find.byWidgetPredicate(
      (widget) =>
          widget is CupertinoTextField &&
          widget.placeholder == '0000-0002-1825-0097',
    );
    const invalid =
        'This is not a valid ORCID iD. It looks like 0000-0002-1825-0097';

    expect(find.text('Josiah Carberry'), findsOneWidget);

    await tester.ensureVisible(find.text('Add ORCID iD'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Add ORCID iD'));
    await tester.pumpAndSettle();
    await tester.enterText(rows.at(1), '0000-0002-1825-0098');
    await tester.pump();
    expect(find.text(invalid), findsNothing);

    FocusManager.instance.primaryFocus!.unfocus();
    await tester.pump();
    expect(find.text(invalid), findsOneWidget);

    await tester.tap(rows.at(1));
    await tester.pump();
    await tester.enterText(rows.at(1), 'https://orcid.org/0000-0002-9079-593X');
    await tester.pumpAndSettle();
    expect(find.text(invalid), findsNothing);
    expect(find.text('No ORCID account has this iD'), findsOneWidget);

    await tester.ensureVisible(find.bySemanticsLabel('Remove ORCID iD').first);
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsLabel('Remove ORCID iD').first);
    await tester.pumpAndSettle();
    await _save(tester);

    expect(repository.saved!['orcidSafelist'], [
      'https://orcid.org/0000-0002-9079-593X',
    ]);
    expect(find.text('Josiah Carberry'), findsNothing);
  });

  testWidgets('the primary source must be an IRI', (tester) async {
    await _openSettings(
      tester,
      _FakeSettingsRepository(const Saved(revision: 'r1', reloading: false)),
    );
    final field = _field('Default primary source');
    const invalid = 'Enter a full IRI, such as https://example.org/source';

    await tester.enterText(field, 'example.org source');
    await tester.pump();
    expect(find.text(invalid), findsNothing);

    FocusManager.instance.primaryFocus!.unfocus();
    await tester.pump();
    expect(find.text(invalid), findsOneWidget);

    await tester.tap(field);
    await tester.pump();
    await tester.enterText(field, 'https://example.org/archive');
    FocusManager.instance.primaryFocus!.unfocus();
    await tester.pump();
    expect(find.text(invalid), findsNothing);
  });

  testWidgets('server issues appear under their fields', (tester) async {
    final repository = _FakeSettingsRepository(
      const Rejected({'settings.appTitle': 'The title cannot be empty'}),
    );
    await _openSettings(tester, repository);

    await tester.enterText(_field('Large title'), ' ');
    await _save(tester);
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    expect(find.text('The title cannot be empty'), findsOneWidget);
  });

  testWidgets('save waits for a real change', (tester) async {
    await _openSettings(
      tester,
      _FakeSettingsRepository(const Saved(revision: 'r1', reloading: false)),
    );
    VoidCallback? save() => tester
        .widget<AppButton>(find.widgetWithText(AppButton, 'Save'))
        .onPressed;
    final title = settingsJson()['appTitle'] as String;

    await tester.enterText(_field('Large title'), '${title}x');
    await tester.pump();
    expect(save(), isNotNull);

    await tester.enterText(_field('Large title'), title);
    await tester.pump();
    expect(save(), isNull);
  });

  testWidgets('cancel restores the saved settings and ends editing', (
    tester,
  ) async {
    final repository = _FakeSettingsRepository(
      const Saved(revision: 'r1', reloading: false),
    );
    await _openSettings(tester, repository);

    await tester.enterText(_field('Large title'), 'Paratext 2');
    await tester.pump();
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Yes, discard changes'));
    await tester.pumpAndSettle();

    expect(find.byType(CupertinoTextField), findsNothing);
    expect(find.text(settingsJson()['appTitle'] as String), findsOneWidget);
    expect(find.text('Edit'), findsOneWidget);
    expect(repository.unlocks, 1);
  });

  testWidgets('another admin editing the settings keeps them read-only', (
    tester,
  ) async {
    await _openSettings(
      tester,
      _FakeSettingsRepository(
        const Saved(revision: 'r1', reloading: false),
        holder: const LockHolder(
          name: 'Other Admin',
          orcid: '0000-0000-0000-0001',
        ),
      ),
    );

    expect(find.text('Settings being edited'), findsOneWidget);
    expect(
      find.text(
        'Other Admin (0000-0000-0000-0001) is editing the system settings.'
        ' Try again when they are done.',
      ),
      findsOneWidget,
    );
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();

    expect(find.byType(CupertinoTextField), findsNothing);
    expect(find.text('Edit'), findsOneWidget);
  });

  testWidgets('a save after another admin took the lock is refused', (
    tester,
  ) async {
    await _openSettings(
      tester,
      _FakeSettingsRepository(
        const HeldBy(
          LockHolder(name: 'Other Admin', orcid: '0000-0000-0000-0001'),
        ),
      ),
    );

    await tester.enterText(_field('Large title'), 'Paratext 2');
    await _save(tester);

    expect(find.text('Settings being edited'), findsOneWidget);
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    expect(find.byType(CupertinoTextField), findsNothing);
    expect(find.text(settingsJson()['appTitle'] as String), findsOneWidget);
  });

  testWidgets('text that cannot become a value blocks saving', (tester) async {
    await _openSettings(
      tester,
      _FakeSettingsRepository(const Saved(revision: 'r1', reloading: false)),
    );
    VoidCallback? save() => tester
        .widget<AppButton>(find.widgetWithText(AppButton, 'Save'))
        .onPressed;

    await tester.enterText(_field('Large title'), 'Paratext 2');
    await tester.enterText(_field('Resources per page'), '12a');
    await tester.pump();
    expect(find.text('Enter a whole number'), findsOneWidget);
    expect(save(), isNull);

    await tester.enterText(_field('Resources per page'), '12');
    await tester.enterText(_field('Dataset generation time'), 'tomorrow');
    await tester.pump();
    expect(
      find.text('Enter a date and time, such as 2024-12-25T10:00:00+01:00'),
      findsOneWidget,
    );
    expect(save(), isNull);

    await tester.enterText(_field('Dataset generation time'), '');
    await tester.pump();
    expect(save(), isNotNull);
  });

  testWidgets('the entity types tab opens the configuration root', (
    tester,
  ) async {
    final router = await _openSettings(
      tester,
      _FakeSettingsRepository(const Saved(revision: 'r1', reloading: false)),
    );

    await tester.tap(find.text('Resource types'));
    await tester.pump();

    expect(
      router.state.uri.path,
      EntityStore.configuration.entityPath(configurationRoot),
    );
    expect(find.byType(EntityPage), findsOneWidget);
  });

  testWidgets('setup mode keeps admins on the configuration page', (
    tester,
  ) async {
    final repository = _FakeSettingsRepository(
      const Saved(revision: 'r1', reloading: false),
    );
    final router = await _openSettings(
      tester,
      repository,
      session: const Session(
        userName: 'Admin',
        defaultPrimarySource: null,
        config: null,
        isAdmin: true,
        setupError: 'The configuration has no system settings',
      ),
    );

    router.go(cataloguePath);
    await tester.pumpAndSettle();

    expect(router.state.uri.path, settingsPath);
    expect(
      find.text(
        'The current configuration cannot be used: '
        'The configuration has no system settings',
      ),
      findsOneWidget,
    );
  });

  testWidgets('setup mode shows other users a waiting message', (tester) async {
    final repository = _FakeSettingsRepository(
      const Saved(revision: 'r1', reloading: false),
    );
    final router = await _openSettings(
      tester,
      repository,
      session: const Session(
        userName: 'Editor',
        defaultPrimarySource: null,
        config: null,
      ),
    );

    expect(router.state.uri.path, landingPath);
    expect(
      find.text('HERITRACE is being configured. Try again later.'),
      findsOneWidget,
    );
  });
}
