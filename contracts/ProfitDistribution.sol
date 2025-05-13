// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./AuthorToken.sol";
import "./CitationNetwork.sol";

/**
 * @title ProfitDistribution
 * @dev 实现基于PageRank和Shapley值的利润分配机制
 * 项目产生的收益进入智能合约金库，由所有参与作者按边际贡献分配
 */
contract ProfitDistribution is Ownable, ReentrancyGuard {
    // 引用其他合约
    AuthorToken public authorToken;
    CitationNetwork public citationNetwork;
    
    // 金库余额
    uint256 public treasuryBalance;
    
    // 最后一次分配时间
    uint256 public lastDistributionTime;
    
    // 分配周期（默认30天）
    uint256 public distributionPeriod = 30 days;
    
    // 作者分配比例（总和为100）
    struct AuthorShare {
        address author;
        uint256 sharePercentage; // 以100为基数的百分比
        uint256 amount;          // 实际分配金额
        bool hasWithdrawn;
    }
    
    // 当前分配期的作者份额
    mapping(uint256 => mapping(address => AuthorShare)) public authorShares; // 分配期ID => 作者地址 => 份额
    
    // 分配期ID
    uint256 public currentDistributionId;
    
    // 事件
    event FundsReceived(address indexed from, uint256 amount);
    event ProfitDistributed(uint256 indexed distributionId, uint256 totalAmount);
    event AuthorShareCalculated(uint256 indexed distributionId, address indexed author, uint256 sharePercentage);
    event AuthorWithdrawal(uint256 indexed distributionId, address indexed author, uint256 amount);
    
    constructor(address _authorTokenAddress, address _citationNetworkAddress) Ownable(msg.sender) {
        authorToken = AuthorToken(_authorTokenAddress);
        citationNetwork = CitationNetwork(_citationNetworkAddress);
        lastDistributionTime = block.timestamp;
        currentDistributionId = 1;
    }
    
    /**
     * @dev 接收资金
     */
    receive() external payable {
        treasuryBalance += msg.value;
        emit FundsReceived(msg.sender, msg.value);
    }
    
    /**
     * @dev 计算并分配利润（仅管理员可调用）
     */
    function distributeProfits() external onlyOwner {
        require(block.timestamp >= lastDistributionTime + distributionPeriod, "Distribution period not reached");
        
        uint256 authorCount = authorToken.getAuthorCount();
        require(authorCount > 0, "No authors registered");
        
        // 计算每位作者的份额
        calculateAuthorShares();
        
        // 更新分配时间
        lastDistributionTime = block.timestamp;
        
        emit ProfitDistributed(currentDistributionId, treasuryBalance);
        
        // 增加分配期ID
        currentDistributionId++;
    }
    
    /**
     * @dev 计算每位作者的份额
     * 使用PageRank得分和Shapley值的简化版本
     */
    function calculateAuthorShares() internal {
        uint256 totalScore = 0;
        uint256 authorCount = authorToken.getAuthorCount();
        address[] memory authors = new address[](authorCount);
        uint256[] memory scores = new uint256[](authorCount);
        
        // 获取当前分配期的总金额
        uint256 totalAmount = getPeriodTotalAmount();
        
        // 获取所有作者地址和PageRank得分
        for (uint256 i = 0; i < authorCount; i++) {
            address author = authorToken.authorAddresses(i);
            authors[i] = author;
            
            // 获取作者的PageRank得分
            (, , uint256 pageRankScore, ) = authorToken.authors(author);
            
            // 计算作者的Shapley值（简化版）
            uint256 lineageSize = citationNetwork.getAuthorLineage(author).length;
            uint256 directCitersCount = citationNetwork.getDirectCiters(author).length;
            
            // 计算综合得分：PageRank得分 * 0.7 + 引用家族大小 * 0.2 + 直接引用者数量 * 0.1
            uint256 score = (pageRankScore * 7 + lineageSize * 2 + directCitersCount * 1) / 10;
            scores[i] = score;
            totalScore += score;
        }
        
        // 计算每位作者的份额百分比
        if (totalScore > 0) {
            // 有得分时的正常分配
            uint256 totalPercentage = 0;
            
            // 先计算前n-1个作者的份额
            for (uint256 i = 0; i < authorCount - 1; i++) {
                address author = authors[i];
                uint256 sharePercentage = scores[i] * 100 / totalScore;
                totalPercentage += sharePercentage;
                uint256 authorAmount = totalAmount * sharePercentage / 100;
                
                authorShares[currentDistributionId][author] = AuthorShare({
                    author: author,
                    sharePercentage: sharePercentage,
                    amount: authorAmount,
                    hasWithdrawn: false
                });
                
                emit AuthorShareCalculated(currentDistributionId, author, sharePercentage);
            }
            
            // 最后一个作者获得剩余份额
            if (authorCount > 0) {
                address lastAuthor = authors[authorCount - 1];
                uint256 lastSharePercentage = 100 - totalPercentage;
                uint256 lastAuthorAmount = totalAmount * lastSharePercentage / 100;
                
                authorShares[currentDistributionId][lastAuthor] = AuthorShare({
                    author: lastAuthor,
                    sharePercentage: lastSharePercentage,
                    amount: lastAuthorAmount,
                    hasWithdrawn: false
                });
                
                emit AuthorShareCalculated(currentDistributionId, lastAuthor, lastSharePercentage);
            }
        } else {
            // 零得分时的平均分配
            uint256 equalShare = 100 / authorCount;
            uint256 remainingShare = 100 - (equalShare * authorCount);
            
            // 为每个作者分配相等份额
            for (uint256 i = 0; i < authorCount; i++) {
                address author = authors[i];
                uint256 sharePercentage = equalShare + (i == authorCount - 1 ? remainingShare : 0);
                uint256 authorAmount = totalAmount * sharePercentage / 100;
                
                authorShares[currentDistributionId][author] = AuthorShare({
                    author: author,
                    sharePercentage: sharePercentage,
                    amount: authorAmount,
                    hasWithdrawn: false
                });
                
                emit AuthorShareCalculated(currentDistributionId, author, sharePercentage);
            }
        }
    }
    
    /**
     * @dev 作者提取收益
     * @param distributionId 分配期ID
     */
    function withdrawShare(uint256 distributionId) external nonReentrant {
        require(distributionId < currentDistributionId, "Distribution not finalized");
        
        AuthorShare storage share = authorShares[distributionId][msg.sender];
        require(share.sharePercentage > 0, "No share for this author");
        require(!share.hasWithdrawn, "Already withdrawn");
        
        // 计算作者应得金额
        uint256 totalAmount = getPeriodTotalAmount();
        uint256 authorAmount = totalAmount * share.sharePercentage / 100;
        
        // 只有在有余额时才进行转账
        if (authorAmount > 0) {
            require(address(this).balance >= authorAmount, "Insufficient contract balance");
            payable(msg.sender).transfer(authorAmount);
        }
        
        // 标记为已提取
        share.hasWithdrawn = true;
        
        emit AuthorWithdrawal(distributionId, msg.sender, authorAmount);
    }
    
    /**
     * @dev 获取指定分配期的总金额
     * @return 总金额
     */
    function getPeriodTotalAmount() public view returns (uint256) {
        // 如果是第一次分配，返回当前金库余额
        if (currentDistributionId == 1) {
            return treasuryBalance;
        }
        // 否则平分总金库余额
        return treasuryBalance / (currentDistributionId - 1);
    }
    
    /**
     * @dev 获取作者在指定分配期的份额
     * @param distributionId 分配期ID
     * @param author 作者地址
     * @return 作者份额信息
     */
    function getAuthorShare(uint256 distributionId, address author) external view returns (AuthorShare memory) {
        return authorShares[distributionId][author];
    }
    
    /**
     * @dev 设置分配周期（仅管理员可调用）
     * @param newPeriod 新的分配周期（秒）
     */
    function setDistributionPeriod(uint256 newPeriod) external onlyOwner {
        require(newPeriod > 0, "Period must be greater than 0");
        distributionPeriod = newPeriod;
    }
}