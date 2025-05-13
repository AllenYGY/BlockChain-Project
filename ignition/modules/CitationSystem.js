// 学术引用系统部署模块
const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

module.exports = buildModule("CitationSystemModule", (m) => {
  // 部署作者身份币合约
  const authorToken = m.contract("AuthorToken", []);
  
  // 部署身份管理合约
  const identityManagement = m.contract("IdentityManagement", []);
  
  // 部署引用网络合约，只依赖于作者身份币合约
  const citationNetwork = m.contract("CitationNetwork", [authorToken]);
  
  // 部署利润分配合约，依赖于作者身份币合约和引用网络合约
  const profitDistribution = m.contract("ProfitDistribution", [
    authorToken,
    citationNetwork
  ]);
  
  return { 
    authorToken, 
    citationNetwork, 
    profitDistribution, 
    identityManagement 
  };
});