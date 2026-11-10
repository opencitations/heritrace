// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/widgets.dart';

import '../../design/app_theme.dart';
import '../../design/controls.dart';
import '../../design/spacing.dart';
import '../form_model.dart';
import 'field_group_widget.dart';

class EntityForm extends StatelessWidget {
  const EntityForm({required this.node, this.paths, super.key});

  final EntityNode node;

  /// The properties to show, when only some of the node's fields appear.
  final List<String>? paths;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: node,
      builder: (context, _) {
        // Fixed values, such as the type of the record, come first.
        final displayed = node.shownGroups(paths);
        final groups = [
          ...displayed.where((group) => group.def.hasValue != null),
          ...displayed.where((group) => group.def.hasValue == null),
        ];
        // Fixed values of the same property, such as the types of a record,
        // read as one field under a single heading.
        bool continuesPrevious(int index) =>
            index > 0 &&
            groups[index].def.hasValue != null &&
            groups[index - 1].def.hasValue != null &&
            groups[index].def.uri == groups[index - 1].def.uri;
        final cards = <List<FieldGroup>>[];
        for (final (index, group) in groups.indexed) {
          if (continuesPrevious(index)) {
            cards.last.add(group);
          } else {
            cards.add([group]);
          }
        }
        final styles = AppTextStyles.of(context);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (final card in cards)
              Padding(
                padding: const EdgeInsets.only(bottom: appSectionSpacing),
                child: AppCard(
                  header: PropertyHeading(
                    label: card.first.def.displayName,
                    style: styles.groupHeader,
                    required: card.first.def.isRequired,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    spacing: appInputSpacing,
                    children: [
                      for (final group in card) FieldGroupWidget(group: group),
                    ],
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}
