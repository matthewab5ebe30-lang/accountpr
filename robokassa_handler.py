import hashlib
import logging
import random
import time
from urllib.parse import urlencode

from config import (
    ROBOKASSA_API_BASE,
    ROBOKASSA_FAIL_URL,
    ROBOKASSA_IS_TEST,
    ROBOKASSA_MERCHANT_LOGIN,
    ROBOKASSA_PASSWORD_1,
    ROBOKASSA_PASSWORD_2,
    ROBOKASSA_SUCCESS_URL,
    ROBOKASSA_TEST_PASSWORD_1,
    ROBOKASSA_TEST_PASSWORD_2,
)

logger = logging.getLogger(__name__)


class RobokassaHandler:
    @staticmethod
    def _md5(value: str) -> str:
        return hashlib.md5(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_out_sum(amount: float) -> str:
        return f"{float(amount):.2f}"

    @staticmethod
    def _build_invoice_id(user_id: int) -> str:
        # Unique enough for practical bot load and keeps InvId numeric.
        return str(int(time.time() * 1000) + random.randint(100, 999) + user_id % 100)

    def make_signature_for_payment(self, out_sum: str, inv_id: str, password_1: str) -> str:
        raw = f"{ROBOKASSA_MERCHANT_LOGIN}:{out_sum}:{inv_id}:{password_1}"
        return self._md5(raw)

    def make_signature_for_result(self, out_sum: str, inv_id: str, password_2: str) -> str:
        raw = f"{out_sum}:{inv_id}:{password_2}"
        return self._md5(raw)

    def verify_result_signature(self, out_sum: str, inv_id: str, signature: str) -> bool:
        passwords = [ROBOKASSA_PASSWORD_2]
        if ROBOKASSA_TEST_PASSWORD_2:
            passwords.append(ROBOKASSA_TEST_PASSWORD_2)

        signature_value = (signature or "").lower()
        for password_2 in passwords:
            expected = self.make_signature_for_result(out_sum, inv_id, password_2)
            if expected.lower() == signature_value:
                return True
        return False

    def create_payment(self, user_id: int, amount: float, description: str, is_test: bool | None = None) -> dict:
        test_mode = ROBOKASSA_IS_TEST if is_test is None else is_test
        password_1 = ROBOKASSA_TEST_PASSWORD_1 if test_mode else ROBOKASSA_PASSWORD_1

        if not ROBOKASSA_MERCHANT_LOGIN or not password_1:
            raise RuntimeError("Robokassa credentials are not configured")

        inv_id = self._build_invoice_id(user_id)
        out_sum = self._normalize_out_sum(amount)
        signature = self.make_signature_for_payment(out_sum, inv_id, password_1)

        params = {
            "MerchantLogin": ROBOKASSA_MERCHANT_LOGIN,
            "OutSum": out_sum,
            "InvId": inv_id,
            "Description": description,
            "SignatureValue": signature,
            "SuccessURL": ROBOKASSA_SUCCESS_URL,
            "FailURL": ROBOKASSA_FAIL_URL,
            "IsTest": 1 if test_mode else 0,
        }

        payment_url = f"{ROBOKASSA_API_BASE}?{urlencode(params)}"
        logger.info(
            "Robokassa payment created inv_id=%s user_id=%s out_sum=%s test_mode=%s",
            inv_id,
            user_id,
            out_sum,
            test_mode,
        )

        return {
            "payment_id": inv_id,
            "out_sum": out_sum,
            "payment_url": payment_url,
            "is_test": test_mode,
        }


robokassa = RobokassaHandler()
