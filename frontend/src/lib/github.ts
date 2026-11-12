/** "owner/repo" for display, from a normalised https://github.com/... URL. */
export function repoName(url: string): string {
  const path = url.replace(/^https:\/\/github\.com\//, "");
  return path.split("/").slice(0, 2).join("/");
}

/** Client-side mirror of the server rule (the server normalises and re-checks). */
export function isGithubRepoUrl(value: string): boolean {
  return /^https:\/\/(www\.)?github\.com\/[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}\/[A-Za-z0-9._-]{1,100}([/?#]\S*)?$/.test(value.trim());
}
