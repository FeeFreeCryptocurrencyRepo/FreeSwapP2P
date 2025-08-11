import os
import re
import json
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from dotenv import load_dotenv
from iota_sdk import (
    SyncOptions,
    ClientOptions,
    CoinType,
    Features,
    OutputParams,
    NativeToken,
    Assets,
    HexStr,
    StrongholdSecretManager,
    StorageDeposit,
    ReturnStrategy,
    Utils,
    Wallet,
    utf8_to_hex,
)
from bech32 import bech32_decode, convertbits

load_dotenv()

"""
IOTA/Shimmer wallet helpers using Stronghold storage.

This module provides:
- Wallet/account lifecycle: create, recover, sign-in
- Address and balance helpers
- Simple send (base coin or native tokens)
- Parsing helpers for outputs/transactions
- Convenience utilities (SMR bech32 -> hex, etc.)

All paths are placed under:
  ~/Documents/Stronghold/<AccountName>/
"""


# ------------------------- Wallet Lifecycle ------------------------- #
def CreateWalletTest(NameYourAcount: str, NameYourPin: str, Password: str) -> None:
    """
    Test helper to create or recover a wallet at:
      ~/Documents/Stronghold/<NameYourAcount>/

    If a Stronghold snapshot exists, it opens it and tries to recover accounts.
    If not, and `recover` is True, it uses a placeholder mnemonic to recover.
    Otherwise it generates a fresh mnemonic and creates a new account with alias = NameYourPin.
    Prints key info (first address) to stdout.
    """
    home_directory = Path.home()
    stronghold_folder = home_directory / "Documents" / "Stronghold" / NameYourAcount
    stronghold_folder.mkdir(parents=True, exist_ok=True)

    stronghold_snapshot_file = stronghold_folder / "vault.stronghold"
    STRONGHOLD_SNAPSHOT_PATH = str(stronghold_snapshot_file)
    rocksdb_storage_path = stronghold_folder / "rocksdb_storage"
    rocksdbstringpath = str(rocksdb_storage_path)

    ACCOUNT_ALIAS = NameYourPin
    node_url = os.environ.get("NODE_URL", "https://api.shimmer.network")
    STRONGHOLD_PASSWORD = os.environ.get("STRONGHOLD_PASSWORD", Password)
    client_options = ClientOptions(nodes=[node_url])

    # Placeholder mnemonic for testing recovery flows. Replace if you rely on a fixed seed.
    mnemonic0 = "your mnemonic words here ..."
    recover = True
    created_account = False

    if stronghold_snapshot_file.is_file():
        secret_manager = StrongholdSecretManager(STRONGHOLD_SNAPSHOT_PATH, STRONGHOLD_PASSWORD)
        wallet = Wallet(
            client_options=client_options,
            coin_type=CoinType.SHIMMER,
            secret_manager=secret_manager,
            storage_path=rocksdbstringpath,
        )
        accounts = wallet.recover_accounts(0, 3, 10, None)
        print("Using existing Stronghold file.")
        print(json.dumps(accounts, indent=4))
    elif recover:
        secret_manager = StrongholdSecretManager(STRONGHOLD_SNAPSHOT_PATH, STRONGHOLD_PASSWORD)
        wallet = Wallet(
            client_options=client_options,
            coin_type=CoinType.SHIMMER,
            secret_manager=secret_manager,
            storage_path=rocksdbstringpath,
        )
        wallet.store_mnemonic(mnemonic0)
        account = wallet.create_account(ACCOUNT_ALIAS)
        created_account = True
        print(f"Created recovery account with alias: {ACCOUNT_ALIAS}")
    else:
        secret_manager = StrongholdSecretManager(STRONGHOLD_SNAPSHOT_PATH, STRONGHOLD_PASSWORD)
        wallet = Wallet(
            client_options=client_options,
            coin_type=CoinType.SHIMMER,
            secret_manager=secret_manager,
            storage_path=rocksdbstringpath,
        )
        mnemonic = Utils.generate_mnemonic()
        print(f"Mnemonic: {mnemonic}")
        wallet.store_mnemonic(mnemonic)
        account = wallet.create_account(ACCOUNT_ALIAS)
        created_account = True
        print(f"Created new account with alias: {ACCOUNT_ALIAS}")

    if created_account:
        address = account.addresses()[0]
        print(f"Address:\n{address.address}")


