import * as waves from '@waves/node-api-js';

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

export interface EcBlockContractInfo {
  chainHeight: number,
  epochNumber: number
}

function parseBlockMeta(response: object): EcBlockContractInfo {
  // @ts-ignore: Property 'value' does not exist on type 'object'.
  const rawMeta = response.result.value;
  return {
    chainHeight: rawMeta._1.value,
    epochNumber: rawMeta._2.value,
  };
}

export type WavesApi = ReturnType<typeof waves.create>;

export async function waitForEcBlock(wavesApi: WavesApi, chainContractAddress: string, blockHash: string): Promise<EcBlockContractInfo> {
  const getBlockData = async () => {
    try {
      return parseBlockMeta(await wavesApi.utils.fetchEvaluate(chainContractAddress, `blockMeta("${blockHash.slice(2)}")`));
    } catch (e) {
      return undefined;
    }
  };
  return await repeat(getBlockData, 2000);
}

export async function chainContractCurrFinalizedBlock(wavesApi: WavesApi, chainContractAddress: string): Promise<EcBlockContractInfo> {
  // @ts-ignore: Property 'value' does not exist on type 'object'.
  return parseBlockMeta(await wavesApi.utils.fetchEvaluate(chainContractAddress, `blockMeta(getStringValue("finalizedBlock"))`));
}
