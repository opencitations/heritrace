// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../common/async_view.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import '../navigation/app_paths.dart';
import 'entity_models.dart';

const resourcePageSize = 5;

/// Loads pages of resources and exposes the loaded state to the parent, which
/// needs the linked URIs before locking the entity. The offset advances by the
/// page size, because the backend can drop rows from a page.
class PagedResources<T> extends ChangeNotifier {
  PagedResources(this._fetch);

  final Future<ResourceListPage<T>> Function(int offset) _fetch;
  final List<T> items = [];
  int _nextOffset = 0;
  bool _disposed = false;
  bool hasMore = false;
  bool loading = false;
  bool loaded = false;
  Object? error;
  Completer<void>? _firstLoad;

  Future<void> get whenLoaded =>
      loaded ? Future.value() : (_firstLoad ??= Completer<void>()).future;

  Future<void> loadMore() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final page = await _fetch(_nextOffset);
      items.addAll(page.results);
      hasMore = page.hasMore;
      _nextOffset += resourcePageSize;
    } on Exception catch (e) {
      error = e;
    } finally {
      loading = false;
      loaded = true;
      _firstLoad?.complete();
      _firstLoad = null;
      if (!_disposed) {
        notifyListeners();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}

class ResourceListSection<T> extends StatelessWidget {
  const ResourceListSection({
    required this.title,
    required this.emptyMessage,
    required this.resources,
    required this.itemBuilder,
    super.key,
  });

  final String title;
  final String emptyMessage;
  final PagedResources<T> resources;
  final Widget Function(T item) itemBuilder;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return ListenableBuilder(
      listenable: resources,
      builder: (context, _) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: appInputSpacing),
          if (resources.error != null)
            ErrorView(error: resources.error!, onRetry: resources.loadMore)
          else if (resources.loaded && resources.items.isEmpty)
            Text(emptyMessage)
          else
            Card(
              child: Column(
                children: [
                  for (final item in resources.items) itemBuilder(item),
                ],
              ),
            ),
          if (resources.loading)
            const Padding(
              padding: EdgeInsets.all(appInputSpacing),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (resources.hasMore)
            Center(
              child: OutlinedButton.icon(
                onPressed: resources.loadMore,
                icon: const Icon(Icons.expand_more),
                label: Text(t.ui.actions.loadMore),
              ),
            ),
        ],
      ),
    );
  }
}

class LinkedResourceTile extends StatelessWidget {
  const LinkedResourceTile({required this.resource, super.key});

  final LinkedResource resource;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return ListTile(
      title: Text(resource.label),
      subtitle: Text(
        [?resource.typeLabel, resource.predicateLabel].join(' · '),
      ),
      trailing: OutlinedButton.icon(
        onPressed: () => context.go(entityPath(resource.subject)),
        icon: const Icon(Icons.arrow_forward, size: 16),
        label: Text(t.ui.actions.visit),
      ),
    );
  }
}

class SimilarResourceTile extends StatelessWidget {
  const SimilarResourceTile({
    required this.resource,
    required this.subject,
    super.key,
  });

  final SimilarResource resource;
  final String subject;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context);
    return ListTile(
      title: Text(resource.label),
      trailing: OutlinedButton.icon(
        onPressed: () => context.go(mergeComparePath(subject, resource.uri)),
        icon: const Icon(Icons.merge, size: 16),
        label: Text(t.ui.entity.merge),
      ),
    );
  }
}
