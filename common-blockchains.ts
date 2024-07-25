import * as wavesCrypto from '@waves/ts-lib-crypto';
import { MerkleTree } from 'merkletreejs';
import { Web3 } from 'web3';
import { repeat } from './common-utils';
import { EcBlockContractInfo, WavesApi } from './types';

export function blake2b(buffer: Buffer): Buffer {
  const arr = new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength);
  const hashedArr = wavesCrypto.blake2b(arr);
  return Buffer.from(hashedArr.buffer, hashedArr.byteOffset, hashedArr.byteLength);
}

function parseBlockMeta(response: object): EcBlockContractInfo {
  // @ts-ignore: Property 'value' does not exist on type 'object'.
  const rawMeta = response.result.value;
  return {
    chainHeight: rawMeta._1.value,
    epochNumber: rawMeta._2.value,
  };
}

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

export function createMerkleTreeLeaves(logsDataFromElBlock: string[]) {
  return logsDataFromElBlock.map(data => blake2b(Buffer.from(data.slice(2), 'hex')));
}

export function createMerkleTree(leaves: Buffer[]) {
  const emptyLeafArr = new Uint8Array([0]);
  const emptyLeaf = Buffer.from(emptyLeafArr.buffer, emptyLeafArr.byteOffset, emptyLeafArr.byteLength);
  const emptyHashedLeaf = blake2b(emptyLeaf);
  for (let i = 1024 - leaves.length; i > 0; i--) { // Merkle tree must have 1024 leaves
    leaves.push(emptyHashedLeaf);
  }

  return new MerkleTree(leaves, blake2b);
}