def SignInToAccount(NameYourAcount: str, NameYourPin: str, Password: str):
    """
    Open an existing wallet stored in:
      ~/Documents/Stronghold/<NameYourAcount>/

    Returns:
        (wallet, accounts_info) or (None, None) if not found/error.
    """
    home_directory = Path.home()
    stronghold_folder = home_directory / "Documents" / "Stronghold" / NameYourAcount
    stronghold_snapshot_file = stronghold_folder / "vault.stronghold"
    STRONGHOLD_SNAPSHOT_PATH = str(stronghold_snapshot_file)
    rocksdb_storage_path = stronghold_folder / "rocksdb_storage"
    rocksdbstringpath = str(rocksdb_storage_path)

    ACCOUNT_ALIAS = NameYourPin
    node_url = os.environ.get("NODE_URL", "https://api.shimmer.network")
    STRONGHOLD_PASSWORD = os.environ.get("STRONGHOLD_PASSWORD", Password)
    client_options = ClientOptions(nodes=[node_url])

    try:
        if stronghold_snapshot_file.is_file():
            secret_manager = StrongholdSecretManager(STRONGHOLD_SNAPSHOT_PATH, STRONGHOLD_PASSWORD)
            wallet = Wallet(
                client_options=client_options,
                coin_type=CoinType.SHIMMER,
                secret_manager=secret_manager,
                storage_path=rocksdbstringpath,
            )
            accounts0 = wallet.recover_accounts(0, 3, 10, None)
            return wallet, accounts0
        else:
            print("Stronghold file does not exist. Please create a wallet first.")
            return None, None
    except Exception as e:
        print(f"An error occurred during sign in: {e}")
        return None, None


def RecoverWallet(NameYourAcount: str, NameYourPin: str, Password: str, mnemonic: str) -> bool:
    """
    Recover a wallet with a provided mnemonic into:
      ~/Documents/Stronghold/<NameYourAcount>/

    Creates an account with alias = NameYourPin.

    Returns:
        True on success, False if the stronghold exists or on error.
    """
    home_directory = Path.home()
    stronghold_folder = home_directory / "Documents" / "Stronghold" / NameYourAcount
    stronghold_snapshot_file = stronghold_folder / "vault.stronghold"
    STRONGHOLD_SNAPSHOT_PATH = str(stronghold_snapshot_file)
    rocksdb_storage_path = stronghold_folder / "rocksdb_storage"
    rocksdbstringpath = str(rocksdb_storage_path)

    ACCOUNT_ALIAS = NameYourPin
    node_url = os.environ.get("NODE_URL", "https://api.shimmer.network")
    STRONGHOLD_PASSWORD = os.environ.get("STRONGHOLD_PASSWORD", Password)
    client_options = ClientOptions(nodes=[node_url])

    if stronghold_snapshot_file.is_file():
        print("Stronghold already exists. Use CreateWallet for a fresh wallet.")
        return False

    try:
        secret_manager = StrongholdSecretManager(STRONGHOLD_SNAPSHOT_PATH, STRONGHOLD_PASSWORD)
        wallet = Wallet(
            client_options=client_options,
            coin_type=CoinType.SHIMMER,
            secret_manager=secret_manager,
            storage_path=rocksdbstringpath,
        )
        wallet.store_mnemonic(mnemonic)
        wallet.create_account(ACCOUNT_ALIAS)
        print(f"Recovered account with alias: {ACCOUNT_ALIAS}")
        return True
    except Exception as e:
        print(f"Error during wallet recovery: {str(e)}")
        return False


