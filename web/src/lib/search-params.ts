/** First value of a search param (Next.js gives an array when a key repeats); "" when absent. */
export function firstParam(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}
