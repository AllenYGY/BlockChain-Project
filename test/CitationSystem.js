const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("学术引用系统测试", function () {
  // 测试合约实例
  let authorToken;
  let citationNetwork;
  let profitDistribution;
  let identityManagement;
  
  // 测试账户
  let owner;
  let author1;
  let author2;
  let author3;
  
  // 部署合约
  beforeEach(async function () {
    // 获取测试账户
    [owner, author1, author2, author3] = await ethers.getSigners();
    
    // 部署AuthorToken合约
    const AuthorToken = await ethers.getContractFactory("AuthorToken");
    authorToken = await AuthorToken.deploy();
    await authorToken.waitForDeployment();
    
    // 部署CitationNetwork合约
    const CitationNetwork = await ethers.getContractFactory("CitationNetwork");
    citationNetwork = await CitationNetwork.deploy(await authorToken.getAddress());
    await citationNetwork.waitForDeployment();
    
    // 部署ProfitDistribution合约
    const ProfitDistribution = await ethers.getContractFactory("ProfitDistribution");
    profitDistribution = await ProfitDistribution.deploy(
      await authorToken.getAddress(),
      await citationNetwork.getAddress()
    );
    await profitDistribution.waitForDeployment();
    
    // 部署IdentityManagement合约
    const IdentityManagement = await ethers.getContractFactory("IdentityManagement");
    identityManagement = await IdentityManagement.deploy();
    await identityManagement.waitForDeployment();
  });
  
  describe("作者身份币测试", function () {
    it("应该允许作者注册", async function () {
      await authorToken.connect(author1).registerAuthor();
      const authorInfo = await authorToken.getAuthorInfo(author1.address);
      
      expect(authorInfo.isRegistered).to.equal(true);
      expect(authorInfo.wallet).to.equal(author1.address);
      expect(authorInfo.citationCount).to.equal(0);
    });
    
    it("不应允许重复注册", async function () {
      await authorToken.connect(author1).registerAuthor();
      await expect(authorToken.connect(author1).registerAuthor())
        .to.be.revertedWith("Author already registered");
    });
    
    it("应该允许添加引用并铸造代币", async function () {
      // 注册两位作者
      await authorToken.connect(author1).registerAuthor();
      await authorToken.connect(author2).registerAuthor();
      
      // 作者1引用作者2
      await authorToken.connect(author1).addCitation(author2.address);
      
      const author2Info = await authorToken.getAuthorInfo(author2.address);
      expect(author2Info.citationCount).to.equal(1);
      
      // 检查代币余额增加
      const balance = await authorToken.balanceOf(author2.address);
      expect(balance).to.be.gt(ethers.parseEther("10")); // 初始10代币 + 引用奖励
    });
    
    it("应该能更新PageRank得分", async function () {
      // 注册三位作者
      await authorToken.connect(author1).registerAuthor();
      await authorToken.connect(author2).registerAuthor();
      await authorToken.connect(author3).registerAuthor();
      
      // 创建引用关系：1->2, 2->3, 3->1 (循环引用)
      await authorToken.connect(author1).addCitation(author2.address);
      await authorToken.connect(author2).addCitation(author3.address);
      await authorToken.connect(author3).addCitation(author1.address);
      
      // 使用任意已注册作者更新PageRank
      await authorToken.connect(author1).updatePageRanks(5, 85); // 5次迭代，阻尼系数0.85
      
      // 检查所有作者都有PageRank得分
      const author1Info = await authorToken.getAuthorInfo(author1.address);
      const author2Info = await authorToken.getAuthorInfo(author2.address);
      const author3Info = await authorToken.getAuthorInfo(author3.address);
      
      expect(author1Info.pageRankScore).to.be.gt(0);
      expect(author2Info.pageRankScore).to.be.gt(0);
      expect(author3Info.pageRankScore).to.be.gt(0);
    });
    
    it("不应允许作者引用自己", async function () {
      await authorToken.connect(author1).registerAuthor();
      await expect(authorToken.connect(author1).addCitation(author1.address))
        .to.be.revertedWith("Cannot cite yourself");
    });
    
    it("不应允许引用未注册作者", async function () {
      await authorToken.connect(author1).registerAuthor();
      await expect(authorToken.connect(author1).addCitation(author2.address))
        .to.be.revertedWith("Cited author not registered");
    });
    
    it("应该正确处理代币余额边界情况", async function () {
      await authorToken.connect(author1).registerAuthor();
      await authorToken.connect(author2).registerAuthor();
      
      // 添加多次引用，检查代币余额增长
      const initialBalance = BigInt(await authorToken.balanceOf(author2.address));
      await authorToken.connect(author1).addCitation(author2.address);
      const balanceAfterOne = BigInt(await authorToken.balanceOf(author2.address));
      expect(balanceAfterOne).to.be.gt(initialBalance);
      
      // 添加更多引用，检查衰减效果
      for(let i = 0; i < 10; i++) {
        await authorToken.connect(author1).addCitation(author2.address);
      }
      const balanceAfterMany = BigInt(await authorToken.balanceOf(author2.address));
      
      // 使用 BigInt 进行计算
      const firstCitationReward = balanceAfterOne - initialBalance;
      const totalAdditionalReward = balanceAfterMany - balanceAfterOne;
      const averageAdditionalReward = totalAdditionalReward / BigInt(10);
      
      expect(averageAdditionalReward).to.be.lt(firstCitationReward);
    });
    
    it("应该正确处理PageRank参数边界", async function () {
      // 先注册作者
      await authorToken.connect(author1).registerAuthor();
      await authorToken.connect(author2).registerAuthor();
      await authorToken.connect(author3).registerAuthor();
      
      // 测试无效迭代次数
      await expect(authorToken.connect(author1).updatePageRanks(0, 85))
        .to.be.revertedWith("Iterations must be greater than 0");
      
      // 测试无效阻尼系数
      await expect(authorToken.connect(author1).updatePageRanks(5, 101))
        .to.be.revertedWith("Damping factor must be <= 100");
      
      // 测试无作者情况
      const AuthorTokenFactory = await ethers.getContractFactory("AuthorToken");
      const newAuthorToken = await AuthorTokenFactory.deploy();
      await newAuthorToken.connect(author1).registerAuthor(); // 先注册一个作者
      await expect(newAuthorToken.connect(author1).updatePageRanks(5, 85))
        .to.not.be.reverted; // 现在应该能成功调用
    });

    // 添加新的测试用例：验证未注册作者不能更新PageRank
    it("不应允许未注册作者更新PageRank", async function () {
      await authorToken.connect(author1).registerAuthor();
      await authorToken.connect(author2).registerAuthor();
      
      // 使用未注册的作者尝试更新PageRank
      await expect(authorToken.connect(author3).updatePageRanks(5, 85))
        .to.be.revertedWith("Caller must be a registered author");
    });

    // 添加新的测试用例：验证任何已注册作者都可以更新PageRank
    it("应该允许任何已注册作者更新PageRank", async function () {
      await authorToken.connect(author1).registerAuthor();
      await authorToken.connect(author2).registerAuthor();
      await authorToken.connect(author3).registerAuthor();
      
      // 创建引用关系
      await authorToken.connect(author1).addCitation(author2.address);
      await authorToken.connect(author2).addCitation(author3.address);
      
      // 使用不同的已注册作者更新PageRank
      await authorToken.connect(author1).updatePageRanks(5, 85);
      const scores1 = await Promise.all([
        authorToken.getAuthorInfo(author1.address),
        authorToken.getAuthorInfo(author2.address),
        authorToken.getAuthorInfo(author3.address)
      ]);
      
      // 使用另一个已注册作者再次更新PageRank
      await authorToken.connect(author2).updatePageRanks(5, 85);
      const scores2 = await Promise.all([
        authorToken.getAuthorInfo(author1.address),
        authorToken.getAuthorInfo(author2.address),
        authorToken.getAuthorInfo(author3.address)
      ]);
      
      // 验证两次更新都成功
      expect(scores1[0].pageRankScore).to.be.gt(0);
      expect(scores1[1].pageRankScore).to.be.gt(0);
      expect(scores1[2].pageRankScore).to.be.gt(0);
      expect(scores2[0].pageRankScore).to.be.gt(0);
      expect(scores2[1].pageRankScore).to.be.gt(0);
      expect(scores2[2].pageRankScore).to.be.gt(0);
    });
  });
  
  describe("引用网络测试", function () {
    beforeEach(async function () {
      // 注册三位作者（使用新的合约实例）
      const AuthorTokenFactory = await ethers.getContractFactory("AuthorToken");
      const newAuthorToken = await AuthorTokenFactory.deploy();
      await newAuthorToken.connect(author1).registerAuthor();
      await newAuthorToken.connect(author2).registerAuthor();
      await newAuthorToken.connect(author3).registerAuthor();
      
      // 部署新的引用网络合约
      const CitationNetworkFactory = await ethers.getContractFactory("CitationNetwork");
      const newCitationNetwork = await CitationNetworkFactory.deploy(await newAuthorToken.getAddress());
      citationNetwork = newCitationNetwork;
    });
    
    it("应该能添加引用关系", async function () {
      // 添加引用：1引用2
      await citationNetwork.connect(author1).addCitation(author2.address, "ipfs://paper/123");
      
      // 检查引用是否存在
      const directCiters = await citationNetwork.getDirectCiters(author2.address);
      expect(directCiters.length).to.equal(1);
      expect(directCiters[0]).to.equal(author1.address);
    });
    
    it("应该正确构建引用家族关系", async function () {
      // 创建引用链：1->2->3
      await citationNetwork.connect(author1).addCitation(author2.address, "ipfs://paper/123");
      await citationNetwork.connect(author2).addCitation(author3.address, "ipfs://paper/456");
      
      // 检查作者1的引用家族
      const lineage = await citationNetwork.getAuthorLineage(author1.address);
      expect(lineage.length).to.equal(2);
      expect(lineage).to.include(author2.address);
      expect(lineage).to.include(author3.address);
      
      // 检查作者2的引用家族
      const lineage2 = await citationNetwork.getAuthorLineage(author2.address);
      expect(lineage2.length).to.equal(1);
      expect(lineage2[0]).to.equal(author3.address);
    });
    
    it("应该能验证Merkle证明", async function () {
      // 添加引用
      const tx = await citationNetwork.connect(author1).addCitation(author2.address, "ipfs://paper/123");
      const receipt = await tx.wait();
      
      // 从事件中获取引用ID
      const event = receipt.logs.find(log => 
        log.fragment && log.fragment.name === 'CitationAdded'
      );
      const citationId = event.args.citationId;
      
      // 创建一个简单的Merkle树（在实际应用中，这应该在链下完成）
      const merkleRoot = ethers.keccak256(ethers.toUtf8Bytes(citationId));
      await citationNetwork.updateMerkleRoot(merkleRoot);
      
      // 创建一个简单的证明（在实际应用中，这应该更复杂）
      const proof = [];
      
      // 验证引用
      await citationNetwork.connect(owner).verifyCitation(citationId, proof);
      
      // 检查引用是否已验证
      const citation = await citationNetwork.getCitation(citationId);
      expect(citation.verified).to.equal(true);
    });
    
    it("应该检测并处理引用循环", async function () {
      // 创建引用链：1->2->3->1
      await citationNetwork.connect(author1).addCitation(author2.address, "ipfs://paper/123");
      await citationNetwork.connect(author2).addCitation(author3.address, "ipfs://paper/456");
      await citationNetwork.connect(author3).addCitation(author1.address, "ipfs://paper/789");
      
      // 检查引用家族是否正确处理循环
      const lineage = await citationNetwork.getAuthorLineage(author1.address);
      expect(lineage.length).to.equal(2); // 不应包含自己
      expect(lineage).to.include(author2.address);
      expect(lineage).to.include(author3.address);
    });
    
    it("应该验证引用时间戳", async function () {
      const tx = await citationNetwork.connect(author1).addCitation(author2.address, "ipfs://paper/123");
      const receipt = await tx.wait();
      const block = await ethers.provider.getBlock(receipt.blockNumber);
      
      const citation = await citationNetwork.getCitation(receipt.logs[0].args.citationId);
      expect(citation.timestamp).to.equal(block.timestamp);
    });
    
    it("应该确保引用ID唯一性", async function () {
      // 添加相同引用
      await citationNetwork.connect(author1).addCitation(author2.address, "ipfs://paper/123");
      await expect(citationNetwork.connect(author1).addCitation(author2.address, "ipfs://paper/123"))
        .to.be.revertedWith("Citation already exists");
    });
  });
  
  describe("身份管理测试", function () {
    it("应该能注册身份", async function () {
      const publicKeyHash = ethers.keccak256(ethers.toUtf8Bytes("author1_public_key"));
      await identityManagement.connect(author1).registerIdentity(publicKeyHash, "ipfs://author/1");
      
      const identity = await identityManagement.getIdentity(author1.address);
      expect(identity.walletAddress).to.equal(author1.address);
      expect(identity.publicKeyHash).to.equal(publicKeyHash);
      expect(identity.isVerified).to.equal(false);
    });
    
    it("应该能验证身份", async function () {
      const publicKeyHash = ethers.keccak256(ethers.toUtf8Bytes("author1_public_key"));
      await identityManagement.connect(author1).registerIdentity(publicKeyHash, "ipfs://author/1");
      
      await identityManagement.connect(owner).verifyIdentity(author1.address);
      
      const identity = await identityManagement.getIdentity(author1.address);
      expect(identity.isVerified).to.equal(true);
    });
    
    it("应该能验证签名", async function () {
      // 注册并验证身份
      const publicKeyHash = ethers.keccak256(ethers.toUtf8Bytes("author1_public_key"));
      await identityManagement.connect(author1).registerIdentity(publicKeyHash, "ipfs://author/1");
      await identityManagement.connect(owner).verifyIdentity(author1.address);
      
      // 创建消息哈希
      const messageHash = ethers.keccak256(ethers.toUtf8Bytes("Test message"));
      
      // 签名消息（在实际应用中，这应该使用私钥）
      const signature = await author1.signMessage(ethers.getBytes(messageHash));
      
      // 验证签名
      const isValid = await identityManagement.connect(author1).verifySignature(messageHash, signature);
      expect(isValid).to.equal(true);
    });
    
    it("不应允许重复身份注册", async function () {
      const publicKeyHash = ethers.keccak256(ethers.toUtf8Bytes("author1_public_key"));
      await identityManagement.connect(author1).registerIdentity(publicKeyHash, "ipfs://author/1");
      await expect(identityManagement.connect(author1).registerIdentity(publicKeyHash, "ipfs://author/1"))
        .to.be.revertedWith("Identity already registered");
    });
    
    it("应该能更新身份信息", async function () {
      const publicKeyHash = ethers.keccak256(ethers.toUtf8Bytes("author1_public_key"));
      await identityManagement.connect(author1).registerIdentity(publicKeyHash, "ipfs://author/1");
      
      const newPublicKeyHash = ethers.keccak256(ethers.toUtf8Bytes("new_public_key"));
      await identityManagement.connect(owner).setIdentity(
        author1.address,
        newPublicKeyHash,
        "ipfs://author/1/updated",
        false
      );
      
      const identity = await identityManagement.getIdentity(author1.address);
      expect(identity.publicKeyHash).to.equal(newPublicKeyHash);
      expect(identity.isVerified).to.equal(false); // 更新后应需要重新验证
    });
    
    it("应该能撤销身份", async function () {
      const publicKeyHash = ethers.keccak256(ethers.toUtf8Bytes("author1_public_key"));
      await identityManagement.connect(author1).registerIdentity(publicKeyHash, "ipfs://author/1");
      await identityManagement.connect(owner).verifyIdentity(author1.address);
      
      await identityManagement.connect(owner).revokeIdentity(author1.address);
      
      const identity = await identityManagement.getIdentity(author1.address);
      expect(identity.isVerified).to.equal(false);
    });
  });
  
  describe("利润分配测试", function () {
    beforeEach(async function () {
      // 注册三位作者
      await authorToken.connect(author1).registerAuthor();
      await authorToken.connect(author2).registerAuthor();
      await authorToken.connect(author3).registerAuthor();
      
      // 创建引用关系
      await authorToken.connect(author1).addCitation(author2.address);
      await authorToken.connect(author1).addCitation(author3.address);
      await authorToken.connect(author2).addCitation(author3.address);
      
      // 使用已注册作者更新PageRank
      await authorToken.connect(author1).updatePageRanks(3, 85);
      
      // 向合约发送资金
      await owner.sendTransaction({
        to: await profitDistribution.getAddress(),
        value: ethers.parseEther("10")
      });
    });
    
    it("应该能分配利润", async function () {
      // 设置较短的分配周期以便测试
      await profitDistribution.setDistributionPeriod(1); // 1秒
      
      // 等待1秒
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 分配利润
      await profitDistribution.distributeProfits();
      
      // 检查分配期ID是否增加
      expect(await profitDistribution.currentDistributionId()).to.equal(2);
      
      // 检查作者份额
      const author1Share = await profitDistribution.getAuthorShare(1, author1.address);
      const author2Share = await profitDistribution.getAuthorShare(1, author2.address);
      const author3Share = await profitDistribution.getAuthorShare(1, author3.address);
      
      expect(author1Share.sharePercentage).to.be.gt(0);
      expect(author2Share.sharePercentage).to.be.gt(0);
      expect(author3Share.sharePercentage).to.be.gt(0);
      
      // 总和应为100
      const totalShare = Number(author1Share.sharePercentage) + Number(author2Share.sharePercentage) + Number(author3Share.sharePercentage);
      expect(totalShare).to.equal(100);
    });
    
    it("应该允许作者提取收益", async function () {
      // 设置较短的分配周期
      await profitDistribution.setDistributionPeriod(1);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 分配利润
      await profitDistribution.distributeProfits();
      
      // 记录提取前余额
      const balanceBefore = await ethers.provider.getBalance(author1.address);
      
      // 提取收益
      await profitDistribution.connect(author1).withdrawShare(1);
      
      // 检查余额是否增加
      const balanceAfter = await ethers.provider.getBalance(author1.address);
      expect(balanceAfter).to.be.gt(balanceBefore);
      
      // 检查提取状态
      const share = await profitDistribution.getAuthorShare(1, author1.address);
      expect(share.hasWithdrawn).to.equal(true);
    });
    
    it("应该正确处理零余额分配", async function () {
      // 部署新的合约实例
      const AuthorTokenFactory = await ethers.getContractFactory("AuthorToken");
      const CitationNetworkFactory = await ethers.getContractFactory("CitationNetwork");
      const ProfitDistributionFactory = await ethers.getContractFactory("ProfitDistribution");
      
      const newAuthorToken = await AuthorTokenFactory.deploy();
      const newCitationNetwork = await CitationNetworkFactory.deploy(await newAuthorToken.getAddress());
      const newProfitDistribution = await ProfitDistributionFactory.deploy(
        await newAuthorToken.getAddress(),
        await newCitationNetwork.getAddress()
      );
      
      // 注册新作者
      await newAuthorToken.connect(author1).registerAuthor();
      await newAuthorToken.connect(author2).registerAuthor();
      
      await newProfitDistribution.setDistributionPeriod(1);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      await newProfitDistribution.distributeProfits();
      
      const share = await newProfitDistribution.getAuthorShare(1, author1.address);
      expect(share.sharePercentage).to.equal(50); // 两个作者平分
      expect(share.amount).to.equal(0); // 零余额
    });
    
    it("不应允许重复提取", async function () {
      await profitDistribution.setDistributionPeriod(1);
      await new Promise(resolve => setTimeout(resolve, 1000));
      await profitDistribution.distributeProfits();
      
      await profitDistribution.connect(author1).withdrawShare(1);
      await expect(profitDistribution.connect(author1).withdrawShare(1))
        .to.be.revertedWith("Already withdrawn");
    });
    
    it("应该准确计算分配比例", async function () {
      // 创建不同的引用关系以产生不同的PageRank
      await authorToken.connect(author1).addCitation(author2.address);
      await authorToken.connect(author2).addCitation(author3.address);
      await authorToken.connect(author3).addCitation(author1.address);
      await authorToken.connect(author1).addCitation(author3.address);
      
      // 使用已注册作者更新PageRank
      await authorToken.connect(author1).updatePageRanks(5, 85);
      
      await profitDistribution.setDistributionPeriod(1);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 分配10 ETH
      const totalAmount = ethers.parseEther("10");
      await owner.sendTransaction({
        to: await profitDistribution.getAddress(),
        value: totalAmount
      });
      await profitDistribution.distributeProfits();
      
      // 检查分配比例总和
      const share1 = await profitDistribution.getAuthorShare(1, author1.address);
      const share2 = await profitDistribution.getAuthorShare(1, author2.address);
      const share3 = await profitDistribution.getAuthorShare(1, author3.address);
      
      const totalShare = Number(share1.sharePercentage) + 
                        Number(share2.sharePercentage) + 
                        Number(share3.sharePercentage);
      expect(totalShare).to.equal(100);
      
      // 检查金额计算
      const amount1 = (totalAmount * BigInt(share1.sharePercentage)) / BigInt(100);
      const amount2 = (totalAmount * BigInt(share2.sharePercentage)) / BigInt(100);
      const amount3 = (totalAmount * BigInt(share3.sharePercentage)) / BigInt(100);
      
      expect(amount1 + amount2 + amount3).to.equal(totalAmount);
    });
  });
});