// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

/**
 * @title IdentityManagement
 * @dev 实现基于椭圆曲线（ECC）密钥对的作者身份认证与签名验证
 */
contract IdentityManagement is Ownable {
    using ECDSA for bytes32;
    using MessageHashUtils for bytes32;
    
    // 作者身份结构体
    struct AuthorIdentity {
        address walletAddress;     // 钱包地址
        bytes32 publicKeyHash;     // 公钥哈希
        string metadataURI;        // 元数据URI（可存储IPFS上的作者信息）
        bool isVerified;           // 是否已验证
        uint256 registrationTime;  // 注册时间
    }
    
    // 作者身份映射：地址 => 身份信息
    mapping(address => AuthorIdentity) public authorIdentities;
    
    // 公钥哈希映射：公钥哈希 => 地址
    mapping(bytes32 => address) public publicKeyToAddress;
    
    // 事件
    event IdentityRegistered(address indexed author, bytes32 publicKeyHash);
    event IdentityVerified(address indexed author);
    event MetadataUpdated(address indexed author, string metadataURI);
    event SignatureVerified(address indexed author, bytes32 messageHash, bool success);
    
    constructor() Ownable(msg.sender) {}
    
    /**
     * @dev 注册作者身份
     * @param publicKeyHash 公钥哈希
     * @param metadataURI 元数据URI
     */
    function registerIdentity(bytes32 publicKeyHash, string calldata metadataURI) external {
        require(authorIdentities[msg.sender].registrationTime == 0, "Identity already registered");
        require(publicKeyToAddress[publicKeyHash] == address(0), "Public key already registered");
        
        authorIdentities[msg.sender] = AuthorIdentity({
            walletAddress: msg.sender,
            publicKeyHash: publicKeyHash,
            metadataURI: metadataURI,
            isVerified: false,
            registrationTime: block.timestamp
        });
        
        publicKeyToAddress[publicKeyHash] = msg.sender;
        
        emit IdentityRegistered(msg.sender, publicKeyHash);
    }
    
    /**
     * @dev 验证作者身份（仅管理员可调用）
     * @param author 作者地址
     */
    function verifyIdentity(address author) external onlyOwner {
        require(authorIdentities[author].registrationTime > 0, "Identity not registered");
        require(!authorIdentities[author].isVerified, "Identity already verified");
        
        authorIdentities[author].isVerified = true;
        
        emit IdentityVerified(author);
    }
    
    /**
     * @dev 更新元数据URI
     * @param metadataURI 新的元数据URI
     */
    function updateMetadata(string calldata metadataURI) external {
        require(authorIdentities[msg.sender].registrationTime > 0, "Identity not registered");
        
        authorIdentities[msg.sender].metadataURI = metadataURI;
        
        emit MetadataUpdated(msg.sender, metadataURI);
    }
    
    /**
     * @dev 验证签名
     * @param messageHash 消息哈希
     * @param signature 签名
     * @return 签名是否有效
     */
    function verifySignature(bytes32 messageHash, bytes calldata signature) external view returns (bool) {
        address signer = ECDSA.recover(MessageHashUtils.toEthSignedMessageHash(messageHash), signature);
        bool isValid = (signer == msg.sender && authorIdentities[signer].isVerified);
        
        return isValid;
    }
    
    /**
     * @dev 获取作者身份信息
     * @param author 作者地址
     * @return 身份信息
     */
    function getIdentity(address author) external view returns (AuthorIdentity memory) {
        return authorIdentities[author];
    }
    
    /**
     * @dev 检查地址是否为已验证的作者
     * @param author 作者地址
     * @return 是否为已验证的作者
     */
    function isVerifiedAuthor(address author) external view returns (bool) {
        return authorIdentities[author].isVerified;
    }
    
    /**
     * @dev 设置或更新作者身份（仅管理员可调用）
     * @param author 作者地址
     * @param publicKeyHash 公钥哈希
     * @param metadataURI 元数据URI
     * @param isRevoked 是否撤销身份
     */
    function setIdentity(
        address author,
        bytes32 publicKeyHash,
        string calldata metadataURI,
        bool isRevoked
    ) external onlyOwner {
        require(author != address(0), "Invalid author address");
        
        if (authorIdentities[author].registrationTime == 0) {
            // 新注册
            require(publicKeyToAddress[publicKeyHash] == address(0), "Public key already registered");
            publicKeyToAddress[publicKeyHash] = author;
        } else {
            // 更新现有身份
            if (publicKeyHash != authorIdentities[author].publicKeyHash) {
                require(publicKeyToAddress[publicKeyHash] == address(0), "Public key already registered");
                publicKeyToAddress[authorIdentities[author].publicKeyHash] = address(0);
                publicKeyToAddress[publicKeyHash] = author;
            }
        }
        
        authorIdentities[author] = AuthorIdentity({
            walletAddress: author,
            publicKeyHash: publicKeyHash,
            metadataURI: metadataURI,
            isVerified: !isRevoked && authorIdentities[author].isVerified,
            registrationTime: authorIdentities[author].registrationTime == 0 ? block.timestamp : authorIdentities[author].registrationTime
        });
        
        if (authorIdentities[author].registrationTime == block.timestamp) {
            emit IdentityRegistered(author, publicKeyHash);
        } else {
            emit MetadataUpdated(author, metadataURI);
        }
    }
    
    /**
     * @dev 撤销作者身份（仅管理员可调用）
     * @param author 作者地址
     */
    function revokeIdentity(address author) external onlyOwner {
        require(authorIdentities[author].registrationTime > 0, "Identity not registered");
        require(authorIdentities[author].isVerified, "Identity not verified");
        
        authorIdentities[author].isVerified = false;
        emit IdentityVerified(author);
    }
}