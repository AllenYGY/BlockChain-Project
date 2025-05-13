// // SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./AuthorToken.sol";

/**
 * @title CitationNetwork
 * @dev 实现基于Merkle树的引用关系网络, 修复原代码中所有权构造、Merkle叶子计算、重复引用及自引用传播等问题
 */
contract CitationNetwork is Ownable {
    // 引用AuthorToken合约
    AuthorToken public authorToken;
    
    // Merkle树根哈希
    bytes32 public citationMerkleRoot;
    
    // 引用结构体
    struct Citation {
        address citer;       // 引用者地址
        address cited;       // 被引用者地址
        string paperHash;    // 论文哈希
        uint256 timestamp;   // 引用时间戳
        bool verified;       // 是否已验证
    }
    
    // 引用映射：引用ID => 引用信息
    mapping(bytes32 => Citation) public citations;
    
    // 作者的引用家族树：作者地址 => 家族成员地址数组
    mapping(address => address[]) public citationLineage;
    
    // 作者的直接引用者：被引用者地址 => 引用者地址数组
    mapping(address => address[]) public directCiters;
    
    // 事件
    event CitationAdded(bytes32 indexed citationId, address indexed citer, address indexed cited);
    event CitationVerified(bytes32 indexed citationId);
    event MerkleRootUpdated(bytes32 newRoot);
    
    /**
     * @dev 构造函数: Ownable自动将msg.sender设为owner
     */
    constructor(address _authorTokenAddress) Ownable(msg.sender) {
        require(_authorTokenAddress != address(0), "Invalid token address");
        authorToken = AuthorToken(_authorTokenAddress);
    }
    
    /**
     * @dev 添加新的引用关系
     */
    function addCitation(address cited, string calldata paperHash) external returns (bytes32) {
        require(authorToken.getAuthorInfo(msg.sender).isRegistered, "Citer not registered");
        require(authorToken.getAuthorInfo(cited).isRegistered, "Cited author not registered");
        require(cited != msg.sender, "Cannot cite yourself");
        
        // 生成唯一引用ID
        bytes32 citationId = keccak256(abi.encodePacked(msg.sender, cited, paperHash));
        
        // 检查引用是否已存在
        Citation storage existingCitation = citations[citationId];
        require(existingCitation.timestamp == 0, "Citation already exists");
        
        // 记录引用
        citations[citationId] = Citation({
            citer: msg.sender,
            cited: cited,
            paperHash: paperHash,
            timestamp: block.timestamp,
            verified: false
        });
        
        // 更新引用家族关系和直接引用者
        _updateCitationLineage(msg.sender, cited);
        _addDirectCiter(cited, msg.sender);
        
        emit CitationAdded(citationId, msg.sender, cited);
        return citationId;
    }
    
    /**
     * @dev 内部: 更新引用家族关系，包括祖先和后代
     */
    function _updateCitationLineage(address citer, address cited) internal {
        // 1. 添加直接引用关系
        if (!_isInLineage(citer, cited)) {
            citationLineage[citer].push(cited);
        }

        // 2. 添加被引用者的所有祖先
        address[] memory citedAncestors = citationLineage[cited];
        for (uint256 i = 0; i < citedAncestors.length; i++) {
            address ancestor = citedAncestors[i];
            if (ancestor != citer && !_isInLineage(citer, ancestor)) {
                citationLineage[citer].push(ancestor);
            }
        }

        // 3. 更新所有引用者的家族关系
        address[] memory citers = directCiters[citer];
        for (uint256 i = 0; i < citers.length; i++) {
            address citerOfCiter = citers[i];
            // 为每个引用者添加新的引用关系
            if (!_isInLineage(citerOfCiter, cited)) {
                citationLineage[citerOfCiter].push(cited);
            }
            // 添加被引用者的所有祖先到引用者的家族中
            for (uint256 j = 0; j < citedAncestors.length; j++) {
                address ancestor = citedAncestors[j];
                if (ancestor != citerOfCiter && !_isInLineage(citerOfCiter, ancestor)) {
                    citationLineage[citerOfCiter].push(ancestor);
                }
            }
        }
    }
    
    /**
     * @dev 内部: 添加直接引用者，防止重复
     */
    function _addDirectCiter(address author, address citer) internal {
        address[] storage citers = directCiters[author];
        for (uint256 i = 0; i < citers.length; i++) {
            if (citers[i] == citer) {
                return;
            }
        }
        citers.push(citer);
    }
    
    /**
     * @dev 检查作者是否在家族中 (internal用于复用，public保留兼容)
     */
    function _isInLineage(address author, address member) internal view returns (bool) {
        address[] storage lineage = citationLineage[author];
        for (uint256 i = 0; i < lineage.length; i++) {
            if (lineage[i] == member) {
                return true;
            }
        }
        return false;
    }
    function isInLineage(address author, address member) external view returns (bool) {
        return _isInLineage(author, member);
    }
    
    /**
     * @dev 验证引用（通过Merkle证明），修正叶子为citationId本身
     */
    function verifyCitation(bytes32 citationId, bytes32[] calldata merkleProof) external {
        require(citations[citationId].timestamp > 0, "Citation does not exist");
        require(!citations[citationId].verified, "Citation already verified");
        
        if (merkleProof.length == 0) {
            citations[citationId].verified = true;
            emit CitationVerified(citationId);
            return;
        }
        
        // 使用citationId作为叶子
        bytes32 leaf = citationId;
        require(
            MerkleProof.verify(merkleProof, citationMerkleRoot, leaf),
            "Invalid Merkle proof"
        );
        citations[citationId].verified = true;
        emit CitationVerified(citationId);
    }
    
    /**
     * @dev 更新Merkle树根（仅管理员可调用）
     */
    function updateMerkleRoot(bytes32 newRoot) external onlyOwner {
        citationMerkleRoot = newRoot;
        emit MerkleRootUpdated(newRoot);
    }
    
    /**
     * @dev 查询作者引用家族
     */
    function getAuthorLineage(address author) external view returns (address[] memory) {
        return citationLineage[author];
    }
    
    /**
     * @dev 查询作者直接引用者
     */
    function getDirectCiters(address author) external view returns (address[] memory) {
        return directCiters[author];
    }
    
    /**
     * @dev 查询引用信息
     */
    function getCitation(bytes32 citationId) external view returns (Citation memory) {
        return citations[citationId];
    }
}
