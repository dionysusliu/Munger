import type { Link, Parent, PhrasingContent, Root, Text } from 'mdast';
import type { Plugin } from 'unified';
import { visit } from 'unist-util-visit';

const WIKILINK_RE = /\[\[([^\]]+)\]\]/g;

function splitWikilinks(text: string, titleToSlug: Map<string, string>): PhrasingContent[] {
  const nodes: PhrasingContent[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = WIKILINK_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push({ type: 'text', value: text.slice(lastIndex, match.index) });
    }

    const title = match[1].trim();
    const slug = titleToSlug.get(title.toLowerCase());
    const link: Link = {
      type: 'link',
      url: slug ? `/wiki/${slug}` : '#unresolved',
      children: [{ type: 'text', value: title }],
    };
    nodes.push(link);
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    nodes.push({ type: 'text', value: text.slice(lastIndex) });
  }

  return nodes.length > 0 ? nodes : [{ type: 'text', value: text }];
}

export function remarkWikilink(titleToSlug: Map<string, string>): Plugin<[], Root> {
  return () => (tree) => {
    visit(tree, 'text', (node: Text, index, parent: Parent | undefined) => {
      if (!parent || index === undefined || !node.value.includes('[[')) {
        return;
      }
      const replacements = splitWikilinks(node.value, titleToSlug);
      if (replacements.length === 1 && replacements[0].type === 'text') {
        return;
      }
      parent.children.splice(index, 1, ...replacements);
    });
  };
}
