#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
学术引用系统交互脚本
使用web3.py与智能合约交互
"""

import json
import os
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

# 连接到本地Hardhat节点
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# 检查连接
if not w3.is_connected():
    print("未能连接到以太坊节点！")
    exit(1)

print(f"已连接到以太坊节点，当前区块号: {w3.eth.block_number}")

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
AUTHORS_FILE = os.path.join(DATA_DIR, 'registered_authors.json')

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 全局变量：存储所有注册过的作者地址
registered_authors = set()

# 加载已注册作者信息
def load_registered_authors():
    global registered_authors
    try:
        if os.path.exists(AUTHORS_FILE):
            with open(AUTHORS_FILE, 'r') as f:
                data = json.load(f)
                registered_authors = set(data.get('authors', []))
                print(f"已加载 {len(registered_authors)} 个已注册作者")
    except Exception as e:
        print(f"加载已注册作者信息时出错: {str(e)}")
        registered_authors = set()

# 保存已注册作者信息
def save_registered_authors():
    try:
        data = {
            'authors': list(registered_authors),
            'last_updated': w3.eth.get_block('latest').timestamp
        }
        with open(AUTHORS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"保存已注册作者信息时出错: {str(e)}")

# 在脚本启动时加载已注册作者信息
load_registered_authors()

# 加载合约ABI
def load_contract(contract_name):
    # 合约地址（使用刚才部署的地址）
    contract_addresses = {
        'AuthorToken': '0x5FbDB2315678afecb367f032d93F642f64180aa3',
        'CitationNetwork': '0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0',
        'ProfitDistribution': '0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9',
        'IdentityManagement': '0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512'
    }
    
    # 加载ABI
    artifacts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'artifacts/contracts')
    contract_json_path = os.path.join(artifacts_dir, f"{contract_name}.sol/{contract_name}.json")
    
    try:
        with open(contract_json_path, 'r') as f:
            contract_json = json.load(f)
            contract_abi = contract_json['abi']
    except FileNotFoundError:
        print(f"找不到合约ABI文件: {contract_json_path}")
        return None
    
    # 获取合约地址
    contract_address = contract_addresses.get(contract_name)
    if not contract_address:
        print(f"警告: {contract_name}合约地址未设置")
        return None
    
    # 创建合约实例
    contract = w3.eth.contract(address=contract_address, abi=contract_abi)
    return contract

# 创建账户或加载现有账户
def get_account(private_key=None):
    if private_key:
        if isinstance(private_key, str):
            return Account.from_key(private_key)
        else:
            # 如果是账户对象，直接返回
            return private_key
    else:
        # 创建新账户
        acct = Account.create()
        print(f"创建新账户: {acct.address}")
        print(f"私钥: {acct.key.hex()}")
        
        # 从测试账户转账一些 ETH
        test_account = Account.from_key("0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
        nonce = w3.eth.get_transaction_count(test_account.address)
        tx = {
            'from': test_account.address,
            'to': acct.address,
            'value': Web3.to_wei(1, 'ether'),  # 转账 1 ETH
            'nonce': nonce,
            'gas': 21000,
            'gasPrice': w3.eth.gas_price
        }
        signed_tx = w3.eth.account.sign_transaction(tx, test_account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"已向新账户转账 1 ETH")
        else:
            print("警告：转账失败，新账户可能无法执行交易")
        
        # 返回私钥字符串而不是账户对象
        return acct.key.hex()

def is_valid_address(address):
    return Web3.is_address(address) and Web3.is_checksum_address(address)

def check_contract_deployed(contract):
    try:
        # 尝试获取合约代码
        code = w3.eth.get_code(contract.address)
        if len(code) <= 2:  # 0x 前缀
            return False
            
        # 尝试调用合约的任意函数
        if hasattr(contract.functions, 'owner'):
            contract.functions.owner().call()
        elif hasattr(contract.functions, 'getAuthorInfo'):
            contract.functions.getAuthorInfo(contract.address).call()
        elif hasattr(contract.functions, 'getAuthorLineage'):
            contract.functions.getAuthorLineage(contract.address).call()
        elif hasattr(contract.functions, 'getDistributionInfo'):
            contract.functions.getDistributionInfo(contract.address).call()
        return True
    except Exception as e:
        print(f"合约检查失败: {str(e)}")
        return False

def check_balance(address):
    balance = w3.eth.get_balance(address)
    return balance > Web3.to_wei(0.1, 'ether')  # 确保有至少0.1 ETH

# 作者注册
def register_author(private_key):
    # 确保 private_key 是字符串
    if not isinstance(private_key, str):
        print("错误：无效的私钥格式")
        return False
        
    account = Account.from_key(private_key)
    author_token = load_contract('AuthorToken')
    identity_mgmt = load_contract('IdentityManagement')
    
    if not author_token or not identity_mgmt:
        print("错误：无法加载合约")
        return False
        
    if not check_contract_deployed(author_token):
        print("错误：合约未正确部署")
        return False
        
    if not check_balance(account.address):
        print("错误：账户余额不足")
        return False
    
    try:
        # 检查是否已注册
        author_info = author_token.functions.getAuthorInfo(account.address).call()
        if author_info[3]:  # isRegistered
            print("错误：该地址已经注册为作者")
            return False
            
        # 注册作者身份
        nonce = w3.eth.get_transaction_count(account.address)
        tx = author_token.functions.registerAuthor().build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            # 注册成功，添加到已注册作者集合中并保存
            registered_authors.add(account.address)
            save_registered_authors()  # 保存到文件
            print(f"作者注册交易哈希: {tx_hash.hex()}")
            print(f"交易状态: 成功")
        else:
            print(f"作者注册交易哈希: {tx_hash.hex()}")
            print(f"交易状态: 失败")
            return False
        
        # 生成公钥哈希并注册身份
        message = f"Register author identity for {account.address}"
        message_hash = encode_defunct(text=message)
        signed_message = Account.sign_message(message_hash, private_key)
        # 将 r 和 s 转换为十六进制字符串
        r_hex = hex(signed_message.r)[2:].zfill(64)  # 确保64个字符
        s_hex = hex(signed_message.s)[2:].zfill(64)  # 确保64个字符
        public_key_hash = w3.keccak(hexstr=r_hex + s_hex)
        
        nonce = w3.eth.get_transaction_count(account.address)
        tx = identity_mgmt.functions.registerIdentity(
            public_key_hash,
            f"ipfs://author/{account.address}"
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"身份注册交易哈希: {tx_hash.hex()}")
        print(f"交易状态: {'成功' if receipt.status == 1 else '失败'}")
        
        return True
    except Exception as e:
        print(f"注册作者时出错: {str(e)}")
        return False

# 添加引用
def add_citation(private_key, cited_address, paper_hash):
    if not is_valid_address(cited_address):
        print("错误：无效的被引用者地址")
        return None
        
    account = get_account(private_key)
    citation_network = load_contract('CitationNetwork')
    author_token = load_contract('AuthorToken')
    
    if not citation_network or not author_token:
        print("错误：无法加载合约")
        return None
        
    if not check_contract_deployed(citation_network) or not check_contract_deployed(author_token):
        print("错误：合约未正确部署")
        return None
        
    if not check_balance(account.address):
        print("错误：账户余额不足")
        return None
    
    try:
        # 检查被引用者是否已注册
        cited_info = author_token.functions.getAuthorInfo(cited_address).call()
        if not cited_info[3]:  # isRegistered
            print("错误：被引用者尚未注册为作者")
            return None
            
        # 1. 首先在 CitationNetwork 中添加引用
        nonce = w3.eth.get_transaction_count(account.address)
        tx = citation_network.functions.addCitation(
            cited_address,
            paper_hash
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 3000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            print(f"添加引用到 CitationNetwork 失败")
            return None
            
        # 获取引用ID（从事件日志中）
        citation_id = None
        logs = citation_network.events.CitationAdded().process_receipt(receipt)
        if logs:
            citation_id = logs[0]['args']['citationId'].hex()
            print(f"引用ID: {citation_id}")
        
        # 2. 然后在 AuthorToken 中更新引用信息
        nonce = w3.eth.get_transaction_count(account.address)
        tx = author_token.functions.addCitation(
            cited_address  # 只传入被引用者地址
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 3000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status != 1:
            print(f"添加引用到 AuthorToken 失败")
            return None
            
        # 3. 更新 PageRank 得分（需要合约所有者权限）
        try:
            # 获取合约所有者地址
            owner_address = author_token.functions.owner().call()
            # 如果当前用户是合约所有者，则更新 PageRank
            if account.address.lower() == owner_address.lower():
                nonce = w3.eth.get_transaction_count(account.address)
                tx = author_token.functions.updatePageRanks(
                    10,  # iterations: 迭代次数
                    85   # dampingFactor: 阻尼系数（0.85 * 100）
                ).build_transaction({
                    'from': account.address,
                    'nonce': nonce,
                    'gas': 5000000,  # 需要更多 gas
                    'gasPrice': w3.eth.gas_price
                })
                
                signed_tx = w3.eth.account.sign_transaction(tx, private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt.status == 1:
                    print("PageRank 得分已更新")
                else:
                    print("PageRank 得分更新失败")
            else:
                print("注意：当前用户不是合约所有者，无法更新 PageRank 得分")
                print(f"请使用合约所有者地址 ({owner_address}) 来更新 PageRank")
        except Exception as e:
            print(f"更新 PageRank 得分时出错: {str(e)}")
            
        print(f"成功添加引用")
        print(f"被引用者: {cited_address}")
        print(f"论文哈希: {paper_hash}")
        print(f"引用ID: {citation_id}")
        
        # 显示更新后的引用信息
        cited_info = author_token.functions.getAuthorInfo(cited_address).call()
        print(f"\n更新后的引用信息:")
        print(f"被引用次数: {cited_info[1]}")
        print(f"PageRank得分: {cited_info[2]}")
        
        return citation_id
    except Exception as e:
        print(f"添加引用时出错: {str(e)}")
        return None

# 获取作者信息
def get_author_info(author_address):
    if not is_valid_address(author_address):
        print("错误：无效的作者地址")
        return None
        
    author_token = load_contract('AuthorToken')
    
    if not author_token:
        print("错误：无法加载合约")
        return None
        
    if not check_contract_deployed(author_token):
        print("错误：合约未正确部署")
        return None
    
    try:
        author_info = author_token.functions.getAuthorInfo(author_address).call()
        print(f"作者地址: {author_info[0]}")
        print(f"被引用次数: {author_info[1]}")
        print(f"PageRank得分: {author_info[2]}")
        print(f"是否已注册: {author_info[3]}")
        
        return author_info
    except Exception as e:
        print(f"获取作者信息时出错: {str(e)}")
        return None

# 获取作者引用家族
def get_author_lineage(author_address):
    citation_network = load_contract('CitationNetwork')
    
    if not citation_network:
        return None
    
    try:
        lineage = citation_network.functions.getAuthorLineage(author_address).call()
        print(f"作者 {author_address} 的引用家族成员:")
        for member in lineage:
            print(f"- {member}")
        
        return lineage
    except Exception as e:
        print(f"获取引用家族时出错: {str(e)}")
        return None

# 获取作者分配份额
def get_author_share(distribution_id, author_address):
    if not is_valid_address(author_address):
        print("错误：无效的作者地址")
        return None
        
    profit_distribution = load_contract('ProfitDistribution')
    
    if not profit_distribution:
        print("错误：无法加载合约")
        return None
    
    try:
        share = profit_distribution.functions.getAuthorShare(distribution_id, author_address).call()
        print(f"分配期ID: {distribution_id}")
        print(f"作者地址: {share[0]}")
        print(f"份额百分比: {share[1]}%")
        print(f"分配金额: {Web3.from_wei(share[2], 'ether')} ETH")
        print(f"是否已提取: {share[3]}")
        
        return share
    except Exception as e:
        print(f"获取作者份额时出错: {str(e)}")
        return None

# 提取收益
def withdraw_share(private_key, distribution_id):
    account = Account.from_key(private_key)
    profit_distribution = load_contract('ProfitDistribution')
    
    if not profit_distribution:
        print("错误：无法加载合约")
        return False
    
    try:
        # 检查是否有可提取的份额
        share = profit_distribution.functions.getAuthorShare(distribution_id, account.address).call()
        if share[1] == 0:  # sharePercentage
            print("错误：没有可提取的份额")
            return False
        if share[3]:  # hasWithdrawn
            print("错误：份额已提取")
            return False
            
        nonce = w3.eth.get_transaction_count(account.address)
        tx = profit_distribution.functions.withdrawShare(distribution_id).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"提取收益交易哈希: {tx_hash.hex()}")
        print(f"交易状态: {'成功' if receipt.status == 1 else '失败'}")
        
        return receipt.status == 1
    except Exception as e:
        print(f"提取收益时出错: {str(e)}")
        return False

# 验证身份
def verify_identity(private_key, author_address):
    if not is_valid_address(author_address):
        print("错误：无效的作者地址")
        return False
        
    account = Account.from_key(private_key)
    identity_mgmt = load_contract('IdentityManagement')
    
    if not identity_mgmt:
        print("错误：无法加载合约")
        return False
    
    try:
        # 检查是否是管理员
        if account.address != identity_mgmt.functions.owner().call():
            print("错误：只有管理员可以验证身份")
            return False
            
        nonce = w3.eth.get_transaction_count(account.address)
        tx = identity_mgmt.functions.verifyIdentity(author_address).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"验证身份交易哈希: {tx_hash.hex()}")
        print(f"交易状态: {'成功' if receipt.status == 1 else '失败'}")
        
        return receipt.status == 1
    except Exception as e:
        print(f"验证身份时出错: {str(e)}")
        return False

# 更新身份信息
def update_identity(private_key, author_address, new_public_key_hash, metadata_uri, is_revoked):
    if not is_valid_address(author_address):
        print("错误：无效的作者地址")
        return False
        
    account = Account.from_key(private_key)
    identity_mgmt = load_contract('IdentityManagement')
    
    if not identity_mgmt:
        print("错误：无法加载合约")
        return False
    
    try:
        # 检查是否是管理员
        if account.address != identity_mgmt.functions.owner().call():
            print("错误：只有管理员可以更新身份")
            return False
            
        nonce = w3.eth.get_transaction_count(account.address)
        tx = identity_mgmt.functions.setIdentity(
            author_address,
            new_public_key_hash,
            metadata_uri,
            is_revoked
        ).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"更新身份交易哈希: {tx_hash.hex()}")
        print(f"交易状态: {'成功' if receipt.status == 1 else '失败'}")
        
        return receipt.status == 1
    except Exception as e:
        print(f"更新身份时出错: {str(e)}")
        return False

# 撤销身份
def revoke_identity(private_key, author_address):
    if not is_valid_address(author_address):
        print("错误：无效的作者地址")
        return False
        
    account = Account.from_key(private_key)
    identity_mgmt = load_contract('IdentityManagement')
    
    if not identity_mgmt:
        print("错误：无法加载合约")
        return False
    
    try:
        # 检查是否是管理员
        if account.address != identity_mgmt.functions.owner().call():
            print("错误：只有管理员可以撤销身份")
            return False
            
        nonce = w3.eth.get_transaction_count(account.address)
        tx = identity_mgmt.functions.revokeIdentity(author_address).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"撤销身份交易哈希: {tx_hash.hex()}")
        print(f"交易状态: {'成功' if receipt.status == 1 else '失败'}")
        
        return receipt.status == 1
    except Exception as e:
        print(f"撤销身份时出错: {str(e)}")
        return False

# 验证引用
def verify_citation(private_key, citation_id, proof):
    account = Account.from_key(private_key)
    citation_network = load_contract('CitationNetwork')
    
    if not citation_network:
        print("错误：无法加载合约")
        return False
    
    try:
        # 检查是否是管理员
        if account.address != citation_network.functions.owner().call():
            print("错误：只有管理员可以验证引用")
            return False
            
        nonce = w3.eth.get_transaction_count(account.address)
        tx = citation_network.functions.verifyCitation(citation_id, proof).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 2000000,
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"验证引用交易哈希: {tx_hash.hex()}")
        print(f"交易状态: {'成功' if receipt.status == 1 else '失败'}")
        
        return receipt.status == 1
    except Exception as e:
        print(f"验证引用时出错: {str(e)}")
        return False

# 获取完整的作者引用信息
def get_complete_citation_info(author_address):
    if not is_valid_address(author_address):
        print("错误：无效的作者地址")
        return None
        
    author_token = load_contract('AuthorToken')
    citation_network = load_contract('CitationNetwork')
    
    if not author_token or not citation_network:
        print("错误：无法加载合约")
        return None
    
    try:
        # 从 AuthorToken 获取基本信息
        author_info = author_token.functions.getAuthorInfo(author_address).call()
        print("\n作者基本信息:")
        print(f"作者地址: {author_info[0]}")
        print(f"被引用次数 (AuthorToken): {author_info[1]}")
        print(f"PageRank得分: {author_info[2]}")
        print(f"是否已注册: {author_info[3]}")
        
        # 从 CitationNetwork 获取引用网络信息
        direct_citers = citation_network.functions.getDirectCiters(author_address).call()
        lineage = citation_network.functions.getAuthorLineage(author_address).call()
        
        print("\n引用网络信息:")
        print(f"直接引用者数量: {len(direct_citers)}")
        print("直接引用者列表:")
        for citer in direct_citers:
            print(f"- {citer}")
            
        print(f"\n引用家族大小: {len(lineage)}")
        print("引用家族成员:")
        for member in lineage:
            print(f"- {member}")
        
        # 计算实际的引用次数（从 CitationNetwork）
        citation_count = len(direct_citers)
        
        # 比较两个合约中的引用次数
        if citation_count != author_info[1]:
            print(f"\n注意: 两个合约中的引用次数不一致")
            print(f"CitationNetwork 中的引用次数: {citation_count}")
            print(f"AuthorToken 中的引用次数: {author_info[1]}")
        
        return {
            'author_info': author_info,
            'direct_citers': direct_citers,
            'lineage': lineage,
            'citation_count': citation_count
        }
    except Exception as e:
        print(f"获取完整引用信息时出错: {str(e)}")
        return None

# 获取所有作者信息
def get_all_authors_info():
    author_token = load_contract('AuthorToken')
    citation_network = load_contract('CitationNetwork')
    
    if not author_token or not citation_network:
        print("错误：无法加载合约")
        return None
    
    try:
        print("\n正在获取所有作者信息...")
        
        # 合并测试账户和已注册作者地址
        all_addresses = set([
            "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",  # 测试账户 #0
            "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",  # 测试账户 #1
            "0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"   # 测试账户 #2
        ])
        all_addresses.update(registered_authors)  # 添加所有已注册的作者地址
        
        # 获取合约所有者地址
        owner_address = author_token.functions.owner().call()
        print(f"\n合约所有者地址: {owner_address}")
        
        authors_info = []
        for address in all_addresses:
            try:
                author_info = author_token.functions.getAuthorInfo(address).call()
                if author_info[3]:  # isRegistered
                    # 获取引用网络信息
                    direct_citers = citation_network.functions.getDirectCiters(address).call()
                    lineage = citation_network.functions.getAuthorLineage(address).call()
                    
                    author_data = {
                        'address': author_info[0],
                        'citation_count': author_info[1],
                        'pagerank_score': author_info[2],
                        'is_registered': author_info[3],
                        'direct_citers_count': len(direct_citers),
                        'lineage_size': len(lineage),
                        'is_owner': address.lower() == owner_address.lower()
                    }
                    authors_info.append(author_data)
                    
                    print(f"\n作者 {address}:")
                    print(f"被引用次数: {author_data['citation_count']}")
                    print(f"PageRank得分: {author_data['pagerank_score']}")
                    print(f"直接引用者数量: {author_data['direct_citers_count']}")
                    print(f"引用家族大小: {author_data['lineage_size']}")
                    if author_data['is_owner']:
                        print("(合约所有者)")
            except Exception as e:
                print(f"获取作者 {address} 信息时出错: {str(e)}")
                continue
        
        if not authors_info:
            print("\n未找到任何已注册的作者")
        else:
            print(f"\n总共找到 {len(authors_info)} 位已注册作者")
            
            # 按 PageRank 得分排序
            authors_info.sort(key=lambda x: x['pagerank_score'], reverse=True)
            print("\n作者排名（按 PageRank 得分）:")
            for i, author in enumerate(authors_info, 1):
                print(f"{i}. 地址: {author['address']}")
                print(f"   PageRank得分: {author['pagerank_score']}")
                print(f"   被引用次数: {author['citation_count']}")
                print(f"   直接引用者数量: {author['direct_citers_count']}")
                print(f"   引用家族大小: {author['lineage_size']}")
        
        return authors_info
    except Exception as e:
        print(f"获取所有作者信息时出错: {str(e)}")
        return None

# 主函数
def main():
    print("学术引用系统交互脚本")
    print("====================")
    print(f"当前已注册作者数量: {len(registered_authors)}")
    print("1. 注册新作者")
    print("2. 添加引用")
    print("3. 查询作者信息")
    print("4. 查询引用家族")
    print("5. 查看作者分配份额")
    print("6. 提取收益")
    print("7. 身份管理")
    print("8. 引用验证")
    print("9. 查看完整引用信息")
    print("10. 查看所有作者信息")
    print("11. 更新 PageRank 得分")
    print("0. 退出")
    
    choice = input("请选择操作: ")
    
    if choice == '1':
        print("\n可用选项：")
        print("1. 使用测试账户 #0（已有 10000 ETH）")
        print("2. 创建新账户（将自动获得 1 ETH）")
        sub_choice = input("请选择（1/2）: ")
        
        if sub_choice == '1':
            private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        elif sub_choice == '2':
            private_key = get_account()
        else:
            print("无效选择")
            return
            
        register_author(private_key)
    
    elif choice == '2':
        print("\n可用测试账户地址：")
        print("账户 #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
        print("账户 #1: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
        print("账户 #2: 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC")
        private_key = input("请输入引用者私钥: ")
        cited_address = input("请输入被引用者地址: ")
        paper_hash = input("请输入论文哈希 (例如: ipfs://paper/123): ")
        add_citation(private_key, cited_address, paper_hash)
    
    elif choice == '3':
        author_address = input("请输入作者地址: ")
        get_author_info(author_address)
    
    elif choice == '4':
        author_address = input("请输入作者地址: ")
        get_author_lineage(author_address)
    
    elif choice == '5':
        distribution_id = int(input("请输入分配期ID: "))
        author_address = input("请输入作者地址: ")
        get_author_share(distribution_id, author_address)
    
    elif choice == '6':
        private_key = input("请输入作者私钥: ")
        distribution_id = int(input("请输入分配期ID: "))
        withdraw_share(private_key, distribution_id)
    
    elif choice == '7':
        print("\n身份管理选项：")
        print("1. 验证身份")
        print("2. 更新身份信息")
        print("3. 撤销身份")
        sub_choice = input("请选择（1-3）: ")
        
        if sub_choice == '1':
            private_key = input("请输入管理员私钥: ")
            author_address = input("请输入作者地址: ")
            verify_identity(private_key, author_address)
        elif sub_choice == '2':
            private_key = input("请输入管理员私钥: ")
            author_address = input("请输入作者地址: ")
            new_public_key_hash = input("请输入新的公钥哈希: ")
            metadata_uri = input("请输入新的元数据URI: ")
            is_revoked = input("是否撤销身份 (y/n): ").lower() == 'y'
            update_identity(private_key, author_address, new_public_key_hash, metadata_uri, is_revoked)
        elif sub_choice == '3':
            private_key = input("请输入管理员私钥: ")
            author_address = input("请输入作者地址: ")
            revoke_identity(private_key, author_address)
        else:
            print("无效选择")
    
    elif choice == '8':
        private_key = input("请输入管理员私钥: ")
        citation_id = input("请输入引用ID: ")
        proof = input("请输入Merkle证明 (以空格分隔的字节数组): ").split()
        verify_citation(private_key, citation_id, proof)
    
    elif choice == '9':
        author_address = input("请输入作者地址: ")
        get_complete_citation_info(author_address)
    
    elif choice == '10':
        get_all_authors_info()
    
    elif choice == '11':
        print("\n更新 PageRank 得分")
        print("注意：只有已注册的作者可以更新 PageRank 得分")
        private_key = input("请输入作者私钥: ")
        account = Account.from_key(private_key)
        author_token = load_contract('AuthorToken')
        
        if not author_token:
            print("错误：无法加载合约")
            return
            
        try:
            # 检查是否是已注册作者
            author_info = author_token.functions.getAuthorInfo(account.address).call()
            if not author_info[3]:  # isRegistered
                print("错误：只有已注册的作者可以更新 PageRank 得分")
                return
                
            nonce = w3.eth.get_transaction_count(account.address)
            tx = author_token.functions.updatePageRanks(
                10,  # iterations: 迭代次数
                85   # dampingFactor: 阻尼系数（0.85 * 100）
            ).build_transaction({
                'from': account.address,
                'nonce': nonce,
                'gas': 5000000,  # 需要更多 gas
                'gasPrice': w3.eth.gas_price
            })
            
            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            if receipt.status == 1:
                print("PageRank 得分更新成功")
                print(f"交易哈希: {tx_hash.hex()}")
                
                # 显示更新后的 PageRank 得分
                print("\n更新后的 PageRank 得分:")
                authors_info = get_all_authors_info()
                if authors_info:
                    # 按 PageRank 得分排序
                    authors_info.sort(key=lambda x: x['pagerank_score'], reverse=True)
                    for i, author in enumerate(authors_info, 1):
                        print(f"{i}. 地址: {author['address']}")
                        print(f"   PageRank得分: {author['pagerank_score']}")
            else:
                print("PageRank 得分更新失败")
                print(f"交易哈希: {tx_hash.hex()}")
        except Exception as e:
            print(f"更新 PageRank 得分时出错: {str(e)}")
    
    elif choice == '0':
        print("退出程序")
        return
    
    else:
        print("无效选择")
    
    # 递归调用主函数，实现循环菜单
    main()

if __name__ == "__main__":
    main()