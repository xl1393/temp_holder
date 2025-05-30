import requests
import json
import logging
import time
from urllib.parse import urlparse, parse_qs

# 配置日志，包含时间、日志级别和消息
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',  # 设置时间格式为精确到秒
    handlers=[
        logging.StreamHandler()  # 输出到控制台
    ]
)

def get_headers(origin: str, user_agent: str) -> dict:
    """生成通用的请求头，根据Origin和User-Agent动态生成"""
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Origin": origin,
        "Referer": origin + "/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": user_agent,
        "sec-ch-ua": "\"Chromium\";v=\"124\", \"Google Chrome\";v=\"124\", \"Not-A.Brand\";v=\"99\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }
    return headers

def get_ct0(auth_token: str, proxies: dict = None) -> str:
    """获取ct0 cookie，最多重试3次，仅在网络错误时重试"""
    retries = 0
    max_retries = 3
    while retries < max_retries:
        cookies = {'auth_token': auth_token}
        url = "https://x.com/home"  # 推特主页地址
        headers = get_headers(
            origin="https://twitter.com",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        try:
            response = requests.get(url, headers=headers, cookies=cookies, proxies=proxies, timeout=30)
            if response.status_code == 200:
                if 'ct0' in response.cookies:
                    ct0 = response.cookies['ct0']
                    logging.info(f"Found ct0: {ct0}")
                    return ct0
                else:
                    logging.error("ct0 not found in cookies.")
                    return None  # 不进行重试，仅记录错误并返回
            else:
                logging.error(f"Request failed with status code: {response.status_code}")
                return None  # 不进行重试，仅记录错误并返回
        except requests.exceptions.RequestException as e:
            logging.error(f"请求ct0时发生异常: {e}")
            retries += 1
            logging.warning(f"获取ct0失败，正在尝试重试 {retries}/{max_retries}...")
            time.sleep(5)
    
    logging.error("获取ct0失败，已达到最大重试次数。")
    return None

# 这里增加一步，需要获取code_challenge 和 state
def get_oauth_params():
    # 设置请求头
    headers = {
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Referer": "https://testnet.pharosnetwork.xyz/",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }

    # 发送GET请求，不允许自动重定向
    response = requests.get('https://api.pharosnetwork.xyz/auth/twitter', headers=headers, allow_redirects=False)

    # 检查是否是重定向响应
    if response.status_code in [301, 302, 303, 307, 308]:
        location = response.headers.get('Location')
        if location:
            # 解析URL并提取查询参数
            parsed_url = urlparse(location)
            query_params = parse_qs(parsed_url.query)
            
            # 获取 code_challenge 和 state
            code_challenge = query_params.get('code_challenge', [None])[0]
            state = query_params.get('state', [None])[0]
            
            if code_challenge and state:
                return code_challenge, state
            else:
                raise ValueError("重定向URL中缺少“code_challenge”或“state”")
                return None, None
        else:
            raise ValueError("重定向响应不包含“Location”标头")
            return None, None
    else:
        raise ValueError(f"状态代码: {response.status_code}")
        return None, None

def get_auth_code(ct0: str, auth_token: str, code_challenge: str, state: str, proxies: dict = None) -> str:
    """获取auth_code，最多重试3次，仅在网络错误时重试"""
    retries = 0
    max_retries = 3
    while retries < max_retries:
        url = "https://twitter.com/i/api/2/oauth2/authorize"
        params = {
            'client_id': 'TGQwNktPQWlBQzNNd1hyVkFvZ2E6MTpjaQ',
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
            'redirect_uri': 'https://testnet.pharosnetwork.xyz',
            'response_type': 'code',
            'scope': 'users.read tweet.read follows.read',
            'state': state
        }
# https://twitter.com/i/oauth2/authorize?client_id=TGQwNktPQWlBQzNNd1hyVkFvZ2E6MTpjaQ&code_challenge=hHDKkZkIBZxZoTzaYvk-9QoK_aEAuAWQWimRbHgwRGY&
# code_challenge_method=S256&redirect_uri=https%3A%2F%2Ftestnet.pharosnetwork.xyz&response_type=code&scope=users.read+tweet.read+follows.read&state=twitterzPgMOZ55hnXCubjayC~fMg.oClJwCKDfrOaaCI8.ZW4

        headers = get_headers(
            origin="https://twitter.com",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        headers.update({
            "x-csrf-token": ct0,
            'x-twitter-client-language': 'zh',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-active-user': 'yes',
            'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
        })
        cookies = {
            'auth_token': auth_token,
            'ct0': ct0
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, cookies=cookies, proxies=proxies, timeout=30)
            if response.status_code == 200:
                response_data = response.json()
                auth_code = response_data.get('auth_code')
                if auth_code:
                    logging.info(f"auth_code: {auth_code}")
                    return auth_code
                else:
                    logging.error("auth_code not found in the response.")
                    return None  # 不进行重试，仅记录错误并返回
            else:
                logging.error(f"Request failed with status code: {response.status_code}")
                return None  # 不进行重试，仅记录错误并返回
        except requests.exceptions.RequestException as e:
            logging.error(f"请求auth_code时发生异常: {e}")
            retries += 1
            logging.warning(f"获取auth_code失败，正在尝试重试 {retries}/{max_retries}...")
            time.sleep(5)
    
    logging.error("获取auth_code失败，已达到最大重试次数。")
    return None

def authorize_with_code(ct0: str, auth_token: str, auth_code: str, proxies: dict = None) -> str:
    """使用auth_code进行授权，返回重定向的URI，最多重试3次，仅在网络错误时重试"""
    retries = 0
    max_retries = 3
    while retries < max_retries:
        url = "https://twitter.com/i/api/2/oauth2/authorize"
        headers = {
            "Host": "twitter.com",
            "Connection": "keep-alive",
            "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "x-twitter-client-language": "pt",
            "x-csrf-token": ct0,
            "sec-ch-ua-mobile": "?0",
            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "content-type": "application/x-www-form-urlencoded",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-active-user": "yes",
            "sec-ch-ua-platform": '"Windows"',
            "Accept": "/",
            "Origin": "https://twitter.com",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        cookies = {
            "auth_token": auth_token,
            "ct0": ct0,
            "lang": "pt",
        }

        data = {
            "approval": "true",
            "code": auth_code
        }
        
        try:
            response = requests.post(url, headers=headers, data=data, cookies=cookies, proxies=proxies, timeout=30)
            if response.status_code == 200:
                try:
                    response_data = response.json()
                except ValueError:
                    logging.error(f"非JSON响应内容: {response.text}")
                    return None  # 不进行重试，仅记录错误并返回

                redirect_uri = response_data.get('redirect_uri')
                if redirect_uri:
                    logging.info(f"Redirect URI: {redirect_uri}")
                    return redirect_uri
                else:
                    logging.error("在响应中找不到redirect_uri")
                    return None  # 不进行重试，仅记录错误并返回
            else:
                logging.error(f"请求失败，状态代码为: {response.status_code}")
                # 可选择是否需要根据特定状态码决定是否重试，这里不重试
                return None  # 不进行重试，仅记录错误并返回
        except requests.exceptions.RequestException as e:
            logging.error(f"授权时发生异常: {e}")
            retries += 1
            logging.warning(f"授权失败，正在尝试重试 {retries}/{max_retries}...")
            time.sleep(5)
    
    logging.error("授权失败，已达到最大重试次数。")
    return None

def bind_wallet(token: str, auth_code: str, state: str, address: str, proxies: dict = None) -> bool:
    """绑定Twitter账号到Pharos Network。
    如果绑定成功（即响应中的'msg'为'bind success'），返回True; 否则，返回False。
    Returns:
        bool: 绑定成功返回True，否则返回False。
    """
    # 设置API的URL
    url = "https://api.pharosnetwork.xyz/auth/bind/twitter"
    
    # 设置请求参数
    params = {
        'state': state,
        'code': auth_code,
        'address': address
    }
    
    # 设置请求头
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Origin': 'https://testnet.pharosnetwork.xyz',
        'Referer': 'https://testnet.pharosnetwork.xyz/',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'zh-CN,zh;q=0.9'
    }
    
    try:
        # 发送POST请求
        response = requests.post(url, params=params, headers=headers, proxies=proxies, timeout=30)
        response.raise_for_status()  # 如果响应状态码不是200，将引发HTTPError
        
        # 解析JSON响应
        response_data = response.json()
        
        # 检查'msg'字段是否为'bind success'
        if response_data.get('msg') == 'bind success':
            return True
        else:
            print(f"绑定失败，消息：{response_data.get('msg')}")
            return False
    except requests.exceptions.RequestException as e:
        # 处理请求异常
        print(f"请求过程中发生错误：{e}")
        return False

def get_auth_code_flow(auth_token: str, code_challenge: str = None, state: str = None, proxies: dict = None) -> str:
    """完整的获取auth_code流程"""
    print("第一步，获取ct0")
    ct0 = get_ct0(auth_token, proxies)
    if not ct0:
        return None
    
    print("第二步，获取auth_code")
    auth_code = get_auth_code(ct0, auth_token, code_challenge, state, proxies)
    if not auth_code:
        return None
    
    print("第三步，获取redirect_uri")
    redirect_uri = authorize_with_code(ct0, auth_token, auth_code, proxies)
    if not redirect_uri:
        return None
    
    # 根据需要，可以返回redirect_uri或其他信息
    return auth_code

# 主函数入口
if __name__ == "__main__":
    auth_token = "ba37425329bc804daad6bb56a1cbbb4a086c42be"  # 请替换为你的auth_token
    get_auth_code_flow(auth_token)
