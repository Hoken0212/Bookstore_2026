import os
import json
import hmac
import hashlib
import uuid
import time
import qrcode
import base64
import requests
from io import BytesIO
from datetime import datetime


def generate_momo_qr(order_id: str, amount: int, order_info: str) -> dict:
    """Generate MoMo QR payment"""
    partner_code = os.getenv('MOMO_PARTNER_CODE', 'MOMO_TEST')
    access_key = os.getenv('MOMO_ACCESS_KEY', 'test_access_key')
    secret_key = os.getenv('MOMO_SECRET_KEY', 'test_secret_key')
    endpoint = os.getenv('MOMO_ENDPOINT', 'https://test-payment.momo.vn/v2/gateway/api/create')
    base_url = os.getenv('BASE_URL', 'http://localhost:5000')

    request_id = f"{partner_code}_{uuid.uuid4().hex}"
    redirect_url = f"{base_url}/payment/momo/callback"
    ipn_url = f"{base_url}/payment/momo/ipn"
    request_type = "captureWallet"
    extra_data = base64.b64encode(json.dumps({'order_id': order_id}).encode()).decode()

    raw_signature = (
        f"accessKey={access_key}&amount={amount}&extraData={extra_data}"
        f"&ipnUrl={ipn_url}&orderId={order_id}&orderInfo={order_info}"
        f"&partnerCode={partner_code}&redirectUrl={redirect_url}"
        f"&requestId={request_id}&requestType={request_type}"
    )
    signature = hmac.new(secret_key.encode(), raw_signature.encode(), hashlib.sha256).hexdigest()

    payload = {
        "partnerCode": partner_code,
        "accessKey": access_key,
        "requestId": request_id,
        "amount": amount,
        "orderId": order_id,
        "orderInfo": order_info,
        "redirectUrl": redirect_url,
        "ipnUrl": ipn_url,
        "extraData": extra_data,
        "requestType": request_type,
        "signature": signature,
        "lang": "vi"
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        data = response.json()
        if data.get('resultCode') == 0:
            qr_url = data.get('qrCodeUrl', '')
            return {'success': True, 'qr_url': qr_url, 'pay_url': data.get('payUrl', ''), 'data': data}
    except Exception as e:
        pass

    # Fallback: generate demo QR with payment info
    return _generate_demo_qr('momo', order_id, amount)


def generate_zalopay_qr(order_id: str, amount: int, description: str) -> dict:
    """Generate ZaloPay QR payment"""
    app_id = os.getenv('ZALOPAY_APP_ID', '2554')
    key1 = os.getenv('ZALOPAY_KEY1', 'sdngKKJmqEMzvh5QQcdD2A9XBSKUNaYn')
    endpoint = os.getenv('ZALOPAY_ENDPOINT', 'https://sb.zalopay.vn/v001/tpe/createorder')
    base_url = os.getenv('BASE_URL', 'http://localhost:5000')

    trans_id = f"{datetime.now().strftime('%y%m%d')}_{int(time.time())}_{order_id[-8:]}"
    app_trans_id = trans_id
    app_time = int(time.time() * 1000)
    embed_data = json.dumps({"redirecturl": f"{base_url}/payment/zalopay/callback"})
    items = json.dumps([{"itemid": order_id, "itename": description, "itemprice": amount, "itemquantity": 1}])

    data = f"{app_id}|{app_trans_id}|user|{amount}|{app_time}|{embed_data}|{items}"
    mac = hmac.new(key1.encode(), data.encode(), hashlib.sha256).hexdigest()

    payload = {
        "app_id": int(app_id),
        "app_trans_id": app_trans_id,
        "app_user": "user",
        "app_time": app_time,
        "amount": amount,
        "item": items,
        "description": description,
        "embed_data": embed_data,
        "mac": mac
    }

    try:
        response = requests.post(endpoint, data=payload, timeout=10)
        result = response.json()
        if result.get('return_code') == 1:
            return {'success': True, 'order_url': result.get('order_url', ''), 'zp_trans_token': result.get('zp_trans_token', '')}
    except Exception:
        pass

    return _generate_demo_qr('zalopay', order_id, amount)


def _generate_demo_qr(provider: str, order_id: str, amount: int) -> dict:
    """Generate a demo QR code for development/testing"""
    if provider == 'momo':
        qr_data = f"2|99|0369100000|BookHaven|{order_id}|{amount}|0|Thanh toan don hang {order_id}"
        color = '#ae2070'
    else:
        qr_data = f"zalopay://app.zalopay.vn?action=payment&order={order_id}&amount={amount}"
        color = '#0068FF'

    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=color, back_color='white')

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_b64 = base64.b64encode(buffer.getvalue()).decode()

    return {
        'success': True,
        'qr_image_b64': f"data:image/png;base64,{img_b64}",
        'demo': True,
        'amount': amount,
        'order_id': order_id
    }


def verify_momo_signature(data: dict) -> bool:
    secret_key = os.getenv('MOMO_SECRET_KEY', '')
    access_key = os.getenv('MOMO_ACCESS_KEY', '')
    raw = (
        f"accessKey={access_key}&amount={data.get('amount')}&extraData={data.get('extraData')}"
        f"&message={data.get('message')}&orderId={data.get('orderId')}&orderInfo={data.get('orderInfo')}"
        f"&orderType={data.get('orderType')}&partnerCode={data.get('partnerCode')}"
        f"&payType={data.get('payType')}&requestId={data.get('requestId')}"
        f"&responseTime={data.get('responseTime')}&resultCode={data.get('resultCode')}"
        f"&transId={data.get('transId')}"
    )
    expected = hmac.new(secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return expected == data.get('signature', '')
