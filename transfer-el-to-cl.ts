import * as waves from '@waves/node-api-js';
import * as wavesCrypto from '@waves/ts-lib-crypto';
import * as wavesTransactions from '@waves/waves-transactions';
import fs from 'fs';
import { MerkleTree } from 'merkletreejs';
import { Contract, Web3 } from 'web3';
import * as common from './common.ts';

// Hack to get a current dir: https://stackoverflow.com/a/50053801
import { dirname } from 'path';
import { fileURLToPath } from 'url';
const __dirname = dirname(fileURLToPath(import.meta.url));

function getArgumentValue(argName: string): string | undefined {
  const index = process.argv.indexOf(argName);
  if (index !== -1 && index + 1 < process.argv.length) {
    return process.argv[index + 1];
  }
  return undefined;
}

const chainIdStr = getArgumentValue('--chain-id') || 'S'; // StageNet by default
const chainId = chainIdStr.charCodeAt(0);

const amount = getArgumentValue('--amount') || '0.01';

const clAccountPrivateKey = getArgumentValue('--waves-private-key');
const elAccountPrivateKey = getArgumentValue('--eth-private-key');
if (!(clAccountPrivateKey && elAccountPrivateKey)) {
  console.error(
    'Transfer native tokens from Execution Layer to Consensus Layer (Waves).\n\
At least two arguments required:\n\
  npx tsx transfer-el-to-cl.ts --waves-private-key <Waves private key in base58> --eth-private-key <Ethereum private key in HEX with 0x>\n\
Additional optional arguments:\n\
  --chain-id <S|T|W>, S by default: S - StageNet, not suported for now: T - TestNet, W - MainNet\n\
  --amount N, 0.01 by default: amount of transferred Unit0 tokens'
  );
  process.exit(1);
}

let clNodeApiUrl = "https://nodes-stagenet.wavesnodes.com";
let elNodeApiUrl = "https://rpc-stagenet.unit0.dev";
let chainContractAddress = "3Mew9817x6rePmCUKNAiRxuzNEP8F2XK1Kd";
let elBridgeAddress = "0xadc0526e55b2234e62e3cc2ac13191552bed542f";

if (chainIdStr == 'T') {
  clNodeApiUrl = "https://nodes-testnet.wavesnodes.com";
  elNodeApiUrl = "https://rpc-testnet.unit0.dev";
  chainContractAddress = "3MsqKJ6o1ABE37676cHHBxJRs6huYTt72ch";
  elBridgeAddress = "0x33ce7f46EbC22D01B50e2eEb8DcD26C31a0e027C";
}

const clAccountPublicKey = wavesTransactions.libs.crypto.publicKey({ privateKey: clAccountPrivateKey });
const clAccountAddress = wavesTransactions.libs.crypto.address({ publicKey: clAccountPublicKey }, chainId);
const clAccountPkHashBytes = wavesCrypto.base58Decode(clAccountAddress).slice(2, 22);

const transfers = [
  { recipient: clAccountAddress, amount: Web3.utils.toWei(amount, 'ether') }
];
const transferIndex = 0;
const transfer = transfers[transferIndex]

let wavesApi = waves.create(clNodeApiUrl);

let ecApi = new Web3(elNodeApiUrl);
ecApi.eth.transactionConfirmationBlocks = 1;
ecApi.eth.transactionBlockTimeout = 10;
ecApi.eth.transactionPollingTimeout = 120000;
ecApi.eth.transactionPollingInterval = 3000;
ecApi.eth.defaultAccount = elAccountPrivateKey;

const elAccount = ecApi.eth.accounts.privateKeyToAccount(elAccountPrivateKey);

const elBridgeAbi = JSON.parse(fs.readFileSync(`${__dirname}/bridge-abi.json`, { encoding: 'utf-8' }));

const elBridgeContract = new Contract(elBridgeAbi, elBridgeAddress, ecApi);

console.log(`Sending ${amount} Unit0 from ${elAccount.address} in Execution Layer to ${clAccountAddress} in Consensus (Waves) Layer`);

