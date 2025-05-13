from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
import json

class AuthSystem:
    def __init__(self):
        self._authors = {}  # public_key -> author_id mapping
        
    def generate_key_pair(self):
        """生成RSA密钥对"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        # 序列化私钥
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # 序列化公钥
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return {
            'private_key': base64.b64encode(private_pem).decode('utf-8'),
            'public_key': base64.b64encode(public_pem).decode('utf-8')
        }
    
    def sign_message(self, private_key_pem: str, message: str) -> str:
        """使用私钥签名消息"""
        private_key = serialization.load_pem_private_key(
            base64.b64decode(private_key_pem),
            password=None,
            backend=default_backend()
        )
        
        signature = private_key.sign(
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_signature(self, public_key_pem: str, message: str, signature: str) -> bool:
        """验证签名"""
        try:
            public_key = serialization.load_pem_public_key(
                base64.b64decode(public_key_pem),
                backend=default_backend()
            )
            
            public_key.verify(
                base64.b64decode(signature),
                message.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
    
    def register_author(self, author_id: str, public_key: str):
        """注册作者公钥"""
        self._authors[public_key] = author_id
    
    def get_author_id(self, public_key: str) -> str:
        """通过公钥获取作者ID"""
        return self._authors.get(public_key)
    
    def verify_author(self, public_key: str, message: str, signature: str) -> bool:
        """验证作者身份"""
        if public_key not in self._authors:
            return False
        return self.verify_signature(public_key, message, signature) 