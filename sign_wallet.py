import asyncio
import random
import time
import os
import pytz
import secrets
from datetime import datetime
from aiohttp import ClientSession, ClientTimeout, ClientResponseError
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_hex
from eth_abi.abi import encode
from web3 import Web3
from colorama import init, Fore, Style


init(autoreset=True)


beijing = pytz.timezone('Asia/Shanghai')

class PharosBot:
    def __init__(self):
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": "https://testnet.pharosnetwork.xyz",
            "Referer": "https://testnet.pharosnetwork.xyz/",
            "User-Agent": FakeUserAgent().random
        }
        self.API_BASE = "https://api.pharosnetwork.xyz"
        self.RPC_URL = "https://testnet.dplabs-internal.com"
        self.PHRS_CONTRACT = "0xf6a07fe10e28a70d1b0f36c7eb7745d2bae2a312"
        self.WPHRS_CONTRACT = "0x76aaada469d23216be5f7c596fa25f282ff9b364"
        self.USDC_CONTRACT = "0xad902cf99c2de2f1ba5ec4d642fd7e49cae9ee37"
        self.SWAP_ROUTER = "0x1a4de519154ae51200b0ad7c90f7fac75547888a"
        self.ERC20_ABI = [
            {
                "constant": True,
                "inputs": [{"name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "owner", "type": "address"},
                    {"name": "spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [],
                "name": "deposit",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [{"name": "wad", "type": "uint256"}],
                "name": "withdraw",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        self.MULTICALL_ABI = [
            {
                "inputs": [
                    {"internalType": "uint256", "name": "collectionAndSelfcalls", "type": "uint256"},
                    {"internalType": "bytes[]", "name": "data", "type": "bytes[]"}
                ],
                "name": "multicall",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
        self.ref_code ="" # "LGwM5n8aXBhbjUlU" 
        self.proxies = []
        self.proxy_idx = 0
        self.account_proxy_map = {}

    def log(self, msg, color=Fore.WHITE):
        """打印带时间戳的日志"""
        print(
            f"{Fore.CYAN}[{datetime.now().astimezone(beijing).strftime('%Y-%m-%d %H:%M:%S')}]{Style.RESET_ALL} "
            f"{color}{msg}{Style.RESET_ALL}"
        )

    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def welcome(self):
        """显示欢迎信息"""
        print(
            f"{Fore.GREEN}=== Pharos Testnet 自动化助手 ==={Style.RESET_ALL}\n"
            f"{Fore.YELLOW}欢迎使用！本工具仅限测试网使用"
            f"{Fore.CYAN}当前时间: {datetime.now().astimezone(beijing).strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

    async def load_proxies(self, proxy_choice):
        """加载代理"""
        try:
            if proxy_choice == 1:
                async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                    async with session.get("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt") as resp:
                        resp.raise_for_status()
                        self.proxies = (await resp.text()).splitlines()
            else:
                with open("proxies.txt", "r") as f:
                    self.proxies = f.read().splitlines()
            self.log(f"已加载 {len(self.proxies)} 个代理", Fore.GREEN)
        except Exception as e:
            self.log(f"加载代理失败: {e}", Fore.RED)
            self.proxies = []

    def check_proxy_scheme(self, proxy):
        """检查代理格式"""
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxy.startswith(scheme) for scheme in schemes):
            return proxy
        return f"http://{proxy}"

    def get_proxy(self, address):
        """为账户分配代理"""
        if not self.proxies:
            return None
        if address not in self.account_proxy_map:
            proxy = self.check_proxy_scheme(self.proxies[self.proxy_idx])
            self.account_proxy_map[address] = proxy
            self.proxy_idx = (self.proxy_idx + 1) % len(self.proxies)
        return self.account_proxy_map[address]

    def rotate_proxy(self, address):
        """轮换代理"""
        if not self.proxies:
            return None
        proxy = self.check_proxy_scheme(self.proxies[self.proxy_idx])
        self.account_proxy_map[address] = proxy
        self.proxy_idx = (self.proxy_idx + 1) % len(self.proxies)
        return proxy

    def generate_address(self, private_key):
        """生成以太坊地址"""
        try:
            account = Account.from_key(private_key)
            return account.address
        except Exception as e:
            self.log(f"生成地址失败: {e}", Fore.RED)
            return None

    def generate_random_receiver(self):
        """生成随机接收地址"""
        try:
            private_key_bytes = secrets.token_bytes(32)
            private_key_hex = to_hex(private_key_bytes)
            account = Account.from_key(private_key_hex)
            return account.address
        except Exception as e:
            self.log(f"生成随机接收地址失败: {e}", Fore.RED)
            return None

    def sign_login(self, private_key, address):
        """生成登录签名"""
        try:
            msg = encode_defunct(text="pharos")
            signed = Account.sign_message(msg, private_key=private_key)
            signature = to_hex(signed.signature)
            return f"{self.API_BASE}/user/login?address={address}&signature={signature}&invite_code={self.ref_code}"
        except Exception as e:
            self.log(f"生成登录签名失败: {e}", Fore.RED)
            return None

    async def check_connection(self, proxy=None):
        """检查网络连接"""
        connector = ProxyConnector.from_url(proxy) if proxy else None
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=30)) as session:
                async with session.get("https://testnet.pharosnetwork.xyz", headers={}) as resp:
                    resp.raise_for_status()
                    return True
        except Exception as e:
            self.log(f"连接检查失败: {e}", Fore.RED)
            return False

    async def login(self, url, proxy=None, retries=3):
        """用户登录"""
        headers = {**self.headers, "Authorization": "Bearer null", "Content-Length": "0"}
        connector = ProxyConnector.from_url(proxy) if proxy else None
        for attempt in range(retries):
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url, headers=headers) as resp:
                        resp.raise_for_status()
                        return (await resp.json())["data"]["jwt"]
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    self.log(f"登录失败 (尝试 {retries} 次): {e}", Fore.RED)
                    return None

    async def user_profile(self, address, token, proxy=None, retries=3):
        """获取用户资料"""
        url = f"{self.API_BASE}/user/profile?address={address}"
        headers = {**self.headers, "Authorization": f"Bearer {token}"}
        connector = ProxyConnector.from_url(proxy) if proxy else None
        for attempt in range(retries):
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url, headers=headers) as resp:
                        resp.raise_for_status()
                        return await resp.json()
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    self.log(f"获取用户资料失败: {e}", Fore.RED)
                    return None

    async def sign_in(self, address, token, proxy=None, retries=3):
        """签到"""
        url = f"{self.API_BASE}/sign/in?address={address}"
        headers = {**self.headers, "Authorization": f"Bearer {token}", "Content-Length": "0"}
        connector = ProxyConnector.from_url(proxy) if proxy else None
        for attempt in range(retries):
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url, headers=headers) as resp:
                        resp.raise_for_status()
                        return await resp.json()
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    self.log(f"签到失败: {e}", Fore.RED)
                    return None

    async def faucet_status(self, address, token, proxy=None, retries=3):
        """检查水龙头状态"""
        url = f"{self.API_BASE}/faucet/status?address={address}"
        headers = {**self.headers, "Authorization": f"Bearer {token}"}
        connector = ProxyConnector.from_url(proxy) if proxy else None
        for attempt in range(retries):
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.get(url, headers=headers) as resp:
                        resp.raise_for_status()
                        return await resp.json()
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    self.log(f"检查水龙头状态失败: {e}", Fore.RED)
                    return None

    async def claim_faucet(self, address, token, proxy=None, retries=3):
        """领取水龙头"""
        url = f"{self.API_BASE}/faucet/daily?address={address}"
        headers = {**self.headers, "Authorization": f"Bearer {token}", "Content-Length": "0"}
        connector = ProxyConnector.from_url(proxy) if proxy else None
        for attempt in range(retries):
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url, headers=headers) as resp:
                        resp.raise_for_status()
                        return await resp.json()
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    self.log(f"领取水龙头失败: {e}", Fore.RED)
                    return None

    async def send_to_friends(self, address, token, tx_hash, proxy=None, retries=3):
        """验证转账任务"""
        url = f"{self.API_BASE}/task/verify?address={address}&task_id=103&tx_hash={tx_hash}"
        headers = {**self.headers, "Authorization": f"Bearer {token}", "Content-Length": "0"}
        connector = ProxyConnector.from_url(proxy) if proxy else None
        for attempt in range(retries):
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=60)) as session:
                    async with session.post(url, headers=headers) as resp:
                        resp.raise_for_status()
                        return await resp.json()
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(2)
                else:
                    self.log(f"验证转账任务失败: {e}", Fore.RED)
                    return None

    async def get_balance(self, address, contract_address):
        """获取代币余额"""
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        try:
            if contract_address == "PHRS":
                balance = web3.eth.get_balance(address)
                decimals = 18
            else:
                token_contract = web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=self.ERC20_ABI)
                decimals = token_contract.functions.decimals().call()
                balance = token_contract.functions.balanceOf(address).call()
            return balance / (10 ** decimals)
        except Exception as e:
            self.log(f"获取余额失败: {e}", Fore.RED)
            return None

    def get_multicall_data(self, address, from_contract_address, to_contract_address, swap_amount):
        """生成多重调用数据"""
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        try:
            data = encode(
                ['address', 'address', 'uint256', 'address', 'uint256', 'uint256', 'uint256'],
                [
                    web3.to_checksum_address(from_contract_address),
                    web3.to_checksum_address(to_contract_address),
                    500,
                    web3.to_checksum_address(address),
                    web3.to_wei(swap_amount, "ether"),
                    0,
                    0
                ]
            )
            return [b'\x04\xe4\x5a\xaf' + data]
            #return [b'\x5a\xe4\x01\xdc' + data]
        except Exception as e:
            self.log(f"生成多重调用数据失败: {e}", Fore.RED)
            return []

    async def perform_transfer(self, private_key, address, receiver, amount):
        """执行转账"""
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        try:
            txn = {
                "to": receiver,
                "value": web3.to_wei(amount, "ether"),
                "nonce": web3.eth.get_transaction_count(address),
                "gas": 21000,
                "gasPrice": web3.eth.gas_price,
                "chainId": web3.eth.chain_id
            }
            signed_tx = web3.eth.account.sign_transaction(txn, private_key)
            tx_hash = web3.to_hex(web3.eth.send_raw_transaction(signed_tx.raw_transaction))
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash, receipt.blockNumber
        except Exception as e:
            self.log(f"转账失败: {e}", Fore.RED)
            return None, None

    async def perform_wrapped(self, private_key, address, amount):
        """包装 PHRS 到 WPHRS"""
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        contract = web3.eth.contract(address=Web3.to_checksum_address(self.WPHRS_CONTRACT), abi=self.ERC20_ABI)
        try:
            amount_wei = web3.to_wei(amount, "ether")
            txn = contract.functions.deposit().build_transaction({
                "from": address,
                "value": amount_wei,
                "gas": 50000,
                "gasPrice": web3.eth.gas_price,
                "nonce": web3.eth.get_transaction_count(address)
            })
            signed_tx = web3.eth.account.sign_transaction(txn, private_key)
            tx_hash = web3.to_hex(web3.eth.send_raw_transaction(signed_tx.raw_transaction))
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash, receipt.blockNumber
        except Exception as e:
            self.log(f"包装失败: {e}", Fore.RED)
            return None, None

    async def perform_unwrapped(self, private_key, address, amount):
        """解包 WPHRS 到 PHRS"""
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        contract = web3.eth.contract(address=Web3.to_checksum_address(self.WPHRS_CONTRACT), abi=self.ERC20_ABI)
        try:
            amount_wei = web3.to_wei(amount, "ether")
            txn = contract.functions.withdraw(amount_wei).build_transaction({
                "from": address,
                "gas": 50000,
                "gasPrice": web3.eth.gas_price,
                "nonce": web3.eth.get_transaction_count(address)
            })
            signed_tx = web3.eth.account.sign_transaction(txn, private_key)
            tx_hash = web3.to_hex(web3.eth.send_raw_transaction(signed_tx.raw_transaction))
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash, receipt.blockNumber
        except Exception as e:
            self.log(f"解包失败: {e}", Fore.RED)
            return None, None

    async def approve_swap(self, private_key, address, contract_address):
        """批准交换"""
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        swap_router = Web3.to_checksum_address(self.SWAP_ROUTER)
        token_contract = web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=self.ERC20_ABI)
        try:
            approve_tx = token_contract.functions.approve(swap_router, 2**256 - 1).build_transaction({
                "from": address,
                "gas": 50000,
                "gasPrice": web3.eth.gas_price,
                "nonce": web3.eth.get_transaction_count(address)
            })
            signed_tx = web3.eth.account.sign_transaction(approve_tx, private_key)
            tx_hash = web3.to_hex(web3.eth.send_raw_transaction(signed_tx.raw_transaction))
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"批准交换成功: {tx_hash}")
            return True
        except Exception as e:
            self.log(f"批准交换失败: {e}", Fore.RED)
            return False

    async def perform_swap(self, private_key, address, multicall_data):
        """执行交换"""
        web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        contract = web3.eth.contract(address=Web3.to_checksum_address(self.SWAP_ROUTER), abi=self.MULTICALL_ABI)
        try:
            tx_data = contract.functions.multicall(int(time.time()), multicall_data)
            estimated_gas = tx_data.estimate_gas({"from": address})
            tx = tx_data.build_transaction({
                "from": address,
                "gas": int(estimated_gas * 1.5),
                "gasPrice": web3.eth.gas_price,
                "nonce": web3.eth.get_transaction_count(address)
            })
            signed_tx = web3.eth.account.sign_transaction(tx, private_key)
            tx_hash = web3.to_hex(web3.eth.send_raw_transaction(signed_tx.raw_transaction))
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash, receipt.blockNumber
        except Exception as e:
            self.log(f"交换失败: {e}", Fore.RED)
            return None, None

    async def print_timer(self, delay):
        """打印倒计时"""
        for remaining in range(delay, 0, -1):
            print(
                f"{Fore.CYAN}[{datetime.now().astimezone(beijing).strftime('%Y-%m-%d %H:%M:%S')}]{Style.RESET_ALL} "
                f"{Fore.YELLOW}等待 {remaining} 秒后继续...{Style.RESET_ALL}",
                end="\r"
            )
            await asyncio.sleep(1)

    def print_question(self):
        """获取用户输入"""
        daily_transfers = 0
        daily_swaps = 0


        print("请选择代理设置:")
        print("1. 使用公共代理")
        print("2. 使用私有代理")
        print("3. 不使用代理")
        while True:
            try:
                use_proxy = int(input(f"{Fore.BLUE}输入选项 [1/2/3]: {Style.RESET_ALL}"))
                if use_proxy in [1, 2, 3]:
                    break
                self.log("请输入 1、2 或 3", Fore.RED)
            except ValueError:
                self.log("请输入有效数字", Fore.RED)

        rotate_proxy = False
        if use_proxy in [1, 2]:
            while True:
                rotate = input("是否自动轮换无效代理？[y/n]: ").lower()
                if rotate in ['y', 'n']:
                    rotate_proxy = rotate == 'y'
                    break
                self.log("请输入 y 或 n", Fore.RED)

        return daily_transfers, daily_swaps, use_proxy, rotate_proxy

    async def process_account(self, private_key, daily_transfers, daily_swaps, use_proxy, rotate_proxy):
        """处理单个账户"""
        address = self.generate_address(private_key)
        if not address:
            return

        url_login = self.sign_login(private_key, address)
        if not url_login:
            return

        self.log(f"处理账户: {address[:6]}...{address[-6:]}", Fore.YELLOW)

    
        proxy = self.get_proxy(address) if use_proxy else None
        if rotate_proxy:
            while not await self.check_connection(proxy):
                self.log(f"代理 {proxy} 无效，轮换中...", Fore.YELLOW)
                proxy = self.rotate_proxy(address)
                await asyncio.sleep(2)
        elif use_proxy and not await self.check_connection(proxy):
            self.log(f"代理 {proxy} 无效，跳过账户", Fore.RED)
            return

    
        token = await self.login(url_login, proxy)
        if not token:
            return
        self.log("登录成功", Fore.GREEN)

        operations = ["sign_in"]
        random.shuffle(operations)

        for op in operations:
            if op == "sign_in":
                # 签到
                self.log("执行签到", Fore.BLUE)
                sign_in = await self.sign_in(address, token, proxy)
                if sign_in and sign_in.get("msg") == "ok":
                    self.log("签到成功", Fore.GREEN)
                elif sign_in and sign_in.get("msg") == "already signed in today":
                    self.log("今日已签到", Fore.YELLOW)
                else:
                    self.log("签到失败", Fore.RED)
                await self.print_timer(random.randint(10, 30))

            elif op == "faucet":
              
                self.log("执行水龙头领取", Fore.BLUE)
                profile = await self.user_profile(address, token, proxy)
                points = profile.get("data", {}).get("user_info", {}).get("TotalPoints", "N/A") if profile and profile.get("msg") == "ok" else "N/A"
                self.log(f"当前积分: {points} PTS", Fore.WHITE)
                faucet_status = await self.faucet_status(address, token, proxy)
                if faucet_status and faucet_status.get("msg") == "ok":
                    is_able = faucet_status.get("data", {}).get("is_able_to_faucet", False)
                    if is_able:
                        claim = await self.claim_faucet(address, token, proxy)
                        if claim and claim.get("msg") == "ok":
                            self.log("水龙头领取成功: 0.2 PHRS", Fore.GREEN)
                        else:
                            self.log("水龙头领取失败", Fore.RED)
                    else:
                        available_ts = faucet_status.get("data", {}).get("avaliable_timestamp", None)
                        available_time = datetime.fromtimestamp(available_ts).astimezone(beijing).strftime('%Y-%m-%d %H:%M:%S') if available_ts else "未知"
                        self.log(f"水龙头已领取，下次可用时间: {available_time}", Fore.YELLOW)
                else:
                    self.log("获取水龙头状态失败", Fore.RED)
                await self.print_timer(random.randint(5, 60))

            elif op == "transfer":
             
                self.log("执行转账", Fore.BLUE)
                for i in range(daily_transfers):
                    self.log(f"转账 {i+1}/{daily_transfers}", Fore.GREEN)
                    receiver = self.generate_random_receiver()
                    if not receiver:
                        continue
                    balance = await self.get_balance(address, "PHRS")
                    if balance is None or balance < 0.001: 
                        self.log("余额不足，跳过转账", Fore.YELLOW)
                        break
                  
                    tx_amount = min(random.uniform(0.001, 0.01), balance * random.uniform(0.01, 0.1))
                    self.log(f"余额: {balance:.4f} PHRS", Fore.WHITE)
                    self.log(f"转账金额: {tx_amount:.6f} PHRS", Fore.WHITE)
                    self.log(f"接收地址: {receiver}", Fore.WHITE)
                    tx_hash, block_number = await self.perform_transfer(private_key, address, receiver, tx_amount)
                    if tx_hash and block_number:
                        verify = await self.send_to_friends(address, token, tx_hash, proxy)
                        explorer = f"https://testnet.pharosscan.xyz/tx/{tx_hash}"
                        if verify and verify.get("msg") == "task verified successfully":
                            self.log("转账验证成功", Fore.GREEN)
                            self.log(f"区块: {block_number}", Fore.WHITE)
                            self.log(f"交易哈希: {tx_hash}", Fore.WHITE)
                            self.log(f"浏览器: {explorer}", Fore.WHITE)
                        else:
                            self.log("转账验证失败", Fore.RED)
                    else:
                        self.log("转账失败", Fore.RED)
                    await self.print_timer(random.randint(10, 60))

            elif op == "wrap":
               
                self.log("执行包装 PHRS -> WPHRS", Fore.BLUE)
                balance = await self.get_balance(address, "PHRS")
                if balance is None or balance < 0.001:
                    self.log("PHRS 余额不足，跳过包装", Fore.YELLOW)
                else:
                   
                    wrap_amount = min(random.uniform(0.001, 0.1), balance * random.uniform(0.05, 0.2))
                    self.log(f"余额: {balance:.4f} PHRS", Fore.WHITE)
                    self.log(f"包装金额: {wrap_amount:.6f} PHRS", Fore.WHITE)
                    tx_hash, block_number = await self.perform_wrapped(private_key, address, wrap_amount)
                    if tx_hash and block_number:
                        explorer = f"https://testnet.pharosscan.xyz/tx/{tx_hash}"
                        self.log(f"包装 {wrap_amount:.6f} PHRS 成功", Fore.GREEN)
                        self.log(f"区块: {block_number}", Fore.WHITE)
                        self.log(f"交易哈希: {tx_hash}", Fore.WHITE)
                        self.log(f"浏览器: {explorer}", Fore.WHITE)
                    else:
                        self.log("包装失败", Fore.RED)
                await self.print_timer(random.randint(10, 60))

            elif op == "unwrap":
               
                self.log("执行解包 WPHRS -> PHRS", Fore.BLUE)
                balance = await self.get_balance(address, self.WPHRS_CONTRACT)
                if balance is None or balance < 0.001:
                    self.log("WPHRS 余额不足，跳过解包", Fore.YELLOW)
                else:
                   
                    unwrap_amount = min(random.uniform(0.001, 0.1), balance * random.uniform(0.05, 0.2))
                    self.log(f"余额: {balance:.4f} WPHRS", Fore.WHITE)
                    self.log(f"解包金额: {unwrap_amount:.6f} WPHRS", Fore.WHITE)
                    tx_hash, block_number = await self.perform_unwrapped(private_key, address, unwrap_amount)
                    if tx_hash and block_number:
                        explorer = f"https://testnet.pharosscan.xyz/tx/{tx_hash}"
                        self.log(f"解包 {unwrap_amount:.6f} WPHRS 成功", Fore.GREEN)
                        self.log(f"区块: {block_number}", Fore.WHITE)
                        self.log(f"交易哈希: {tx_hash}", Fore.WHITE)
                        self.log(f"浏览器: {explorer}", Fore.WHITE)
                    else:
                        self.log("解包失败", Fore.RED)
                await self.print_timer(random.randint(1, 10))

            elif op == "swap":
                # 交换 WPHRS ↔ USDC
                self.log("执行 WPHRS 与 USDC 互换", Fore.BLUE)
                for i in range(daily_swaps):
                    self.log(f"交换 {i+1}/{daily_swaps}", Fore.GREEN)
                    for swap_type in ["WPHRStoUSDC", "USDCtoWPHRS"]:
                        from_contract = self.WPHRS_CONTRACT if swap_type == "WPHRStoUSDC" else self.USDC_CONTRACT
                        to_contract = self.USDC_CONTRACT if swap_type == "WPHRStoUSDC" else self.WPHRS_CONTRACT
                        from_token = "WPHRS" if swap_type == "WPHRStoUSDC" else "USDC"
                        to_token = "USDC" if swap_type == "WPHRStoUSDC" else "WPHRS"
                        # 随机金额：WPHRStoUSDC 0.001-0.01，USDCtoWPHRS 0.5-2.0
                        swap_amount = random.uniform(0.001, 0.01) if swap_type == "WPHRStoUSDC" else random.uniform(0.5, 2.0)
                        self.log(f"交换类型: {from_token} -> {to_token}", Fore.BLUE)
                        balance = await self.get_balance(address, from_contract)
                        self.log(f"余额: {balance:.4f} {from_token}", Fore.WHITE)
                        self.log(f"交换金额: {swap_amount:.6f} {from_token}", Fore.WHITE)
                        if balance is None or balance < swap_amount:
                            self.log(f"{from_token} 余额不足，跳过交换", Fore.YELLOW)
                            continue
                        approved = await self.approve_swap(private_key, address, from_contract)
                        await asyncio.sleep(15)

                        if not approved:
                            continue
                        multicall_data = self.get_multicall_data(address, from_contract, to_contract, swap_amount)
                        if not multicall_data:
                            continue
                        tx_hash, block_number = await self.perform_swap(private_key, address, multicall_data)
                        if tx_hash and block_number:
                            explorer = f"https://testnet.pharosscan.xyz/tx/{tx_hash}"
                            self.log(f"交换 {swap_amount:.6f} {from_token} -> {to_token} 成功", Fore.GREEN)
                            self.log(f"区块: {block_number}", Fore.WHITE)
                            self.log(f"交易哈希: {tx_hash}", Fore.WHITE)
                            self.log(f"浏览器: {explorer}", Fore.WHITE)
                        else:
                            self.log("交换失败", Fore.RED)
                        await self.print_timer(random.randint(1, 10))

    async def process_accounts_concurrently(self, accounts, daily_transfers, daily_swaps, use_proxy, rotate_proxy, batch_size=1):
        """并发处理账户"""
        self.log(f"开始并发处理 {len(accounts)} 个账户，批次大小: {batch_size}", Fore.YELLOW)
        for i in range(0, len(accounts), batch_size):
            batch = accounts[i:i + batch_size]
            tasks = [
                self.process_account(
                    private_key, daily_transfers, daily_swaps, use_proxy, rotate_proxy
                ) for private_key in batch
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            self.log(f"完成批次 {i//batch_size + 1}/{(len(accounts) + batch_size - 1)//batch_size}", Fore.GREEN)
            await asyncio.sleep(random.randint(1, 10))

    async def main(self):
        """主函数"""
        self.clear_screen()
        self.welcome()

        daily_transfers, daily_swaps, use_proxy, rotate_proxy = self.print_question()

      
        try:
            with open("accounts.txt", "r") as f:
                accounts = [line.strip() for line in f if line.strip()]
            self.log(f"共加载 {len(accounts)} 个账户", Fore.GREEN)
        except FileNotFoundError:
            self.log("未找到 accounts.txt 文件", Fore.RED)
            return

       
        self.clear_screen()
        self.welcome()
        self.log(f"账户总数: {len(accounts)}", Fore.GREEN)
        await self.process_accounts_concurrently(
            accounts, 1, 1 , use_proxy in [1, 2], rotate_proxy
        )

if __name__ == "__main__":
    try:
        bot = PharosBot()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN}[{datetime.now().astimezone(beijing).strftime('%Y-%m-%d %H:%M:%S')}]{Style.RESET_ALL} "
            f"{Fore.RED}程序已退出{Style.RESET_ALL}"
        )
