import hashlib
import hmac
import urllib.parse
import uuid
from datetime import datetime
import requests
from django.conf import settings


class VNPayService:
    def __init__(self):
        self.vnp_tmncode = getattr(settings, 'VNPAY_TMN_CODE', '2SS3YMXK')
        self.vnp_hashsecret = getattr(settings, 'VNPAY_HASH_SECRET', '4UQXNY0AEK9S4Y1FFKCC0O29ZZ83D4CE')
        self.vnp_url = getattr(settings, 'VNPAY_URL', 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html')
        # Return URL phải trỏ về backend để xử lý, sau đó redirect về frontend
        self.vnp_returnurl = getattr(settings, 'VNPAY_RETURN_URL', 'http://127.0.0.1:8000/vnpay/return/')
        self.vnp_ipnurl = getattr(settings, 'VNPAY_IPN_URL', 'http://127.0.0.1:8000/vnpay/ipn/')

    def create_payment_url(self, order_id, amount, order_desc, client_ip='127.0.0.1'):
        vnp_params = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'pay',
            'vnp_TmnCode': self.vnp_tmncode,
            'vnp_Amount': int(amount * 100), 
            'vnp_CurrCode': 'VND',
            'vnp_TxnRef': str(order_id),
            'vnp_OrderInfo': order_desc,
            'vnp_OrderType': 'other',
            'vnp_Locale': 'vn',
            'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
            'vnp_IpAddr': client_ip,
            'vnp_ReturnUrl': self.vnp_returnurl,
        }

        # Sắp xếp params theo thứ tự alphabet
        sorted_params = sorted(vnp_params.items())
        
        # Tạo query string với URL encoding đúng cách
        query_string = '&'.join([f'{key}={urllib.parse.quote_plus(str(value))}' for key, value in sorted_params])
        
        # Tạo secure hash
        secure_hash = self._create_secure_hash(query_string)
        
        # Thêm secure hash vào params
        vnp_params['vnp_SecureHash'] = secure_hash
        
        # Tạo URL cuối cùng
        payment_url = f"{self.vnp_url}?{urllib.parse.urlencode(vnp_params)}"
        
        return payment_url

    def verify_payment_response(self, vnp_params):
        """
        Xác thực phản hồi từ VNPay
        """
        # Lấy secure hash từ response
        vnp_secure_hash = vnp_params.pop('vnp_SecureHash', None)
        
        if not vnp_secure_hash:
            return False, "Missing secure hash"
        
        # Sắp xếp params để tạo query string
        sorted_params = sorted(vnp_params.items())
        query_string = '&'.join([f'{key}={urllib.parse.quote_plus(str(value))}' for key, value in sorted_params])
        
        # Tạo secure hash để so sánh
        calculated_hash = self._create_secure_hash(query_string)
        
        # So sánh hash
        if vnp_secure_hash != calculated_hash:
            return False, "Invalid secure hash"
        
        # Kiểm tra response code
        response_code = vnp_params.get('vnp_ResponseCode')
        if response_code == '00':
            return True, "Payment successful"
        else:
            return False, f"Payment failed with code: {response_code}"

    def _create_secure_hash(self, query_string):
        """
        Tạo secure hash theo chuẩn VNPay
        """
        return hmac.new(
            self.vnp_hashsecret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

    def get_payment_status(self, txn_ref):
        """
        Truy vấn trạng thái giao dịch
        """
        vnp_params = {
            'vnp_Version': '2.1.0',
            'vnp_Command': 'querydr',
            'vnp_TmnCode': self.vnp_tmncode,
            'vnp_TxnRef': txn_ref,
            'vnp_OrderInfo': f'Truy van giao dich {txn_ref}',
            'vnp_TransactionNo': '',
            'vnp_TransDate': datetime.now().strftime('%Y%m%d%H%M%S'),
            'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
            'vnp_IpAddr': '127.0.0.1',
        }

        # Sắp xếp và tạo secure hash
        sorted_params = sorted(vnp_params.items())
        query_string = '&'.join([f'{key}={value}' for key, value in sorted_params])
        secure_hash = self._create_secure_hash(query_string)
        vnp_params['vnp_SecureHash'] = secure_hash

        # Gửi request truy vấn
        query_url = "https://sandbox.vnpayment.vn/merchant_webapi/api/transaction"
        
        try:
            response = requests.post(query_url, data=vnp_params, timeout=30)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error querying VNPay: {e}")
            return None
