/** Only http(s) URLs from data files or user input may become links. */
export function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

/** "https://www.example.com/a" -> "example.com/a" */
export function displayUrl(url: string): string {
  return url.replace(/^https?:\/\/(www\.)?/i, "");
}