def CreateWallet(NameYourAcount: str, NameYourPin: str, Password: str) -> Optional[str]:
    """
    Create a brand new wallet and account at:
      ~/Documents/Stronghold/<NameYourAcount>/

    Returns:
        The generated mnemonic string on success, or None if the wallet exists.
    """
    home_directory = Path.home()
    stronghold_folder = home_directory / "Documents" / "Stronghold" / NameYourAcount
    stronghold_snapshot_file = stronghold_folder / "vault.stronghold"
    STRONGHOLD_SNAPSHOT_PATH = str(stronghold_snapshot_file)
    rocksdb_storage_path = stronghold_folder / "rocksdb_storage"
    rocksdbstringpath = str(rocksdb_storage_path)

    ACCOUNT_ALIAS = NameYourPin
    node_url = os.environ.get("NODE_URL", "https://api.shimmer.network")
    STRONGHOLD_PASSWORD = os.environ.get("STRONGHOLD_PASSWORD", Password)
    client_options = ClientOptions(nodes=[node_url])

    if stronghold_snapshot_file.is_file():
        print("Wallet already exists for this Account Name. Return to Login")
        return None

    secret_manager = StrongholdSecretManager(STRONGHOLD_SNAPSHOT_PATH, STRONGHOLD_PASSWORD)
    wallet = Wallet(
        client_options=client_options,
        coin_type=CoinType.SHIMMER,
        secret_manager=secret_manager,
        storage_path=rocksdbstringpath,
    )
    mnemonic = Utils.generate_mnemonic()
    wallet.store_mnemonic(mnemonic)
    wallet.create_account(ACCOUNT_ALIAS)
    print("Successfully created account. Save your mnemonic securely.")
    return str(mnemonic)


# ------------------------- Send Transactions ------------------------- #
def send_transaction(
    wallet: Wallet,
    NameYourPin1: str,
    recipient_address1: str,
    amount: int,
    note: Optional[str] = None,
    tag: Optional[str] = None,
):
    """
    Send base coin (SMR) to a bech32 address.

    Args:
        wallet: Wallet instance.
        NameYourPin1: Account alias to send from.
        recipient_address1: Receiver bech32 address.
        amount: Amount in micro-SMR (1 SMR = 1_000_000).
        note, tag: Not used in this simplified version (reserved for future features).

    Returns:
        Transaction object on success, or {'amount':'0','timestamp':'0'} on error.
    """
    try:
        params = [{"address": recipient_address1, "amount": str(amount)}]
        account = wallet.get_account(NameYourPin1)
        tx = account.send_with_params(params)
        return tx
    except Exception:
        return {"amount": "0", "timestamp": "0"}


def send_transaction_any(
    wallet: Wallet,
    NameYourPin1: str,
    recipient_address_str: str,
    custom_amount: int,
    token_id: Optional[str] = None,
    custom_metadata_str: Optional[str] = None,
):
    """
    Send either base coin or a native token with optional metadata.

    - When token_id is None: sends base coin `custom_amount`.
    - When token_id is provided: sends the given native token amount (hex-encoded).
    """
    try:
        account = wallet.get_account(NameYourPin1)

        if token_id is None:
            output = account.prepare_output(
                OutputParams(
                    recipientAddress=recipient_address_str,
                    amount=str(custom_amount),
                    features=Features(metadata=HexStr(utf8_to_hex(utf8_data=custom_metadata_str or ""))),
                )
            )
            tx = account.send_outputs([output])
        else:
            storage_deposit_options = StorageDeposit(
                returnStrategy=ReturnStrategy.Gift, useExcessIfLow=True
            )
            output = account.prepare_output(
                OutputParams(
                    recipientAddress=recipient_address_str,
                    amount=str(0),
                    assets=Assets(nativeTokens=[NativeToken(token_id, hex(custom_amount))]),
                    features=Features(metadata=HexStr(utf8_to_hex(utf8_data=custom_metadata_str or ""))),
                    storageDeposit=storage_deposit_options,
                )
            )
            tx = account.send_outputs([output])

        print(tx)
        return tx
    except Exception as e:
        return {"amount": "0", "timestamp": "0", "error": str(e)}


