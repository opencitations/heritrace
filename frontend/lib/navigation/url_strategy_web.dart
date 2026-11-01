// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_web_plugins/url_strategy.dart';

import 'app_paths.dart';

/// Writes entity locations to the browser history encoded, as the router
/// reports them. A decoded entry would come back on Back as a location
/// different from the router's, which the router then pushes as a new entry.
class _EntityUrlStrategy extends PathUrlStrategy {
  @override
  String prepareExternalUrl(String internalUrl) => super.prepareExternalUrl(
    encodeEntityLocation(internalUrl.substring(1).split('/')) ?? internalUrl,
  );
}

void useAppUrlStrategy() => setUrlStrategy(_EntityUrlStrategy());
