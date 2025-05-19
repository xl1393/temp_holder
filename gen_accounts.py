from eth_account import Account

# 启用助记词支持（如果不需要助记词可以忽略）
Account.enable_unaudited_hdwallet_features()

# 打开文件用于写入
with open("accounts.txt", "w") as f:
    for _ in range(24):
        acct = Account.create()
        private_key = acct.key.hex()  # 去掉开头的 '0x'
        f.write(private_key + "\n")

print("生成完成，私钥已保存在 accounts.txt 中。")
