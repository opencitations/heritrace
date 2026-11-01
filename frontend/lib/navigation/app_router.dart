// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../catalogue/catalogue_page.dart';
import '../entity/create_entity_page.dart';
import '../entity/entity_page.dart';
import '../history/history_page.dart';
import '../history/version_page.dart';
import '../landing/landing_page.dart';
import '../merge/merge_page.dart';
import '../session/session_controller.dart';
import 'app_paths.dart';
import 'app_scaffold.dart';
import 'external_navigation.dart';
import 'leave_guard.dart';
import 'not_found_page.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final sessionListenable = _SessionListenable(ref);
  ref.onDispose(sessionListenable.dispose);
  return GoRouter(
    refreshListenable: sessionListenable,
    redirect: (context, state) {
      final encodedLocation = encodeEntityLocation(state.uri.pathSegments);
      if (encodedLocation != null) {
        return encodedLocation;
      }
      final session = ref.read(sessionProvider).value;
      if (session == null || session.isSignedIn) {
        return null;
      }
      if (state.uri.path == landingPath) {
        return null;
      }
      navigateExternally(backendUrl(loginPath));
      return landingPath;
    },
    errorBuilder: (context, state) => const NotFoundPage(),
    routes: [
      ShellRoute(
        builder: (context, state, child) => AppScaffold(child: child),
        routes: [
          GoRoute(
            path: landingPath,
            builder: (context, state) => LandingPage(
              loginError: state.uri.queryParameters['login_error'],
            ),
          ),
          GoRoute(
            path: cataloguePath,
            builder: (context, state) => CataloguePage(
              recycleBin: false,
              query: state.uri.queryParameters,
            ),
          ),
          GoRoute(
            path: recycleBinPath,
            builder: (context, state) => CataloguePage(
              recycleBin: true,
              query: state.uri.queryParameters,
            ),
          ),
          GoRoute(
            path: createEntityPath,
            builder: (context, state) => const CreateEntityPage(),
            onExit: (context, state) => ref.read(leaveGuardProvider).canLeave(),
          ),
          GoRoute(
            path: mergePath,
            builder: (context, state) => MergePage(
              subject: state.uri.queryParameters['subject'],
              otherSubject: state.uri.queryParameters['other_subject'],
            ),
          ),
          GoRoute(
            path: '/entity-version/:uri/:timestamp',
            builder: (context, state) => VersionPage(
              uri: state.pathParameters['uri']!,
              timestamp: state.pathParameters['timestamp']!,
            ),
          ),
          GoRoute(
            path: '/entity-history/:uri',
            builder: (context, state) =>
                HistoryPage(uri: state.pathParameters['uri']!),
          ),
          GoRoute(
            path: '/about/:subject',
            builder: (context, state) =>
                EntityPage(uri: state.pathParameters['subject']!),
            onExit: (context, state) => ref.read(leaveGuardProvider).canLeave(),
          ),
        ],
      ),
    ],
  );
});

class _SessionListenable extends ChangeNotifier {
  _SessionListenable(Ref ref) {
    _subscription = ref.listen(sessionProvider, (_, _) => notifyListeners());
  }

  late final ProviderSubscription<AsyncValue<Object?>> _subscription;

  @override
  void dispose() {
    _subscription.close();
    super.dispose();
  }
}
