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
    required this.shacl,
    required this.datatypeOptions,
  });

  factory AppConfig.fromJson(Map<String, dynamic> json) => AppConfig(
    appTitle: json['app_title'] as String,
    appSubtitle: json['app_subtitle'] as String,
    shacl: json['shacl'] as bool,
    datatypeOptions: (json['datatype_options'] as List<dynamic>)
        .map((e) => DatatypeOption.fromJson(e as Map<String, dynamic>))
        .toList(),
  );

  final String appTitle;
  final String appSubtitle;
  final bool shacl;
  final List<DatatypeOption> datatypeOptions;
}

class Session {
  const Session({
    required this.userName,
    required this.defaultPrimarySource,
    required this.config,
    this.isAdmin = false,
    this.setupError,
    this.configurationRevision,
  });

  factory Session.fromJson(Map<String, dynamic> json) => Session(
    userName: (json['user'] as Map<String, dynamic>?)?['name'] as String?,
    defaultPrimarySource: json['default_primary_source'] as String?,
    config: json['config'] == null
        ? null
        : AppConfig.fromJson(json['config'] as Map<String, dynamic>),
    isAdmin: json['is_admin'] as bool,
    setupError: json['setup_error'] as String?,
    configurationRevision: json['configuration_revision'] as String?,
  );

  /// The signed-in user's name, null when nobody is signed in.
  final String? userName;
  final String? defaultPrimarySource;

  /// Null while HERITRACE waits for an administrator to configure it.
  final AppConfig? config;
  final bool isAdmin;

  /// Why the configuration cannot be used, shown to administrators only.
  final String? setupError;
  final String? configurationRevision;

  bool get isSignedIn => userName != null;

  bool get setupRequired => config == null;

  Session _copy({String? userName, String? defaultPrimarySource}) => Session(
    userName: userName,
    defaultPrimarySource: defaultPrimarySource,
    config: config,
    isAdmin: isAdmin,
    setupError: setupError,
    configurationRevision: configurationRevision,
  );

  Session signedOut() => _copy();

  Session withDefaultPrimarySource(String? source) =>
      _copy(userName: userName, defaultPrimarySource: source);
}
