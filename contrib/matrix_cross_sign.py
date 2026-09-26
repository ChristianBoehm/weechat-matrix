#!/usr/bin/env python3
# matrix_cross_sign - Sign our own device with the cross-signing
# self-signing key, which is read from the server side secret storage (SSSS)
# and unlocked with the user's recovery key.

# Copyright © 2026 Christian Boehm <c.boehm@computertechnik-boehm.com>
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted, provided that the
# above copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
# SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# The secrets (access token, recovery key) are read as JSON from stdin so that
# they never show up in the process list. The result is printed as a single
# JSON object on stdout.

import base64
import hmac
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from hashlib import sha256

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import (Encoding,
                                                          PublicFormat)

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
RECOVERY_KEY_PREFIX = b"\x8b\x01"
SSSS_ALGORITHM = "m.secret_storage.v1.aes-hmac-sha2"
SELF_SIGNING_SECRET = "m.cross_signing.self_signing"


class CrossSignError(Exception):
    pass


def b64decode(data):
    return base64.b64decode(data + "=" * (-len(data) % 4))


def b64encode(data):
    return base64.b64encode(data).decode().rstrip("=")


def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True).encode("utf-8")


def decode_recovery_key(recovery_key):
    number = 0
    for char in recovery_key.replace(" ", ""):
        try:
            number = number * 58 + BASE58_ALPHABET.index(char)
        except ValueError:
            raise CrossSignError("The recovery key contains invalid characters")

    decoded = number.to_bytes((number.bit_length() + 7) // 8, "big")

    parity = 0
    for byte in decoded:
        parity ^= byte

    if (len(decoded) != 35 or parity != 0
            or not decoded.startswith(RECOVERY_KEY_PREFIX)):
        raise CrossSignError("This is not a valid recovery key")

    return decoded[2:34]


def derive_keys(key, secret_name):
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=64,
        salt=b"\x00" * 32,
        info=secret_name.encode(),
    ).derive(key)
    return derived[:32], derived[32:]


def aes_ctr(key, iv, data):
    cipher = Cipher(algorithms.AES(key), modes.CTR(iv)).decryptor()
    return cipher.update(data) + cipher.finalize()


def check_mac(hmac_key, ciphertext, mac):
    expected = hmac.new(hmac_key, ciphertext, sha256).digest()
    return hmac.compare_digest(expected, b64decode(mac))


def check_secret_storage_key(key, key_info):
    # The key description carries the encryption of 32 zero bytes, used to
    # tell if the user gave us the right key.
    aes_key, hmac_key = derive_keys(key, "")
    ciphertext = aes_ctr(aes_key, b64decode(key_info["iv"]), b"\x00" * 32)

    if not check_mac(hmac_key, ciphertext, key_info["mac"]):
        raise CrossSignError("The recovery key doesn't match the secret "
                             "storage key of this account")


def decrypt_secret(key, secret_name, encrypted):
    aes_key, hmac_key = derive_keys(key, secret_name)
    ciphertext = b64decode(encrypted["ciphertext"])

    if not check_mac(hmac_key, ciphertext, encrypted["mac"]):
        raise CrossSignError("Bad MAC while decrypting {}".format(secret_name))

    return aes_ctr(aes_key, b64decode(encrypted["iv"]), ciphertext).decode()


class Api(object):
    def __init__(self, homeserver, access_token):
        self.homeserver = homeserver.rstrip("/")
        self.access_token = access_token

    def request(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(
            self.homeserver + "/_matrix/client/v3" + path,
            data=data,
            method=method,
            headers={
                "Authorization": "Bearer " + self.access_token,
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            try:
                error = json.loads(e.read()).get("error", e.reason)
            except ValueError:
                error = e.reason
            raise CrossSignError("{} {} failed: {} {}".format(
                method, path.split("?")[0], e.code, error))

    def account_data(self, user_id, event_type):
        return self.request("GET", "/user/{}/account_data/{}".format(
            urllib.parse.quote(user_id), urllib.parse.quote(event_type)))


def cross_sign(args):
    user_id = args["user_id"]
    device_id = args["device_id"]
    api = Api(args["homeserver"], args["access_token"])

    key = decode_recovery_key(args["recovery_key"])

    key_id = api.account_data(user_id, "m.secret_storage.default_key")["key"]
    key_info = api.account_data(user_id,
                                "m.secret_storage.key.{}".format(key_id))

    if key_info.get("algorithm") != SSSS_ALGORITHM:
        raise CrossSignError("Unsupported secret storage algorithm {}".format(
            key_info.get("algorithm")))

    check_secret_storage_key(key, key_info)

    secret = api.account_data(user_id, SELF_SIGNING_SECRET)
    encrypted = secret.get("encrypted", {}).get(key_id)

    if not encrypted:
        raise CrossSignError("The self-signing key isn't stored with the "
                             "default secret storage key")

    seed = b64decode(decrypt_secret(key, SELF_SIGNING_SECRET, encrypted))
    signing_key = Ed25519PrivateKey.from_private_bytes(seed)
    public_key = b64encode(signing_key.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw))

    keys = api.request("POST", "/keys/query",
                       {"device_keys": {user_id: [device_id]}})

    self_signing_keys = keys.get("self_signing_keys", {}).get(user_id, {})
    if public_key not in self_signing_keys.get("keys", {}).values():
        raise CrossSignError("The stored self-signing key doesn't match the "
                             "published one")

    device_keys = keys.get("device_keys", {}).get(user_id, {}).get(device_id)
    if not device_keys:
        raise CrossSignError("The server doesn't know our device keys")

    # Only sign the device keys if they are the ones we hold locally,
    # otherwise we would vouch for keys the server made up.
    server_fingerprint = device_keys["keys"].get("ed25519:" + device_id)
    if server_fingerprint != args["fingerprint"]:
        raise CrossSignError("The device keys on the server don't match our "
                             "local device keys")

    device_keys.pop("unsigned", None)
    signatures = device_keys.pop("signatures", {})
    signature = b64encode(signing_key.sign(canonical_json(device_keys)))

    signatures.setdefault(user_id, {})["ed25519:" + public_key] = signature
    device_keys["signatures"] = signatures

    response = api.request("POST", "/keys/signatures/upload",
                           {user_id: {device_id: device_keys}})

    if response.get("failures"):
        raise CrossSignError("The server rejected the signature: {}".format(
            json.dumps(response["failures"])))

    return public_key


def main():
    try:
        public_key = cross_sign(json.loads(sys.stdin.read()))
        result = {"type": "ok", "self_signing_key": public_key}
    except CrossSignError as e:
        result = {"type": "error", "message": str(e)}
    except (KeyError, ValueError, OSError) as e:
        result = {"type": "error",
                  "message": "{}: {}".format(type(e).__name__, e)}

    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
