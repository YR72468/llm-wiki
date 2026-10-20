# LLM Wiki 知识引擎

基于知识图谱的 LLM 知识管理系统，实现**抽取 → 构建/更新 → 生成/审计**三阶段自动化流水线。

## 核心能力

- 从 Markdown / 文本中抽取实体与关系，自动构建知识图谱
- 支持增量更新与重复实体检测
- 自动生成结构化 Wiki 页面
- 知识健康审计：健康评分、冲突检测、孤立节点分析

## 快速开始

```bash
pip install -r requirements.txt

# 从示例语料构建知识库
python main.py --input examples/sample.md --output knowledge-base/

# 仅运行健康审计
python main.py --audit --graph knowledge-base/graph.json --report output/health-report.md
```

## 目录结构

| 路径 | 说明 |
|------|------|
| `main.py` | 主入口与命令行接口 |
| `knowledge_engine/` | 知识引擎核心（graph / extractor / generator / auditor / updater） |
| `knowledge-base/` | 生成的知识库与 `graph.json` 图谱 |
| `examples/` | 示例语料 |
| `tests/` | 单元测试套件（pytest） |

## CI/CD

本项目通过 GitHub Actions 实现：

- **lint**：Flake8 + Black 代码风格校验
- **test**：Python 3.10 / 3.11 / 3.12 矩阵单元测试与覆盖率
- **knowledge-graph-validation**：基于真实 `graph.json` 的知识图谱健康审计
- **security-scan**：safety + bandit 安全扫描
- **deploy**：构建 MkDocs 站点并发布到 GitHub Pages