// Call "sendNative" on Bridge in EL
console.log('Call "sendNative" on Bridge in EL');

const sendNativeCall = elBridgeContract.methods.sendNative(clAccountPkHashBytes);
let sendNativeTx = {
  to: elBridgeContract.options.address,
  from: elAccount.address,
  gas: await sendNativeCall.estimateGas({
    from: elAccount.address,
    value: transfer.amount,
  }),
  gasPrice: await common.estimateGasPrice(ecApi),
  value: transfer.amount,
  data: sendNativeCall.encodeABI(),
};

const sendNativeSignedTx = await ecApi.eth.accounts.signTransaction(sendNativeTx, elAccount.privateKey);
const sendNativeResult = await ecApi.eth.sendSignedTransaction(sendNativeSignedTx.rawTransaction);

console.log('EL sendNative result:', sendNativeResult);

// Get an index of withdrawal in the block with this withdrawal

const logsInElBlock = await ecApi.eth.getPastLogs({
  blockHash: sendNativeResult.blockHash,
  address: elBridgeAddress,
  topics: elBridgeContract.events.SentNative().args.topics
});

const lookingForData = sendNativeResult.logs[0].data;
console.log(logsInElBlock);

const withdrawIndex = logsInElBlock.findIndex((log) => log.data == lookingForData);
console.log('Index of withdrawal:', withdrawIndex);

// Getting proofs

const emptyLeafArr = new Uint8Array([0]);
const emptyLeaf = Buffer.from(emptyLeafArr.buffer, emptyLeafArr.byteOffset, emptyLeafArr.byteLength);
const emptyHashedLeaf = common.blake2b(emptyLeaf);

let leaves = logsInElBlock.map(log => common.blake2b(Buffer.from(log.data.slice(2), 'hex')));

for (let i = 1024 - leaves.length; i > 0; i--) { // Merkle tree must have 1024 leaves
  leaves.push(emptyHashedLeaf);
}

const merkleTree = new MerkleTree(leaves, common.blake2b);
let proofs = merkleTree.getProof(leaves[withdrawIndex])

// Waiting for EL block with our withdrawal

console.log(`Waiting EL block ${sendNativeResult.blockHash} confirmation on CL`);
const withdrawBlockMeta = await common.waitForEcBlock(wavesApi, chainContractAddress, sendNativeResult.blockHash);

console.log(`Withdraw block meta: %O`, withdrawBlockMeta);

// Waiting for finalization

console.log(`Wait until EL block #${withdrawBlockMeta.chainHeight} becomes finalized`);
await common.repeat(async () => {
  // NOTE: values sometimes are cached if we ask this a dockerized service
  const currFinalizedBlock = await common.chainContractCurrFinalizedBlock(wavesApi, chainContractAddress);
  console.log(`Current finalized height: ${currFinalizedBlock.chainHeight}`);
  return currFinalizedBlock.chainHeight < withdrawBlockMeta.chainHeight ? null : true;
}, 2000);

// Preparing a CL transaction

const withdrawSignedTx = wavesTransactions.invokeScript(
  {
    dApp: chainContractAddress,
    call: {
      function: "withdraw",
      args: [
        {
          type: "string",
          value: sendNativeResult.blockHash.slice(2)
        },
        {
          type: "list",
          value: proofs.map(x => {
            return {
              type: "binary",
              value: x.data.toString('base64')
            };
          })
        },
        {
          type: "integer",
          value: withdrawIndex
        },
        {
          type: "integer",
          value: Number(BigInt(transfer.amount) / (10n ** 10n)) // 10^10 - see EL_TO_CL_RATIO in bridge.sol
        },
      ]
    },
    payment: [],
    fee: 500000,
    chainId: chainIdStr
  },
  {
    privateKey: clAccountPrivateKey
  }
)

// Sending the withdraw transaction to CL

const withdrawSendSignedTxResult = await wavesApi.transactions.broadcast(withdrawSignedTx);
console.log('CL withdrawal result:', withdrawSendSignedTxResult);

