// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:intl/intl.dart';

import '../common/reference_views.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import 'iri_text.dart';
import 'orcid_list_field.dart';
import 'settings_draft.dart';
import 'settings_fields.dart';

const _linkingResourcesDocs =
    'https://opencitations.github.io/heritrace/configuration/extra/'
    '#relationship-properties-proxy-pattern';

class SystemSettingsForm extends StatelessWidget {
  const SystemSettingsForm({required this.draft, super.key});

  final SettingsDraft draft;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context).ui.settings.system;
    final settings = draft.settings;
    String? issue(String key) => draft.issue('settings.$key');
    ValueChanged<T>? edit<T>(ValueChanged<T> apply) =>
        draft.editing ? (value) => draft.update(() => apply(value)) : null;
    ValueChanged<bool> readable(String field) =>
        (readable) => draft.setReadable(field, readable: readable);
    final countLimit = NumberFormat.decimalPattern().format(
      settings.countLimit,
    );
    final strategies = [
      for (final strategy in draft.options.strategies)
        AppMenuOption(strategy, switch (strategy) {
          'ASK' => t.strategyAsk,
          'DELETE' => t.strategyDelete,
          'KEEP' => t.strategyKeep,
          _ => throw StateError('Unknown strategy $strategy'),
        }),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      spacing: appSectionSpacing,
      children: [
        SettingsGroup(
          title: t.homePage,
          children: [
            SettingsTextField(
              label: t.appTitle,
              value: settings.appTitle,
              errorText: issue('appTitle'),
              onChanged: edit((value) => settings.appTitle = value),
            ),
            SettingsTextField(
              label: t.appSubtitle,
              value: settings.appSubtitle,
              errorText: issue('appSubtitle'),
              onChanged: edit((value) => settings.appSubtitle = value),
            ),
          ],
        ),
        SettingsGroup(
          title: t.provenance,
          children: [
            SettingsTextField(
              label: t.primarySource,
              value: settings.primarySource,
              hint: t.primarySourceHint,
              errorText: issue('primarySource'),
              keyboardType: TextInputType.url,
              validator: (text) => isIri(text) ? null : t.iriInvalid,
              onChanged: edit((value) => settings.primarySource = value.trim()),
            ),
            SettingsDateTimeField(
              label: t.generationTime,
              value: settings.datasetGenerationTime,
              hint: t.generationTimeHint,
              errorText: issue('datasetGenerationTime'),
              onReadable: readable('datasetGenerationTime'),
              onChanged: edit(
                (value) => settings.datasetGenerationTime = value,
              ),
            ),
          ],
        ),
        SettingsGroup(
          title: t.lists,
          children: [
            SettingsNumberField(
              label: t.perPage,
              value: settings.catalogueDefaultPerPage,
              errorText: issue('catalogueDefaultPerPage'),
              onReadable: readable('catalogueDefaultPerPage'),
              onChanged: edit(
                (value) => settings.catalogueDefaultPerPage = value,
              ),
            ),
            SettingsNumberField(
              label: t.countLimit,
              value: settings.countLimit,
              hint: settings.countLimit == draft.options.defaultCountLimit
                  ? t.countLimitHintDefault(count: countLimit)
                  : t.countLimitHint(count: countLimit),
              errorText: issue('countLimit'),
              onReadable: readable('countLimit'),
              onChanged: edit((value) => settings.countLimit = value),
            ),
          ],
        ),
        SettingsGroup(
          title: t.deletion,
          children: [
            SettingsMenu<String>(
              label: t.orphans,
              value: settings.orphanHandling,
              options: strategies,
              errorText: issue('orphanHandling'),
              hint: t.orphansHint,
              onChanged: edit((value) => settings.orphanHandling = value),
            ),
            SettingsMenu<String>(
              label: t.proxies,
              value: settings.proxyHandling,
              options: strategies,
              errorText: issue('proxyHandling'),
              hint: t.proxiesHint,
              link: LinkText(
                label: t.proxiesHowTo,
                onTap: () => openExternal(_linkingResourcesDocs),
              ),
              onChanged: edit((value) => settings.proxyHandling = value),
            ),
          ],
        ),
        SettingsGroup(
          title: t.access,
          children: [
            OrcidListField(
              draft: draft,
              label: t.safelist,
              orcids: settings.orcidSafelist,
              location: 'settings.orcidSafelist',
            ),
          ],
        ),
      ],
    );
  }
}
