// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter_test/flutter_test.dart';
import 'package:heritrace/entity/entity_models.dart';
import 'package:heritrace/entity/resource_lists.dart';

void main() {
  test(
    'the offset advances by the page size even when a page is short',
    () async {
      final offsets = <int>[];
      final resources = PagedResources<String>((offset) async {
        offsets.add(offset);
        return const ResourceListPage(results: ['only one'], hasMore: true);
      });

      await resources.loadMore();
      await resources.loadMore();

      expect(offsets, [0, resourcePageSize]);
      expect(resources.items, ['only one', 'only one']);
      resources.dispose();
    },
  );
}