# ------------------------- Transaction Helpers ------------------------- #
def parse_transaction_data(transaction_data: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract 'amount' and 'timestamp' from a transaction-like object by regex parsing its string form.

    Returns:
        (amount, timestamp) or (None, None)
    """
    try:
        amount_match = re.search(r"'amount': '(\d+)'", str(transaction_data))
        amount = int(amount_match.group(1)) if amount_match else None

        timestamp_match = re.search(r"timestamp='(\d+)'", str(transaction_data))
        timestamp = int(timestamp_match.group(1)) if timestamp_match else None

        return amount, timestamp
    except Exception:
        return None, None


def sync_account(wallet: Wallet, NameYourPin: str):
    """
    Synchronize an account to refresh local state.
    """
    try:
        account = wallet.get_account(NameYourPin)
        if account:
            account.sync(None)
            print(f"Account '{NameYourPin}' synchronized.")
            return account
        print(f"Account '{NameYourPin}' not found.")
        return None
    except Exception as e:
        print(f"Error synchronizing '{NameYourPin}': {e}")
        return None


def get_transactions(wallet: Wallet, account_alias: str):
    """
    Return all transactions for an account (implementation depends on SDK bindings).
    """
    try:
        account = wallet.get_account(account_alias)
        all_transactions = account.get_transaction()
        return all_transactions
    except Exception as e:
        return str(e)


def get_last_n_transactions(wallet: Wallet, account_alias: str, n: int = 10):
    """
    Return the last N transactions for an account.
    """
    try:
        account = wallet.get_account(account_alias)
        all_transactions = account.transactions()
        return all_transactions[-n:]
    except Exception as e:
        return str(e)


def get_incoming_transactions(wallet: Wallet, alias: str):
    """
    Get all incoming transactions for the given account alias, after syncing.
    """
    try:
        account = wallet.get_account(alias)
        account.sync()
        return account.incoming_transactions()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return []


def parse_transaction_string(input_string: str):
    """
    Parse a text blob to extract transactionIds and amounts.
    Returns:
        (transaction_ids1, transaction_ids2, amounts)
    """
    transaction_id_pattern = r"'transactionId': '(0x[0-9a-fA-F]+)'|transactionId='(0x[0-9a-fA-F]+)'"
    amount_pattern = r"'amount': '(\d+)'"

    transaction_id_matches = re.findall(transaction_id_pattern, input_string)
    transaction_ids1, transaction_ids2, amounts = [], [], []

    for match1, match2 in transaction_id_matches:
        if match1:
            transaction_ids1.append(match1)
        elif match2:
            transaction_ids2.append(match2)

    amount_matches = re.findall(amount_pattern, input_string)
    for match in amount_matches:
        amounts.append(int(match))

    return transaction_ids1, transaction_ids2, amounts


def find_transaction_by_token(outputs, token_id: str) -> Optional[Dict[str, Any]]:
    """
    Search outputs for a given native token ID and return basic details of the first match.
    """
    for output_data in outputs:
        output = output_data.output
        if output.nativeTokens:
            for token in output.nativeTokens:
                if token.id == token_id:
                    return {
                        "outputId": output_data.outputId,
                        "transactionId": output_data.metadata.transactionId,
                        "amount": int(token.amount, 16),
                        "isSpent": output_data.isSpent,
                        "timestampBooked": output_data.metadata.milestoneTimestampBooked,
                        "address": output_data.address.pubKeyHash,
                    }
    print(f"No transaction found for token ID '{token_id}'.")
    return None


def find_latest_transaction_by_address(outputs, hex_address: str) -> Optional[Dict[str, Any]]:
    """
    Find the latest transaction (by booked timestamp) for a given address hex.
    """
    latest = None
    for output_data in outputs:
        if output_data.address.pubKeyHash == hex_address:
            output = output_data.output
            if output.nativeTokens:
                for token in output.nativeTokens:
                    details = {
                        "tokenId": token.id,
                        "amount": int(token.amount, 16),
                        "timestampBooked": output_data.metadata.milestoneTimestampBooked,
                    }
                    if latest is None or details["timestampBooked"] > latest["timestampBooked"]:
                        latest = details
    if latest:
        return latest
    print(f"No transaction found for address '{hex_address}'.")
    return None


def get_recent_sender_info(wallet: Wallet, alias: str, token_id: str):
    """
    Attempt to find the most recent incoming tx carrying `token_id` and infer sender info.

    Returns:
        (sender_address, amount, timestamp) or (None, 0.0, None)
    """
    try:
        account = wallet.get_account(alias)
        account.sync()
        transactions = account.incoming_transactions()

        for tx in reversed(transactions):
            for output in tx.payload["essence"]["outputs"]:
                if "nativeTokens" in output:
                    for token in output["nativeTokens"]:
                        if token["id"] == token_id:
                            input_tx_id = tx.payload["essence"]["inputs"][0]["transactionId"]
                            input_tx = account.get_transaction(input_tx_id)
                            sender_address = input_tx.payload["essence"]["outputs"][0]["unlockConditions"][0]["address"]["pubKeyHash"]
                            amount = float(int(token["amount"], 16))
                            timestamp = tx.timestamp
                            return sender_address, amount, timestamp

        print(f"No transaction found for token ID '{token_id}'.")
        return None, 0.0, None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None, 0.0, None


def check_outputs(wallet: Wallet, account_alias: str, is_unspent: bool = False) -> None:
    """
    Print output IDs for (unspent/all) outputs of an account.
    """
    try:
        account = wallet.get_account(account_alias)
        account.sync()
        outputs = account.unspent_outputs() if is_unspent else account.outputs()
        print("Output IDs:")
        for output in outputs:
            print(output.outputId)
    except Exception as e:
        print(f"An error occurred: {str(e)}")


# ------------------------- Address / Balance ------------------------- #
def get_account_addresses(wallet: Wallet, alias: str) -> List[str]:
    """
    Return all addresses for an account alias.
    """
    try:
        account = wallet.get_account(alias)
        return account.addresses()
    except Exception as e:
        print(f"Error: {str(e)}")
        return []


def get_my_address_Reference(wallet: Wallet, alias: str) -> str:
    """
    Return the first address string for the given account alias, or empty string.
    """
    try:
        account = wallet.get_account(alias)
        addrs = account.addresses()
        return addrs[0].address if addrs else ""
    except Exception as e:
        print(f"Error: {str(e)}")
        return ""


def get_my_address(NameYourAcount: str, NameYourPin: str, Password: str) -> Optional[str]:
    """
    Convenience wrapper: sign in, then return the first address for the alias.
    """
    WalletExists, accountExists = SignInToAccount(NameYourAcount, NameYourPin, Password)
    if WalletExists is not None and accountExists is not None:
        return get_my_address_Reference(WalletExists, NameYourPin)
    return None


def get_my_address_instanced(WalletExists: Wallet, NameYourAcount: str, NameYourPin: str, Password: str) -> Optional[str]:
    """
    Return the first address from an already-open wallet instance.
    """
    if WalletExists is not None:
        return get_my_address_Reference(WalletExists, NameYourPin)
    return None


def get_my_balance(wallet: Wallet, alias: str):
    """
    Sync account and return the balance object from the SDK.
    """
    try:
        account = wallet.get_account(alias)
        balance = account.sync(SyncOptions(sync_only_most_basic_outputs=True))
        return balance
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return 0


def parse_available_balance(balance_str: str) -> int:
    """
    Parse `available` from the string form of a balance object.

    Returns:
        Available base coin amount as int (micro-SMR) or 0.
    """
    try:
        match = re.search(r"available='(\d+)'", balance_str)
        return int(match.group(1)) if match else 0
    except Exception:
        return 0


def get_available_balances(balance, token_id: Optional[str] = None) -> float:
    """
    Return available balance for a native token by token_id, or base coin if None.
    """
    try:
        if token_id:
            for token in balance.nativeTokens:
                if token.tokenId == token_id:
                    return float(int(token.available, 16))
            print(f"Token ID '{token_id}' not found.")
            return 0.0
        return float(balance.baseCoin.available)
    except AttributeError as e:
        print(f"An attribute error occurred: {str(e)}")
        return 0.0
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return 0.0


# ------------------------- Utility ------------------------- #
def generate_request(symbol: str, request_type: str, price: float, counts: float) -> Tuple[str, int]:
    """
    Build a simple request payload and compute amount in micro-units for trading flows.
    Returns (metadata_json_string_without_newlines, amount_int).
    """
    count = int(counts * 1_000_000)
    request_dict = {"request": {"symbol": symbol, "requestType": request_type, "price": price, "count": count}}

    if request_type == "BUY_TOKEN":
        amount = int(price * count)
    elif request_type in ("SELL_TOKEN", "TRADE"):
        amount = int(count)
    else:
        raise ValueError("Invalid request type")

    metadata = json.dumps(request_dict, indent=2).replace("\n", "")
    return metadata, amount


def smr_address_to_hex(bech32_address: str) -> Optional[str]:
    """
    Convert a Bech32-encoded SMR address to the hex pubkey hash (without the 0x00 prefix).
    """
    try:
        hrp, data = bech32_decode(bech32_address)
        if hrp != "smr":
            raise ValueError("Invalid HRP for Shimmer address")
        decoded = convertbits(data, 5, 8, False)
        pubkey_hash = bytes(decoded[1:]).hex()
        return pubkey_hash
    except Exception as e:
        print(f"Error decoding address: {e}")
        return None


class CustomJSONEncoder(json.JSONEncoder):
    """Serialize SDK objects by falling back to __dict__ or str()."""
    def default(self, obj):
        try:
            return obj.__dict__
        except AttributeError:
            return str(obj)


def get_incoming_transactions_json(wallet: Wallet, alias: str) -> str:
    """
    Sync and return incoming transactions for an account as a JSON string.
    """
    try:
        account = wallet.get_account(alias)
        account.sync()
        txs = account.incoming_transactions()
        return json.dumps(txs, indent=4, cls=CustomJSONEncoder)
    except Exception as e:
        print(f"An error occurred: {e}")
        return "{}"


# ------------------------- Automated Responder ------------------------- #
def responder_transaction_with_self_sent_adjustment(
    wallet: Wallet,
    alias: str,
    expected_sender_address: str,
    max_amount_received: float,
    max_response_amount: float,
    divisor: int,
    received_token_id: Optional[str] = None,
    response_token_id: Optional[str] = None,
) -> None:
    """
    Watch for incoming increments and respond in `divisor` chunks,
    adjusting for self-sent tokens so net increases trigger responses.

    - Tracks starting balance (for a given token or base coin).
    - On each observed net increase, sends the next response amount.
    - Stops when `max_amount_received` or all response chunks are sent.
    """
    starting_balance = get_available_balances(get_my_balance(wallet, alias), token_id=received_token_id)
    print(f"Starting balance for token '{received_token_id}': {starting_balance}")

    total_received = 0.0
    total_responded = 0.0
    per_response = round(max_response_amount / divisor, 8)
    response_amounts = [per_response] * divisor

    # Fix rounding residue in the last chunk
    diff = max_response_amount - sum(response_amounts)
    if abs(diff) > 0:
        response_amounts[-1] += diff

    print("Responder starting...")
    print(f"Max received: {max_amount_received}, Max response: {max_response_amount}, Chunks: {response_amounts}")

    idx = 0
    while total_received < max_amount_received:
        time.sleep(5)

        current_balance = get_available_balances(get_my_balance(wallet, alias), token_id=received_token_id)
        net_increment = current_balance - (starting_balance + total_received - total_responded)

        if net_increment > 0 or total_responded == 0:
            total_received += net_increment
            print(f"Net received from {expected_sender_address}: {net_increment}")

            if idx < len(response_amounts):
                send_amt = response_amounts[idx]
                try:
                    tx = send_transaction_any(
                        wallet=wallet,
                        NameYourPin1=alias,
                        recipient_address_str=expected_sender_address,
                        custom_amount=int(send_amt * 1_000_000),
                        token_id=response_token_id,
                        custom_metadata_str="Responder transaction",
                    )
                    print(f"Response transaction sent: {tx}")
                    total_responded += send_amt
                    idx += 1
                except Exception as e:
                    print(f"Error sending response transaction: {e}")
                    continue
            else:
                print("All response transactions have been sent.")
                break

        if total_received >= max_amount_received:
            print("Maximum received amount reached. Exiting responder process.")
            break

    print(f"Responder completed. Total received: {total_received}, Total responded: {total_responded}")


# ------------------------- Stronghold Discovery Helpers ------------------------- #
def find_stronghold_folders(folder_path: str) -> List[str]:
    """
    Return subfolder names under ~/Documents/Stronghold/<folder_path>
    that contain a 'vault.stronghold' file.
    """
    base = Path.home() / "Documents" / "Stronghold"
    combined = base / folder_path
    names: List[str] = []

    if combined.exists() and combined.is_dir():
        for sub in combined.iterdir():
            if sub.is_dir() and (sub / "vault.stronghold").is_file():
                names.append(sub.name)
    return names


def get_folder_name_by_index(folder_names: List[str], index: int) -> Optional[str]:
    """Bounds-checked access to a folder name by index."""
    return folder_names[index] if 0 <= index < len(folder_names) else None


def create_character_folder(character_name: Optional[str]) -> Optional[str]:
    """
    Build a nested folder path from the last 7 characters (illustrative helper).
    Returns a path-like string or None if input is None.
    """
    if character_name is None:
        return None
    s = character_name.lower()
    tail = s[-8::-1][::-1]
    parts = list(s[-7:])
    return "/".join(parts) + "/" + tail
