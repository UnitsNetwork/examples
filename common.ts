import * as waves from '@waves/node-api-js';
import { Web3 } from 'web3';
import * as wavesCrypto from '@waves/ts-lib-crypto';

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

export function blake2b(buffer: Buffer): Buffer {
  const arr = new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  const hashedArr = wavesCrypto.blake2b(arr);
  return Buffer.from(hashedArr.buffer, hashedArr.byteOffset, hashedArr.byteLength);
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

/**
 * Estimates the gas price based on recent blocks and current gas price.
 * @param web3 The Web3 instance with registered subscription types.
 * @param minBlocks The minimum number of blocks to consider for calculating the average gas price.
 */
export async function estimateGasPrice(web3: Web3<any>, minBlocks: number = 5): Promise<bigint> {
  const height = Number(await web3.eth.getBlockNumber());
  const blockCount = Math.max(minBlocks, Math.min(20, height));

  const gasPriceByPpi = BigInt(await web3.eth.getGasPrice());

  // Bad schema in web3:
  // @ts-ignore: Type 'bigint' is not assignable to type 'bigint[]'
  const gasPricesHistory: bigint[] = (await web3.eth.getFeeHistory(blockCount, 'latest', [])).baseFeePerGas;

  let gasPrice: bigint;
  if (gasPricesHistory.length > 0) {
    const averagePrice = gasPricesHistory.reduce((acc, fee) => acc + fee, 0n) / BigInt(gasPricesHistory.length);
    gasPrice = averagePrice > gasPriceByPpi ? averagePrice : gasPriceByPpi;
  } else {
    gasPrice = gasPriceByPpi;
  }

  return gasPrice * 110n / 100n; // + 10% tip
}
