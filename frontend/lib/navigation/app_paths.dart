// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

const landingPath = '/';
const cataloguePath = '/catalogue';
const timeVaultPath = '/time-vault';
const createEntityPath = '/create-entity';
const mergePath = '/merge/compare-and-merge';
const loginPath = '/auth/login';

String entityPath(String uri) => '/about/${Uri.encodeComponent(uri)}';

String entityHistoryPath(String uri) =>
    '/entity-history/${Uri.encodeComponent(uri)}';

String entityVersionPath(String uri, String timestamp) =>
    '/entity-version/${Uri.encodeComponent(uri)}/${Uri.encodeComponent(timestamp)}';

String mergeComparePath(String subject, String otherSubject) => Uri(
  path: mergePath,
  queryParameters: {'subject': subject, 'other_subject': otherSubject},
).toString();
