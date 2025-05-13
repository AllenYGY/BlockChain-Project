import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8090/"

class CitationSystemTest:
    def __init__(self):
        self.author1_keys = None
        self.author2_keys = None
        self.author1_id = None
        self.author2_id = None
        self.paper1_id = None
        self.paper2_id = None
        self.paper3_id = None
        self.citation1_id = None
        self.citation2_id = None

    def test_generate_keys(self) -> Dict[str, str]:
        """测试生成密钥对"""
        print("\n=== Testing Key Generation ===")
        response = requests.post(f"{BASE_URL}auth/generate-keys")
        keys = response.json()
        print(f"Generated keys: {json.dumps(keys, indent=2)}")
        return keys

    def test_sign_message(self, private_key: str) -> str:
        """测试签名生成"""
        print("\n=== Testing Message Signing ===")
        response = requests.post(
            f"{BASE_URL}auth/sign",
            params={
                "private_key": private_key,
                "message": "verify"
            }
        )
        signature = response.json()["signature"]
        print(f"Generated signature: {signature[:50]}...")
        return signature

    def test_create_author(self, name: str, public_key: str) -> Dict[str, Any]:
        """测试创建作者"""
        print(f"\n=== Testing Author Creation: {name} ===")
        response = requests.post(
            f"{BASE_URL}authors",
            json={
                "name": name,
                "public_key": public_key
            }
        )
        author = response.json()
        print(f"Created author: {json.dumps(author, indent=2)}")
        return author

    def test_get_author(self, author_id: str) -> Dict[str, Any]:
        """测试获取作者信息"""
        print(f"\n=== Testing Get Author: {author_id} ===")
        response = requests.get(f"{BASE_URL}authors/{author_id}")
        author = response.json()
        print(f"Author info: {json.dumps(author, indent=2)}")
        return author

    def test_create_paper(self, title: str, authors: list, public_key: str, signature: str) -> Dict[str, Any]:
        """测试创建论文"""
        print(f"\n=== Testing Paper Creation: {title} ===")
        response = requests.post(
            f"{BASE_URL}papers",
            headers={
                "public-key": public_key,
                "signature": signature
            },
            json={
                "title": title,
                "authors": authors,
                "citations": []
            }
        )
        paper = response.json()
        print(f"Created paper: {json.dumps(paper, indent=2)}")
        return paper

    def test_get_paper(self, paper_id: str) -> Dict[str, Any]:
        """测试获取论文信息"""
        print(f"\n=== Testing Get Paper: {paper_id} ===")
        response = requests.get(f"{BASE_URL}papers/{paper_id}")
        paper = response.json()
        print(f"Paper info: {json.dumps(paper, indent=2)}")
        return paper

    def test_create_citation(self, citing_paper_id: str, cited_paper_id: str, public_key: str, signature: str) -> Dict[str, Any]:
        """测试创建引用"""
        print(f"\n=== Testing Citation Creation ===")
        print(f"Citing paper: {citing_paper_id}")
        print(f"Cited paper: {cited_paper_id}")
        response = requests.post(
            f"{BASE_URL}citations",
            headers={
                "public-key": public_key,
                "signature": signature
            },
            json={
                "citing_paper_id": citing_paper_id,
                "cited_paper_id": cited_paper_id,
                "signature": signature
            }
        )
        citation = response.json()
        print(f"Created citation: {json.dumps(citation, indent=2)}")
        return citation

    def test_get_balance(self, author_id: str) -> Dict[str, float]:
        """测试获取作者余额"""
        print(f"\n=== Testing Get Balance: {author_id} ===")
        response = requests.get(f"{BASE_URL}authors/{author_id}/balance")
        balance = response.json()
        print(f"Author balance: {json.dumps(balance, indent=2)}")
        return balance

    def test_burn_tokens(self, author_id: str, amount: float, public_key: str, signature: str) -> Dict[str, str]:
        """测试销毁代币"""
        print(f"\n=== Testing Token Burn: {author_id} ===")
        response = requests.post(
            f"{BASE_URL}authors/{author_id}/burn",
            headers={
                "public-key": public_key,
                "signature": signature
            },
            json={
                "amount": amount,
                "reason": "Testing token burn",
                "signature": signature
            }
        )
        result = response.json()
        print(f"Burn result: {json.dumps(result, indent=2)}")
        return result

    def test_get_transactions(self, author_id: str) -> list:
        """测试获取交易历史"""
        print(f"\n=== Testing Get Transactions: {author_id} ===")
        response = requests.get(f"{BASE_URL}authors/{author_id}/transactions")
        transactions = response.json()
        print(f"Transaction history: {json.dumps(transactions, indent=2)}")
        return transactions

    def test_get_network_stats(self) -> Dict[str, Any]:
        """测试获取网络统计信息"""
        print("\n=== Testing Network Stats ===")
        response = requests.get(f"{BASE_URL}stats/network")
        stats = response.json()
        print(f"Network stats: {json.dumps(stats, indent=2)}")
        return stats

    def test_get_token_stats(self) -> Dict[str, Any]:
        """测试获取代币统计信息"""
        print("\n=== Testing Token Stats ===")
        response = requests.get(f"{BASE_URL}stats/tokens")
        stats = response.json()
        print(f"Token stats: {json.dumps(stats, indent=2)}")
        return stats

    def run_full_test(self):
        """运行完整测试流程"""
        try:
            # 1. 创建两个作者
            print("\n=== Starting Full Test ===")
            self.author1_keys = self.test_generate_keys()
            self.author2_keys = self.test_generate_keys()
            
            author1 = self.test_create_author("Alice", self.author1_keys["public_key"])
            author2 = self.test_create_author("Bob", self.author2_keys["public_key"])
            self.author1_id = author1["id"]
            self.author2_id = author2["id"]
            
            # 2. 获取作者信息
            self.test_get_author(self.author1_id)
            self.test_get_author(self.author2_id)
            
            # 3. 创建论文
            signature1 = self.test_sign_message(self.author1_keys["private_key"])
            signature2 = self.test_sign_message(self.author2_keys["private_key"])
            
            paper1 = self.test_create_paper("Paper 1 by Alice", [self.author1_id], 
                                          self.author1_keys["public_key"], signature1)
            paper2 = self.test_create_paper("Paper 2 by Bob", [self.author2_id], 
                                          self.author2_keys["public_key"], signature2)
            paper3 = self.test_create_paper("Paper 3 by Alice", [self.author1_id], 
                                          self.author1_keys["public_key"], signature1)
            
            self.paper1_id = paper1["id"]
            self.paper2_id = paper2["id"]
            self.paper3_id = paper3["id"]
            
            # 4. 获取论文信息
            self.test_get_paper(self.paper1_id)
            self.test_get_paper(self.paper2_id)
            self.test_get_paper(self.paper3_id)
            
            # 5. 创建引用关系
            citation1 = self.test_create_citation(self.paper2_id, self.paper1_id, 
                                                self.author2_keys["public_key"], signature2)
            citation2 = self.test_create_citation(self.paper3_id, self.paper2_id, 
                                                self.author1_keys["public_key"], signature1)
            
            self.citation1_id = citation1["id"]
            self.citation2_id = citation2["id"]
            
            # 6. 检查代币余额
            time.sleep(1)  # 等待代币铸造
            self.test_get_balance(self.author1_id)
            self.test_get_balance(self.author2_id)
            
            # 7. 测试代币销毁
            self.test_burn_tokens(self.author1_id, 0.1, 
                                self.author1_keys["public_key"], signature1)
            
            # 8. 检查交易历史
            self.test_get_transactions(self.author1_id)
            self.test_get_transactions(self.author2_id)
            
            # 9. 获取统计信息
            self.test_get_network_stats()
            self.test_get_token_stats()
            
            print("\n=== Full Test Completed Successfully ===")
            
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            if hasattr(e, 'response'):
                print(f"Response status: {e.response.status_code}")
                print(f"Response content: {e.response.content}")

if __name__ == "__main__":
    tester = CitationSystemTest()
    tester.run_full_test() 