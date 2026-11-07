// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

typedef Json = Map<String, dynamic>;

List<String> _strings(Object? list) =>
    (list as List<dynamic>).map((e) => e as String).toList();

class SystemSettings {
  SystemSettings({
    required this.appTitle,
    required this.appSubtitle,
    required this.countLimit,
    required this.catalogueDefaultPerPage,
    this.datasetGenerationTime,
    required this.primarySource,
    required this.orcidSafelist,
    required this.orphanHandling,
    required this.proxyHandling,
  });

  factory SystemSettings.fromJson(Json json) => SystemSettings(
    appTitle: json['appTitle'] as String,
    appSubtitle: json['appSubtitle'] as String,
    countLimit: json['countLimit'] as int,
    catalogueDefaultPerPage: json['catalogueDefaultPerPage'] as int,
    datasetGenerationTime: json['datasetGenerationTime'] as String?,
    primarySource: json['primarySource'] as String,
    orcidSafelist: _strings(json['orcidSafelist']),
    orphanHandling: json['orphanHandling'] as String,
    proxyHandling: json['proxyHandling'] as String,
  );

  String appTitle;
  String appSubtitle;
  int countLimit;
  int catalogueDefaultPerPage;
  String? datasetGenerationTime;
  String primarySource;
  List<String> orcidSafelist;
  String orphanHandling;
  String proxyHandling;

  Json toJson() => {
    'appTitle': appTitle,
    'appSubtitle': appSubtitle,
    'countLimit': countLimit,
    'catalogueDefaultPerPage': catalogueDefaultPerPage,
    'datasetGenerationTime': datasetGenerationTime,
    'primarySource': primarySource,
    'orcidSafelist': orcidSafelist,
    'orphanHandling': orphanHandling,
    'proxyHandling': proxyHandling,
  };
}

class SettingsOptions {
  const SettingsOptions({
    required this.strategies,
    required this.defaultCountLimit,
  });

  factory SettingsOptions.fromJson(Json json) => SettingsOptions(
    strategies: _strings(json['strategies']),
    defaultCountLimit: json['defaultCountLimit'] as int,
  );

  final List<String> strategies;
  final int defaultCountLimit;
}

class StoredSettings {
  const StoredSettings({required this.settings, required this.options});

  factory StoredSettings.fromJson(Json json) => StoredSettings(
    settings: SystemSettings.fromJson(json['settings'] as Json),
    options: SettingsOptions.fromJson(json['options'] as Json),
  );

  final SystemSettings settings;
  final SettingsOptions options;
}

sealed class SaveResult {
  const SaveResult();
}

class Saved extends SaveResult {
  const Saved({required this.revision, required this.reloading});

  final String revision;
  final bool reloading;
}

/// Another admin holds the lock on the settings.
class HeldBy extends SaveResult {
  const HeldBy(this.holder);

  final LockHolder holder;
}

class LockHolder {
  const LockHolder({required this.name, required this.orcid});

  factory LockHolder.fromJson(Json json) => LockHolder(
    name: json['user_name'] as String,
    orcid: json['user_id'] as String,
  );

  final String name;
  final String orcid;
}

class Rejected extends SaveResult {
  const Rejected(this.issues);

  /// Messages by location, such as `settings.orcidSafelist.1`.
  final Map<String, String> issues;
}
