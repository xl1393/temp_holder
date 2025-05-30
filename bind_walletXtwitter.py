import logging
import requests
from web3 import Web3
import eth_account.messages as messages
from eth_account.messages import encode_defunct
import time
from eth_account import Account
from datetime import datetime, timedelta
import random
from multiprocessing import Pool, Manager, Lock
from requests.exceptions import RequestException

from twitter_auth import get_auth_code_flow, get_oauth_params, bind_wallet


def generate_address(private_key):
    """生成以太坊地址"""
    try:
        account = Account.from_key(private_key)
        print(f"生成地址: {account.address}")
        return account.address
    except Exception as e:
        self.log(f"生成地址失败: {e}", Fore.RED)
        return None

def main():
    """主函数"""
    print("开始绑定钱包...")
    try:
        with open("accounts.txt", "r") as f:
            accounts = [line.strip() for line in f if line.strip()]
        with open("Xtoken.txt", "r") as f:
            twitter_auth = [line.strip() for line in f if line.strip()]
        if len(accounts) == 0 or len(twitter_auth) == 0 or len(accounts) != len(twitter_auth):
            print("请确保accounts.txt和Xtoken.txt文件中有相同数量的非空行。")
            return
        print(f"读取到 {len(accounts)} 个账户和 {len(twitter_auth)} 个Twitter认证令牌。")

        for i in range(len(accounts)):
            code_challenge, state = get_oauth_params()
            auth_code = get_auth_code_flow(auth_token=twitter_auth[i], code_challenge=code_challenge, state=state)
            bind_success = bind_wallet(token=twitter_auth[i], auth_code=auth_code, state=state, address=generate_address(accounts[i]))
            print(f"账户 {i + 1} 绑定结果: {bind_success}, 地址: {generate_address(accounts[i])}, Twitter Token: {twitter_auth[i]}")
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    main()