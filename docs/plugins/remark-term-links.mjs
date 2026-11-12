// SPDX-FileCopyrightText: 2026 Arcangelo Massari <arcangelo.massari@unibo.it>
//
// SPDX-License-Identifier: ISC

import { SKIP, visit } from 'unist-util-visit';
import { termDefinitions } from '../src/data/term-definitions.mjs';

// Turns each inline code that names a known term into a link to its
// definition, except inside headings and links.
export function remarkTermLinks() {
	return (tree) => {
		visit(tree, (node, index, parent) => {
			if (node.type === 'heading' || node.type === 'link') return SKIP;
			const url = node.type === 'inlineCode' && termDefinitions[node.value];
			if (!url || !parent || index === undefined) return undefined;
			parent.children[index] = { type: 'link', url, children: [node] };
			return SKIP;
		});
	};
}
