// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../common/async_view.dart';
import '../design/controls.dart';
import '../design/spacing.dart';
import '../i18n/translations.g.dart';
import 'orcid.dart';
import 'settings_draft.dart';
import 'settings_repository.dart';

/// One row per ORCID iD, each checked on its own and, once valid, shown with
/// the name of its ORCID account.
class OrcidListField extends StatefulWidget {
  const OrcidListField({
    required this.draft,
    required this.label,
    required this.orcids,
    required this.location,
    super.key,
  });

  final SettingsDraft draft;
  final String label;
  final List<String> orcids;
  final String location;

  @override
  State<OrcidListField> createState() => _OrcidListFieldState();
}

class _OrcidListFieldState extends State<OrcidListField> {
  // The iDs are plain strings and may repeat, so each row gets its own key
  // to keep its text field when a row above it is removed.
  final _keys = <Key>[];
  Key? _added;

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context).ui.settings.system;
    final orcids = widget.orcids;
    final editing = widget.draft.editing;
    while (_keys.length < orcids.length) {
      _keys.add(UniqueKey());
    }
    _keys.length = orcids.length;
    return AppLabeledField(
      label: widget.label,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        spacing: appInputSpacing,
        children: [
          for (final (index, orcid) in orcids.indexed)
            _OrcidRow(
              key: _keys[index],
              value: orcid,
              autofocus: _keys[index] == _added,
              serverIssue: widget.draft.issue('${widget.location}.$index'),
              onChanged: editing
                  ? (value) =>
                        widget.draft.update(() => orcids[index] = value.trim())
                  : null,
              onRemove: editing
                  ? () {
                      _keys.removeAt(index);
                      widget.draft.restructure(() => orcids.removeAt(index));
                    }
                  : null,
            ),
          if (orcids.isEmpty) FieldCaption(t.safelistEmpty),
          if (editing)
            Align(
              alignment: Alignment.centerLeft,
              child: AppButton(
                icon: CupertinoIcons.add_circled,
                label: t.addOrcid,
                onPressed: () {
                  _added = UniqueKey();
                  _keys.add(_added!);
                  widget.draft.restructure(() => orcids.add(''));
                },
              ),
            ),
        ],
      ),
    );
  }
}

class _OrcidRow extends ConsumerStatefulWidget {
  const _OrcidRow({
    required this.value,
    required this.autofocus,
    required this.serverIssue,
    required this.onChanged,
    required this.onRemove,
    super.key,
  });

  final String value;
  final bool autofocus;
  final String? serverIssue;

  /// Both null when the row shows the iD as text.
  final ValueChanged<String>? onChanged;
  final VoidCallback? onRemove;

  @override
  ConsumerState<_OrcidRow> createState() => _OrcidRowState();
}

class _OrcidRowState extends ConsumerState<_OrcidRow> {
  late final _controller = TextEditingController(text: widget.value);
  final _focus = FocusNode();

  @override
  void initState() {
    super.initState();
    // A half-typed iD is not wrong yet, so its error waits for the field to
    // lose focus.
    _focus.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _controller.dispose();
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = Translations.of(context).ui.settings.system;
    final text = widget.value;
    final orcidId = orcidIdOf(text);
    final valid = isValidOrcidId(orcidId);
    final invalid = text.isNotEmpty && !valid && !_focus.hasFocus;
    if (widget.onChanged == null) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(text),
          if (valid) _OrcidAccount(orcidId: orcidId),
        ],
      );
    }
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      spacing: appInputSpacing,
      children: [
        if (widget.onRemove case final onRemove?)
          RemoveButton(label: t.removeOrcid, onPressed: onRemove),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AppTextField(
                controller: _controller,
                focusNode: _focus,
                autofocus: widget.autofocus,
                placeholder: '0000-0002-1825-0097',
                errorText: invalid ? t.orcidInvalid : widget.serverIssue,
                onChanged: widget.onChanged,
              ),
              if (valid) _OrcidAccount(orcidId: orcidId),
            ],
          ),
        ),
      ],
    );
  }
}

class _OrcidAccount extends ConsumerWidget {
  const _OrcidAccount({required this.orcidId});

  final String orcidId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = Translations.of(context).ui.settings.system;
    final (text, error) = ref
        .watch(orcidLookupProvider(orcidId))
        .when(
          data: (lookup) => switch (lookup) {
            OrcidFound(:final name) => (name ?? t.orcidNoName, false),
            OrcidMissing() => (t.orcidMissing, true),
            OrcidUnreachable() => (t.orcidUnreachable, false),
          },
          loading: () => (t.orcidChecking, false),
          error: (failure, _) => (describeError(context, failure), true),
        );
    return FieldCaption(text, error: error);
  }
}
