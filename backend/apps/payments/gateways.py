"""Request building and response checking for JazzCash and Easypaisa.

Both follow the gateways' hosted-checkout ("page redirection") integration:
the customer's browser POSTs a signed form to the gateway, pays there, and is
sent back to our return URL.
"""

import base64
import datetime
import hashlib
import hmac
from decimal import Decimal

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

JAZZCASH_URLS = {
    True: "https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform/",
    False: "https://payments.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform/",
}
EASYPAISA_URLS = {
    True: {
        "index": "https://easypaystg.easypaisa.com.pk/easypay/Index.jsf",
        "confirm": "https://easypaystg.easypaisa.com.pk/easypay/Confirm.jsf",
    },
    False: {
        "index": "https://easypay.easypaisa.com.pk/easypay/Index.jsf",
        "confirm": "https://easypay.easypaisa.com.pk/easypay/Confirm.jsf",
    },
}
JAZZCASH_SUCCESS = "000"


# --- JazzCash ---------------------------------------------------------------------

def jazzcash_hash(fields, integrity_salt):
    """pp_SecureHash: HMAC-SHA256 (key = integrity salt) over the salt and every non-empty
    pp_* value, in alphabetical order of the field names, joined with '&'. Upper-case hex."""
    values = [
        str(fields[key])
        for key in sorted(fields)
        if (key.startswith("pp_") or key.startswith("ppmpf_")) and key != "pp_SecureHash" and str(fields[key]) != ""
    ]
    message = "&".join([integrity_salt, *values])
    return hmac.new(integrity_salt.encode(), message.encode(), hashlib.sha256).hexdigest().upper()


def jazzcash_request(account, reference, amount, description, bill_reference, return_url, now):
    fields = {
        "pp_Version": "1.1",
        "pp_TxnType": "",
        "pp_Language": "EN",
        "pp_MerchantID": account.merchant_id,
        "pp_SubMerchantID": "",
        "pp_Password": account.password,
        "pp_BankID": "",
        "pp_ProductID": "",
        "pp_TxnRefNo": reference,
        "pp_Amount": str(int((Decimal(amount) * 100).quantize(Decimal(1)))),  # in paisa
        "pp_TxnCurrency": "PKR",
        "pp_TxnDateTime": now.strftime("%Y%m%d%H%M%S"),
        "pp_BillReference": bill_reference,
        "pp_Description": description[:100],
        "pp_TxnExpiryDateTime": (now + datetime.timedelta(days=1)).strftime("%Y%m%d%H%M%S"),
        "pp_ReturnURL": return_url,
        "ppmpf_1": "",
        "ppmpf_2": "",
        "ppmpf_3": "",
        "ppmpf_4": "",
        "ppmpf_5": "",
    }
    fields["pp_SecureHash"] = jazzcash_hash(fields, account.secret)
    return {"method": "POST", "action": JAZZCASH_URLS[account.test_mode], "fields": fields}


def jazzcash_check(data, account, expected_amount):
    """(ok, message) for the response JazzCash posts back to the return URL."""
    received = str(data.get("pp_SecureHash", ""))
    if not received or not hmac.compare_digest(received.upper(), jazzcash_hash(data, account.secret)):
        return False, "The response signature did not match."
    if data.get("pp_MerchantID") and data.get("pp_MerchantID") != account.merchant_id:
        return False, "The response is for a different merchant."
    paisa = str(int((Decimal(expected_amount) * 100).quantize(Decimal(1))))
    if str(data.get("pp_Amount", "")) != paisa:
        return False, "The paid amount does not match."
    if data.get("pp_ResponseCode") != JAZZCASH_SUCCESS:
        return False, str(data.get("pp_ResponseMessage") or "Payment was not completed.")
    return True, str(data.get("pp_ResponseMessage") or "Paid")


# --- Easypaisa --------------------------------------------------------------------

def easypaisa_encrypt(plain, hash_key):
    """merchantHashedReq: AES-128-ECB with PKCS#5 padding (key = hash key), base64."""
    key = hash_key.encode()
    padder = padding.PKCS7(128).padder()
    data = padder.update(plain.encode()) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()  # noqa: S305 - required by Easypaisa
    return base64.b64encode(encryptor.update(data) + encryptor.finalize()).decode()


def easypaisa_decrypt(token, hash_key):
    decryptor = Cipher(algorithms.AES(hash_key.encode()), modes.ECB()).decryptor()  # noqa: S305
    data = decryptor.update(base64.b64decode(token)) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(data) + unpadder.finalize()).decode()


def easypaisa_request(account, reference, amount, postback_url, now, email="", mobile=""):
    fields = {
        "storeId": account.merchant_id,
        "amount": f"{Decimal(amount):.1f}",
        "postBackURL": postback_url,
        "orderRefNum": reference,
        "expiryDate": (now + datetime.timedelta(days=1)).strftime("%Y%m%d %H%M%S"),
        "autoRedirect": "1",
        "emailAddr": email,
        "mobileNum": mobile,
    }
    plain = "&".join(f"{key}={fields[key]}" for key in sorted(fields) if fields[key] != "")
    fields["merchantHashedReq"] = easypaisa_encrypt(plain, account.secret)
    return {"method": "POST", "action": EASYPAISA_URLS[account.test_mode]["index"], "fields": fields}


