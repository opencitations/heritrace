// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'entity_store.dart';

const landingPath = '/';
const cataloguePath = '/catalogue';
const recycleBinPath = '/recycle-bin';
const createEntityPath = '/create-entity';
const mergePath = '/merge/compare-and-merge';
const settingsPath = '/settings';
const loginPath = '/auth/login';

String entityPath(String uri) => EntityStore.dataset.entityPath(uri);

String entityHistoryPath(String uri) => EntityStore.dataset.historyPath(uri);

String entityVersionPath(String uri, String timestamp) =>
    EntityStore.dataset.versionPath(uri, timestamp);

String mergeComparePath(String subject, String otherSubject) => Uri(
  path: mergePath,
  queryParameters: {'subject': subject, 'other_subject': otherSubject},
).toString();

/// The location with the entity URI encoded as a single path segment, or null
/// when [segments] hold no entity URI split over several segments. The web
/// engine decodes every location it writes to the browser history, so links
/// and history entries carry the entity URI split at its slashes.
String? encodeEntityLocation(List<String> segments) => switch (segments) {
  ['settings', 'shapes', ...final rest] => _encodeStoreLocation(
    EntityStore.configuration,
    rest,
  ),
  _ => _encodeStoreLocation(EntityStore.dataset, segments),
};

String? _encodeStoreLocation(EntityStore store, List<String> segments) =>
    switch (segments) {
      ['about', _, _, ...] => store.entityPath(segments.skip(1).join('/')),
      ['entity-history', _, _, ...] => store.historyPath(
        segments.skip(1).join('/'),
      ),
      ['entity-version', _, _, _, ...] => store.versionPath(
        segments.sublist(1, segments.length - 1).join('/'),
        segments.last,
      ),
      _ => null,
    };
