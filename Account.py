import random
import string
import datetime
import requests
from web3.auto import w3 as web3
from fake_useragent import UserAgent
from eth_account.messages import encode_defunct
from tenacity import retry, stop_after_attempt, wait_fixed

from config import retries, retries_delay


class Account:
    name = None
    abstract_wallet = None
    mail = None
    authorization = None
    session = None

    def __init__(
            self, private: str,
            proxy: dict | None = None
    ):
        self.private = private
        self.proxy = proxy
        self.wallet_address = web3.eth.account.from_key(self.private).address
        self.session: requests.Session = self.init_session()
        self.web3_auth_jwt = self.get_web3_auth_jwt()
        self.me = self.login()

    def init_session(self):
        session = requests.session()
        ua = UserAgent().chrome
        version = ua.split('Chrome/')[1].split('.')[0]
        headers = {
            'authority': 'api.moca-id.mocaverse.xyz',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'content-type': 'application/json',
            'origin': 'https://www.mocaverse.xyz',
            'pragma': 'no-cache',
            'referer': 'https://www.mocaverse.xyz/',
            'sec-ch-ua': f'"Chromium";v="{version}", "Not(A:Brand";v="24", "Google Chrome";v="{version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': ua,
        }
        session.headers.update(headers)
        session.proxies = {'http': self.proxy, 'https': self.proxy} if self.proxy != {} else self.proxy
        return session

    def sign_message(self, message: str, type_='text') -> hex:
        message_hash = encode_defunct(text=message)
        if type_ == 'hexstr':
            message_hash = encode_defunct(hexstr=message)
        signed_message = web3.eth.account.sign_message(message_hash, self.private)

        signature = signed_message.signature.hex()
        return signature

    @retry(stop=stop_after_attempt(retries), wait=wait_fixed(retries_delay), reraise=True)
    def get_web3_auth_jwt(self):
        chars = string.ascii_lowercase + string.digits
        nonce = ''.join(random.choice(chars) for _ in range(10))
        date = datetime.datetime.now().strftime('%Y-%m-%dT%TZ')

        json_data = {
            'payload': {
                'domain': 'https://account.mocaverse.xyz',
                'uri': 'https://account.mocaverse.xyz/frame#origin=https%3A%2F%2Fwww.mocaverse.xyz',
                'address': self.wallet_address,
                'chainId': 137,
                'version': '1',
                'nonce': nonce,
                'issuedAt': date,
            },
            'header': {
                't': 'eip191',
            },
            'network': 'ethereum',
        }

        message = self.session.post('https://authjs.web3auth.io/siww/get', json=json_data).json()['challenge']
        signature = self.sign_message(message)

        json_data = {
            'signature': {
                's': signature,
                't': 'eip191',
            },
            'message': message,
            'issuer': 'metamask',
            'audience': 'account.mocaverse.xyz',
            'timeout': 86400,
        }

        token = self.session.post('https://authjs.web3auth.io/siww/verify', json=json_data).json()['token']

        json_data = {
            'account_type': 'external',
            'public_address': self.wallet_address,
            'id_token': token,
            'network': 'sapphire_mainnet',
        }

        token = self.session.post('https://api.moca-account.mocaverse.xyz/auth/verify', json=json_data).json()['token']

        return f'{token}'

    @retry(stop=stop_after_attempt(retries), wait=wait_fixed(retries_delay), reraise=True)
    def login(self):
        json_data = {
            'web3AuthJwt': self.web3_auth_jwt,
        }

        response = self.session.post('https://api.moca-id.mocaverse.xyz/auth/login', json=json_data).json()

        self.name = response['realmId']
        self.abstract_wallet = response['abstractAccountAddress']
        self.mail = response['emailNotification']
        self.authorization = response['accessToken']

        self.session.headers.update({'authorization': f'Bearer {self.authorization}'})

        return response