def easypaisa_confirm_form(account, auth_token, postback_url):
    return {
        "method": "POST",
        "action": EASYPAISA_URLS[account.test_mode]["confirm"],
        "fields": {"auth_token": auth_token, "postBackURL": postback_url},
    }


def easypaisa_ipn_check(ipn, account, reference, expected_amount):
    """(ok, message) for the transaction details fetched from Easypaisa's IPN URL."""
    if str(ipn.get("order_id")) != reference:
        return False, "IPN is for a different order."
    if account.merchant_id and str(ipn.get("store_id", account.merchant_id)) != account.merchant_id:
        return False, "IPN is for a different store."
    try:
        paid = Decimal(str(ipn.get("transaction_amount")))
    except Exception:
        return False, "IPN amount is missing."
    if paid != Decimal(expected_amount):
        return False, "The paid amount does not match."
    if str(ipn.get("transaction_status", "")).upper() != "PAID":
        return False, f"Status: {ipn.get('transaction_status')}"
    return True, "Paid"


# --- Stripe (cards, any currency) -----------------------------------------------------
# Hosted Checkout: we create a Checkout Session with the institute's secret key and send the browser to
# its URL. A payment counts only after we read the session back from Stripe (on return) or receive a
# webhook whose signature checks out with the institute's webhook signing secret.

ZERO_DECIMAL = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF"}
STRIPE_TOLERANCE = 300  # seconds a webhook signature stays valid


def stripe_base():
    from django.conf import settings

    return getattr(settings, "STRIPE_API_BASE", "https://api.stripe.com").rstrip("/")


def minor_units(amount, currency):
    factor = 1 if currency.upper() in ZERO_DECIMAL else 100
    return int((Decimal(amount) * factor).quantize(Decimal(1)))


def stripe_call(secret_key, path, data=None):
    import json
    import urllib.parse
    import urllib.request

    request = urllib.request.Request(
        f"{stripe_base()}{path}",
        data=urllib.parse.urlencode(data).encode() if data is not None else None,
        method="POST" if data is not None else "GET",
        headers={"Authorization": "Basic " + base64.b64encode(f"{secret_key}:".encode()).decode(),
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - fixed Stripe host
        return json.loads(response.read().decode())


def stripe_create_session(account, reference, amount, currency, description, return_url, cancel_url):
    return stripe_call(account.secret, "/v1/checkout/sessions", {
        "mode": "payment",
        "client_reference_id": reference,
        "metadata[reference]": reference,
        "line_items[0][quantity]": 1,
        "line_items[0][price_data][currency]": currency.lower(),
        "line_items[0][price_data][unit_amount]": minor_units(amount, currency),
        "line_items[0][price_data][product_data][name]": description[:120],
        "success_url": return_url,
        "cancel_url": cancel_url,
    })


def stripe_session_check(session, reference, expected_amount, currency):
    """(ok, message) for a Checkout Session read from Stripe or sent in a verified webhook."""
    if session.get("client_reference_id") != reference:
        return False, "Session is for a different payment."
    if str(session.get("currency", "")).upper() != currency.upper():
        return False, "The currency does not match."
    if session.get("amount_total") != minor_units(expected_amount, currency):
        return False, "The paid amount does not match."
    if session.get("payment_status") != "paid":
        return False, f"Status: {session.get('payment_status')}"
    return True, "Paid by card"


def stripe_verify_signature(payload, header, secret, now=None):
    """Check a ``Stripe-Signature`` header (t=..., v1=...) against the raw request body."""
    import time

    parts = {}
    for item in (header or "").split(","):
        key, _, value = item.strip().partition("=")
        parts.setdefault(key, []).append(value)
    try:
        timestamp = int(parts.get("t", [""])[0])
    except ValueError:
        return False
    if abs((now or time.time()) - timestamp) > STRIPE_TOLERANCE:
        return False
    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", []))


# --- Safepay (Pakistan: cards, wallets, bank accounts) --------------------------------
# Hosted checkout: create a tracker with the API key, send the browser to the checkout page; Safepay
# sends the browser back with the tracker and ``sig`` = HMAC-SHA256(secret key, tracker), which we check.

SAFEPAY_URLS = {True: "https://sandbox.api.getsafepay.com", False: "https://api.getsafepay.com"}


def safepay_base(test_mode):
    from django.conf import settings

    return (getattr(settings, "SAFEPAY_API_BASE", "") or SAFEPAY_URLS[test_mode]).rstrip("/")


def safepay_create_tracker(account, amount):
    import json
    import urllib.request

    body = json.dumps({"client": account.merchant_id, "amount": float(Decimal(amount)), "currency": "PKR",
                       "environment": "sandbox" if account.test_mode else "production"}).encode()
    request = urllib.request.Request(f"{safepay_base(account.test_mode)}/order/v1/init", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - fixed Safepay host
        return json.loads(response.read().decode())["data"]["token"]


def safepay_checkout_url(account, tracker, reference, return_url, cancel_url):
    from urllib.parse import urlencode

    query = urlencode({"env": "sandbox" if account.test_mode else "production", "beacon": tracker, "source": "custom",
                       "order_id": reference, "redirect_url": return_url, "cancel_url": cancel_url})
    return f"{safepay_base(account.test_mode)}/components?{query}"


def safepay_signature_ok(account, tracker, signature):
    expected = hmac.new(account.secret.encode(), tracker.encode(), hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)
