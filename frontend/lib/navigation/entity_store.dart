// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The IRI of the entity that holds the whole SHACL configuration.
const configurationRoot = 'https://w3id.org/heritrace/configuration';

/// Where entities live: the dataset, or the SHACL configuration that admins
/// edit as one entity with the same pages.
enum EntityStore {
  dataset(apiPrefix: '/api', pathPrefix: ''),
  configuration(
    apiPrefix: '/api/configuration',
    pathPrefix: '/settings/shapes',
  );

  const EntityStore({required this.apiPrefix, required this.pathPrefix});

  final String apiPrefix;
  final String pathPrefix;

  String entityPath(String uri) =>
      '$pathPrefix/about/${Uri.encodeComponent(uri)}';

  String historyPath(String uri) =>
      '$pathPrefix/entity-history/${Uri.encodeComponent(uri)}';

  String versionPath(String uri, String timestamp) =>
      '$pathPrefix/entity-version/${Uri.encodeComponent(uri)}/${Uri.encodeComponent(timestamp)}';
}

final entityStoreProvider = Provider<EntityStore>(
  (ref) => EntityStore.dataset,
  dependencies: const [],
);

extension EntityStoreContext on BuildContext {
  EntityStore get entityStore =>
      ProviderScope.containerOf(this, listen: false).read(entityStoreProvider);
}
