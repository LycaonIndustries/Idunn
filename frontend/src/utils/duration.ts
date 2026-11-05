/**
 * Extract time duration in seconds from explicit step minutes or natural language instruction text.
 *
 * @param instruction - Natural language instruction text string.
 * @param explicitMinutes - Optional explicitly tagged step minutes.
 * @returns Parsed duration in seconds or null if no duration detected.
 */
export function extractStepDuration(
  instruction: string,
  explicitMinutes?: number | null,
): number | null {
  if (explicitMinutes && explicitMinutes > 0) {
    return Math.round(explicitMinutes * 60)
  }
  const matchMin = instruction.match(
    /(?:for\s+)?(\d+(?:\.\d+)?)\s*(?:-|to\s+\d+\s*)?(?:min(?:ute)?s?)/i,
  )
  if (matchMin && matchMin[1]) {
    return Math.round(parseFloat(matchMin[1]) * 60)
  }
  const matchSec = instruction.match(/(?:for\s+)?(\d+)\s*(?:sec(?:ond)?s?)/i)
  if (matchSec && matchSec[1]) {
    return parseInt(matchSec[1], 10)
  }
  return null
}
