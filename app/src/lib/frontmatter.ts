const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/;

export function splitFrontmatter(content: string): {
  frontmatter: Record<string, string>;
  body: string;
} {
  const match = content.match(FRONTMATTER_RE);
  if (!match) {
    return { frontmatter: {}, body: content };
  }

  const frontmatter: Record<string, string> = {};
  for (const line of match[1].split('\n')) {
    const colon = line.indexOf(':');
    if (colon === -1) continue;
    const key = line.slice(0, colon).trim();
    const raw = line.slice(colon + 1).trim();
    const value = raw.replace(/^['"]|['"]$/g, '');
    if (key) frontmatter[key] = value;
  }

  return { frontmatter, body: content.slice(match[0].length) };
}
