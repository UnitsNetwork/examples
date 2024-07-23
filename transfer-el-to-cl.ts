import * as waves from '@waves/node-api-js';
import * as wavesCrypto from '@waves/ts-lib-crypto';
import * as wavesTransactions from '@waves/waves-transactions';
import fs from 'fs';
import { Contract, Transaction, Web3 } from 'web3';
import { Web3Account } from 'web3-eth-accounts';
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

interface ElToClTransfer {
  recipient: string,
  amount: string
}
const transfer: ElToClTransfer = {
  recipient: clAccountAddress,
  amount: Web3.utils.toWei(amount, 'ether')
};

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
async function sendElRequest(transfer: ElToClTransfer, fromAccount: Web3Account, nonce: number, gasPrice: bigint) {
  const clAccountPkHashBytes = wavesCrypto.base58Decode(transfer.recipient).slice(2, 22);
  const sendNativeCall = elBridgeContract.methods.sendNative(clAccountPkHashBytes);
  const nonceHex = Web3.utils.toHex(nonce);
  const gasPriceHex = Web3.utils.toWei(gasPrice, "wei");
  const dataAbi = sendNativeCall.encodeABI();
  const gas = await sendNativeCall.estimateGas({
    from: fromAccount.address,
    nonce: nonceHex,
    gasPrice: gasPrice,
    value: transfer.amount,
    data: dataAbi
  });
  let sendNativeTx: Transaction = {
    from: fromAccount.address,
    nonce: nonceHex,
    to: elBridgeContract.options.address,
    gas: gas,
    gasPrice: gasPriceHex,
    value: transfer.amount,
    data: dataAbi,
  };

  const sendNativeSignedTx = await ecApi.eth.accounts.signTransaction(sendNativeTx, elAccount.privateKey);
  return await ecApi.eth.sendSignedTransaction(sendNativeSignedTx.rawTransaction);
}

const gasPrice = await common.estimateGasPrice(ecApi);
const initNonce = Number(await ecApi.eth.getTransactionCount(elAccount.address));

console.log('Call "sendNative" on Bridge in EL');
const sendNativeResult = await sendElRequest(transfer, elAccount, initNonce, gasPrice);
console.log('EL sendNative result:', sendNativeResult);

const blockHash: string = sendNativeResult.blockHash;
console.log(`Block hash: ${blockHash}`);

// Get an index of withdrawal in the block with this withdrawal

const logsInElBlock = await ecApi.eth.getPastLogs({
  blockHash: blockHash,
  address: elBridgeAddress,
  topics: elBridgeContract.events.SentNative().args.topics
});

const withdrawIndex = logsInElBlock.findIndex((log: any) => log.transactionHash == sendNativeResult.transactionHash);
console.log(`Index of withdrawal: ${withdrawIndex}`);

// Getting proofs

const merkleTreeLeaves = common.createMerkleTreeLeaves(logsInElBlock.map((l: any) => l.data));
const merkleTree = common.createMerkleTree(merkleTreeLeaves);
let proofs = merkleTree.getProof(merkleTreeLeaves[withdrawIndex], withdrawIndex)

// Waiting for EL block with our withdrawal

console.log(`Waiting EL block ${blockHash} confirmation on CL`);
const withdrawBlockMeta = await common.waitForEcBlock(wavesApi, chainContractAddress, blockHash);

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
function signWithdraw(blockHash: string, proofs: any[], withdrawIndex: number, amountInWei: string) {
  return wavesTransactions.invokeScript(
    {
      dApp: chainContractAddress,
      call: {
        function: "withdraw",
        args: [
          {
            type: "string",
            value: blockHash.slice(2)
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
            value: Number(BigInt(amountInWei) / (10n ** 10n)) // 10^10 - see EL_TO_CL_RATIO in bridge.sol
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
}

const withdrawSignedTx = signWithdraw(blockHash, proofs, withdrawIndex, transfer.amount);

// Sending the withdraw transaction to CL

const withdrawSendSignedTxResult = await wavesApi.transactions.broadcast(withdrawSignedTx);
console.log('CL withdrawal result:', withdrawSendSignedTxResult);
