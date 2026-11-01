// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/widgets.dart';

import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../form_model.dart';
import 'field_group_widget.dart';

class EntityForm extends StatelessWidget {
  const EntityForm({required this.node, super.key});

  final EntityNode node;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: node,
      builder: (context, _) {
        final groups = node.groups
            .where((group) => group.def.shouldBeDisplayed)
            .toList();
        // Fixed values of the same property, such as the types of a record,
        // read as one field under a single heading.
        bool continuesPrevious(int index) =>
            index > 0 &&
            groups[index].def.hasValue != null &&
            groups[index - 1].def.hasValue != null &&
            groups[index].def.uri == groups[index - 1].def.uri;
        final cards = <List<Widget>>[];
        for (final (index, group) in groups.indexed) {
          final continues = continuesPrevious(index);
          if (!continues) {
            cards.add([]);
          }
          cards.last.add(
            FieldGroupWidget(group: group, showHeading: !continues),
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (final card in cards)
              Padding(
                padding: const EdgeInsets.only(bottom: appSectionSpacing),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: card,
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
