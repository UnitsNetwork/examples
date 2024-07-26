export function sleep(ms: number): Promise<void> {
  return new Promise<void>(resolve => setTimeout(resolve, ms));
}

/**
 * Repeats function call every specified interval until it returns a non-null result.
 * @param f The function to execute repeatedly.
 * @param interval Interval in milliseconds between function calls.
 */
export async function repeat<T>(f: () => Promise<T | undefined>, interval: number): Promise<T> {
  let result: T | undefined;
  while (true) {
    result = await f();
    if (result === null || result === undefined) {
      await sleep(interval);
    } else {
      return result;
    }
  }
}

export function getArgumentValue(argName: string): string | undefined {
  const index = process.argv.indexOf(argName);
  if (index !== -1 && index + 1 < process.argv.length) {
    return process.argv[index + 1];
  }
  return undefined;
}

export function isString(value): value is string {
  return typeof value === 'string' || value instanceof String;
}
