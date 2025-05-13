// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title AuthorToken
 * @dev 实现基于学术引用的作者身份币系统
 * 使用PageRank算法计算作者在引用网络中的影响力
 */
contract AuthorToken is ERC20, Ownable {
    // 作者结构体
    struct Author {
        address wallet;          // 作者钱包地址
        uint256 citationCount;   // 被引用次数
        uint256 pageRankScore;   // PageRank得分
        bool isRegistered;       // 是否已注册
    }
    
    // 引用结构体
    struct Citation {
        address citer;      // 引用者地址
        address cited;      // 被引用者地址
        uint256 timestamp;  // 引用时间戳
        bool isValid;       // 是否有效
    }
    
    // 作者映射：地址 => 作者信息
    mapping(address => Author) public authors;
    
    // 作者地址数组，用于PageRank计算
    address[] public authorAddresses;
    
    // 引用映射：引用ID => 引用信息
    mapping(bytes32 => Citation) public citations;
    
    // 引用关系映射：作者地址 => 引用过的作者地址数组
    mapping(address => address[]) public citationGraph;
    
    // 引用曲线参数
    uint256 public baseMintRate = 10;      // 基础铸币率
    uint256 public decayFactor = 5;        // 衰减因子
    uint256 public totalCitations = 0;     // 总引用数
    
    // 事件
    event AuthorRegistered(address indexed author);
    event CitationAdded(address indexed citer, address indexed cited, bytes32 citationId);
    event PageRankUpdated(address indexed author, uint256 newScore);
    event TokensMinted(address indexed author, uint256 amount);
    
    constructor() ERC20("AuthorIdentityToken", "AIT") Ownable(msg.sender) {}
    
    /**
     * @dev 注册新作者
     */
    function registerAuthor() external {
        require(!authors[msg.sender].isRegistered, "Author already registered");
        
        authors[msg.sender] = Author({
            wallet: msg.sender,
            citationCount: 0,
            pageRankScore: 0,
            isRegistered: true
        });
        
        authorAddresses.push(msg.sender);
        
        // 初始铸造少量代币
        _mint(msg.sender, 10 * 10**decimals());
        
        emit AuthorRegistered(msg.sender);
    }
    
    /**
     * @dev 添加引用关系
     * @param cited 被引用者地址
     */
    function addCitation(address cited) external {
        require(authors[msg.sender].isRegistered, "Citer not registered");
        require(authors[cited].isRegistered, "Cited author not registered");
        require(cited != msg.sender, "Cannot cite yourself");
        
        // 生成唯一引用ID
        bytes32 citationId = keccak256(abi.encodePacked(msg.sender, cited, block.timestamp));
        require(!citations[citationId].isValid, "Citation already exists");
        
        // 记录引用
        citations[citationId] = Citation({
            citer: msg.sender,
            cited: cited,
            timestamp: block.timestamp,
            isValid: true
        });
        
        // 更新引用图
        citationGraph[msg.sender].push(cited);
        
        // 更新被引用次数
        authors[cited].citationCount++;
        totalCitations++;
        
        // 计算并铸造代币
        uint256 tokensToMint = calculateCitationReward(cited);
        _mint(cited, tokensToMint);
        
        emit CitationAdded(msg.sender, cited, citationId);
        emit TokensMinted(cited, tokensToMint);
    }
    
    /**
     * @dev 计算引用奖励代币数量
     * @param author 作者地址
     * @return 奖励代币数量
     */
    function calculateCitationReward(address author) public view returns (uint256) {
        uint256 citationCount = authors[author].citationCount;
        
        // 引用曲线：随着引用次数增加，每次新增引用的奖励递减
        uint256 reward = baseMintRate * 10**decimals() / (1 + (citationCount / decayFactor));
        
        return reward;
    }
    
    /**
     * @dev 更新所有作者的PageRank得分
     * @param iterations PageRank迭代次数
     * @param dampingFactor 阻尼系数（通常为0.85）
     */
    function updatePageRanks(uint8 iterations, uint256 dampingFactor) external {
        require(authors[msg.sender].isRegistered, "Caller must be a registered author");
        require(iterations > 0, "Iterations must be greater than 0");
        require(dampingFactor <= 100, "Damping factor must be <= 100");
        
        uint256 authorCount = authorAddresses.length;
        require(authorCount > 0, "No authors registered");
        
        // 初始化PageRank得分
        uint256[] memory scores = new uint256[](authorCount);
        uint256[] memory newScores = new uint256[](authorCount);
        
        // 初始得分均为1
        for (uint256 i = 0; i < authorCount; i++) {
            scores[i] = 1 * 10**18; // 使用高精度
        }
        
        // PageRank迭代计算
        for (uint8 iter = 0; iter < iterations; iter++) {
            // 重置新得分
            for (uint256 i = 0; i < authorCount; i++) {
                newScores[i] = (100 - dampingFactor) * 10**18 / 100; // (1-d)
            }
            
            // 计算每个作者的新得分
            for (uint256 i = 0; i < authorCount; i++) {
                address author = authorAddresses[i];
                address[] memory citedAuthors = citationGraph[author];
                
                if (citedAuthors.length > 0) {
                    uint256 contributionPerCitation = scores[i] / citedAuthors.length;
                    
                    // 分配得分给被引用者
                    for (uint256 j = 0; j < citedAuthors.length; j++) {
                        address cited = citedAuthors[j];
                        
                        // 查找被引用者的索引
                        for (uint256 k = 0; k < authorCount; k++) {
                            if (authorAddresses[k] == cited) {
                                newScores[k] += dampingFactor * contributionPerCitation / 100;
                                break;
                            }
                        }
                    }
                }
            }
            
            // 更新得分
            for (uint256 i = 0; i < authorCount; i++) {
                scores[i] = newScores[i];
            }
        }
        
        // 更新合约状态
        for (uint256 i = 0; i < authorCount; i++) {
            address author = authorAddresses[i];
            authors[author].pageRankScore = scores[i];
            
            emit PageRankUpdated(author, scores[i]);
        }
    }
    
    /**
     * @dev 获取作者信息
     * @param author 作者地址
     * @return 作者信息
     */
    function getAuthorInfo(address author) external view returns (Author memory) {
        return authors[author];
    }
    
    /**
     * @dev 获取作者数量
     * @return 作者数量
     */
    function getAuthorCount() external view returns (uint256) {
        return authorAddresses.length;
    }
}