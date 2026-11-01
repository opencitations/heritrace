// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import 'package:flutter/cupertino.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../design/app_theme.dart';
import '../design/spacing.dart';
import '../navigation/app_paths.dart';
import 'references.dart';

Future<void> openExternal(String url) =>
    launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);

class LinkText extends StatelessWidget {
  const LinkText({required this.label, required this.onTap, super.key});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: Text(
          label,
          style: const TextStyle(
            color: AppColors.primary,
            decoration: TextDecoration.underline,
          ),
        ),
      ),
    );
  }
}

class AgentRefView extends StatelessWidget {
  const AgentRefView({required this.agent, super.key});

  final AgentRef agent;

  @override
  Widget build(BuildContext context) {
    final url = agent.url;
    if (url == null) {
      return Text(agent.label);
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (agent.kind == 'orcid') ...[
          Image.asset('assets/images/orcid-logo.png', height: 16),
          const SizedBox(width: 4),
        ],
        Flexible(
          child: LinkText(
            label: agent.orcidId == null
                ? agent.label
                : '${agent.label} [orcid:${agent.orcidId}]',
            onTap: () => openExternal(url),
          ),
        ),
      ],
    );
  }
}

class SourceRefView extends StatelessWidget {
  const SourceRefView({required this.source, super.key});

  final SourceRef source;

  @override
  Widget build(BuildContext context) {
    final url = source.url;
    if (url == null) {
      return Text(source.label);
    }
    final link = switch (source.kind) {
      'version' => LinkText(
        label: source.label,
        onTap: () =>
            context.go(entityVersionPath(source.entityUri!, source.timestamp!)),
      ),
      _ => LinkText(label: source.label, onTap: () => openExternal(url)),
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (source.kind == 'zenodo') ...[
              Image.asset('assets/images/zenodo-logo.png', height: 20),
              const SizedBox(width: appInputSpacing / 2),
            ],
            Flexible(child: link),
          ],
        ),
        if (source.extra != null)
          Text(source.extra!, style: AppTextStyles.of(context).caption),
      ],
    );
  }
}
