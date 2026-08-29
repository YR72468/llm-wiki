# LLM Wiki — 自生长知识网络引擎

## 核心设计理念

**突破点：从"检索答案"升级为"拥有知识"**

传统 RAG/Knowledge-Base 的问题：
1. **机械检索** — 每次查询都要重新扫描全文、计算向量相似度
2. **知识碎片化** — 没有实体关联、概念沉淀、结构演进
3. **不会自省** — 不知道自己的知识有没有矛盾、缺了什么

这个系统的解法：

```
输入: 原始文档 (PDF/Markdown/网页)
         ↓
   [知识提取] → 实体/关系/概念/事实
         ↓
   [图谱构建] → 知识图谱 (Neo4j/纯文本)
         ↓
   [关联映射] → 实体页 ↔ 概念页 ↔ 主题页
         ↓
   [自我进化] → 每有新资料 → 自动检测冲突/增量/新实体
```

## 三阶段工作流

### Phase 1: 内容整合 (Integrate)
- 输入新文档/资料
- 自动抽取: 实体(Entity) → 关系(Relationship) → 命题(Proposition)
- 去重: 对比已有知识图谱，识别重复/矛盾/新概念
- 输出: `knowledge-graph.json` (结构化知识图谱)

### Phase 2: 动态更新 (Evolve)
- 基于知识图谱自动生成三类页面:
  - **实体页** (`entities/<name>.md`) — 关于具体的人/事/物
  - **概念页** (`concepts/<name>.md`) — 抽象概念的定义与应用
  - **主题页** (`themes/<name>.md`) — 围绕特定主题的聚合
- 将历史问答结果回写知识图谱 (持续迭代)

### Phase 3: 自检优化 (Audit)
- 运行 `audit.py` 生成知识健康报告
- 检测: 孤立节点、矛盾关系、缺失关联、覆盖率统计
- 输出: `output/health-report.md` (带优先级标记)

## 文件结构

```
llm-wiki/
├── ARCHITECTURE.md          # 本文件
├── USAGE.md                 # 使用指南
├── knowledge-engine/
│   ├── __init__.py
│   ├── extractor.py         # 知识抽取 (实体/关系/事实)
│   ├── graph.py             # 知识图谱核心
│   ├── auditor.py           # 自检引擎
│   ├── generator.py         # 页面生成器
│   ├── updater.py           # 增量更新
│   ├── templates/           # 页面模板
│   │   ├── entity.md
│   │   ├── concept.md
│   │   └── theme.md
│   └── knowledge-base/      # 知识库 (最终产物)
│       ├── entities/        # 实体页
│       ├── concepts/        # 概念页
│       └── themes/          # 主题页
├── examples/                # 示例资料
│   └── sample.md
└── output/                  # 生成产物
    ├── health-report.md     # 健康报告
    └── ...
```

## 关键技术决策

| 维度 | 选择 | 理由 |
|------|------|------|
| 图谱存储 | JSON + Markdown | 纯文本可 git 管理、可 diff、不需要数据库 |
| 抽取引擎 | LLM Prompt 驱动 | 灵活，不依赖预训练模型 |
| 更新策略 | 增量追加 + 冲突合并 | 保留历史痕迹，便于审计 |
| 搜索方式 | 全文搜索 + 图谱遍历 | 避免向量检索开销，利用结构化索引 |
| 可视化 | 可选接入 Mermaid | Markdown 原生兼容 |

## 与传统方案对比

```
RAG/向量检索:
  查询 → 嵌入(document) → 相似度搜索 → 拼凑答案
  缺点: 每查一次扫一遍全文，答案可能矛盾

本方案:
  查询 → 图谱遍历(实体关系) → 定位精确页面 → 生成连贯答案
  优点: 知识已沉淀，有结构，可溯源，自检测
```
