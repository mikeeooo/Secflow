const localDateFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: 'Europe/Chisinau',
  year: 'numeric', month: '2-digit', day: '2-digit',
})

function localDateAt(timestamp: number): string {
  const values = Object.fromEntries(
    localDateFormatter.formatToParts(new Date(timestamp)).map(part => [part.type, part.value]),
  )
  return `${values.year}-${values.month}-${values.day}`
}

function firstInstantOfLocalDate(day: string): number {
  const utcMidnight = Date.parse(`${day}T00:00:00.000Z`)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || Number.isNaN(utcMidnight)) {
    throw new RangeError(`Invalid calendar date: ${day}`)
  }
  let low = utcMidnight - 18 * 60 * 60 * 1000
  let high = utcMidnight + 18 * 60 * 60 * 1000
  while (low < high) {
    const middle = Math.floor((low + high) / 2)
    if (localDateAt(middle) < day) low = middle + 1
    else high = middle
  }
  return low
}

export function localDayUtcBounds(day: string): {start: string; end: string} {
  const nextDay = new Date(Date.parse(`${day}T00:00:00.000Z`) + 86_400_000)
    .toISOString().slice(0, 10)
  return {
    start: new Date(firstInstantOfLocalDate(day)).toISOString(),
    end: new Date(firstInstantOfLocalDate(nextDay) - 1).toISOString(),
  }
}
