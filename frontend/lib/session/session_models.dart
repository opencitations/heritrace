// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

class DatatypeOption {
  const DatatypeOption({required this.label, required this.uri});

  factory DatatypeOption.fromJson(Map<String, dynamic> json) => DatatypeOption(
    label: json['label'] as String,
    uri: json['uri'] as String,
  );

  final String label;
  final String uri;
}

class AppConfig {
  const AppConfig({
    required this.appTitle,
    required this.appSubtitle,
    required this.allowedPerPage,
    required this.shacl,
    required this.datatypeOptions,
  });

  factory AppConfig.fromJson(Map<String, dynamic> json) => AppConfig(
    appTitle: json['app_title'] as String,
    appSubtitle: json['app_subtitle'] as String,
    allowedPerPage: (json['allowed_per_page'] as List<dynamic>).cast<int>(),
    shacl: json['shacl'] as bool,
    datatypeOptions: (json['datatype_options'] as List<dynamic>)
        .map((e) => DatatypeOption.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final String appTitle;
  final String appSubtitle;
  final List<int> allowedPerPage;
  final bool shacl;
  final List<DatatypeOption> datatypeOptions;
}

class Session {
  const Session({
    required this.isSignedIn,
    required this.defaultPrimarySource,
    required this.config,
  });

  factory Session.fromJson(Map<String, dynamic> json) => Session(
    isSignedIn: json['user'] != null,
    defaultPrimarySource: json['default_primary_source'] as String?,
    config: AppConfig.fromJson(json['config'] as Map<String, dynamic>),
  );

  final bool isSignedIn;
  final String? defaultPrimarySource;
  final AppConfig config;

  Session signedOut() =>
      Session(isSignedIn: false, defaultPrimarySource: null, config: config);

  Session withDefaultPrimarySource(String? source) => Session(
    isSignedIn: isSignedIn,
    defaultPrimarySource: source,
    config: config,
  );
}
