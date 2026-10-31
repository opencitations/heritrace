// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/material.dart';

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
      builder: (context, _) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final group in node.groups)
            if (group.def.shouldBeDisplayed)
              Padding(
                padding: const EdgeInsets.only(bottom: appSectionSpacing),
                child: FieldGroupWidget(group: group),
              ),
        ],
      ),
    );
  }
}
