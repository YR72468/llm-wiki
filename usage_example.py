"""
LLM Wiki 使用说明
"""

# ============================================================
# LLM Wiki 自生长知识网络引擎 — 使用说明
# ============================================================

USAGE_TEXT = '''
================================================================================
LLM Wiki — 自生长知识网络引擎
================================================================================

## 快速开始

1. 准备你的知识资料 (Markdown/Text 格式)
   放在 examples/ 目录下

2. 首次构建
   ```bash
   cd llm-wiki
   python main.py --input examples/ --output knowledge-base/
   ```

3. 增量更新 (添加新资料)
   ```bash
   python main.py --input examples/new-material.md --output knowledge-base/ --incremental
   ```

4. 单独运行知识健康审计
   ```bash
   python main.py --audit --graph knowledge-base/graph.json --report output/health-report.md
   ```

## 系统架构

```
原始资料 → [抽取] → [图谱] → [页面] → [审计]
             ↓        ↓        ↓        ↓
        实体/关系  知识网络  Markdown   健康报告
```

## 目录结构

llm-wiki/
├── main.py                  # 入口脚本
├── knowledge-engine/        # 核心引擎
│   ├── extractor.py         # 知识抽取 (实体/关系/命题)
│   ├── graph.py             # 知识图谱 (图数据结构)
│   ├── generator.py         # 页面生成器 (实体页/概念页/主题页)
│   ├── auditor.py           # 知识审计器 (健康检测)
│   └── updater.py           # 增量更新器 (去重/合并)
├── examples/                # 输入资料
├── knowledge-base/          # 生成的知识库
│   ├── entities/            # 实体页
│   ├── concepts/            # 概念页
│   └── themes/              # 主题页
└── output/                  # 审计报告
    └── health-report.md

## 进阶用法

### 自定义抽取规则
编辑 knowledge-engine/extractor.py 中的 RELATION_TEMPLATES
添加更多的正则模板来匹配你的领域。

### 集成 LLM 抽取器
当前版本使用启发式规则抽取，你可以替换 extractor.py 中的
extract() 方法，使用 OpenAI API / Claude API / 本地模型
进行更精准的知识抽取。

### API 调用示例
from knowledge_engine.graph import KnowledgeGraph
from knowledge_engine.extractor import KnowledgeExtractor

kg = KnowledgeGraph("my_project")
extractor = KnowledgeExtractor()

for doc in documents:
    unit = extractor.extract(doc.text, doc.id)
    kg.ingest(unit)

kg.save("output/graph.json")

## 设计哲学

- 纯文本可管理: 不需要数据库，全部存为 Markdown + JSON
- 增量可审计: 每次更新都记录日志，可追溯
- 自检自优化: 定期运行审计发现知识缺口和矛盾
- 结构化生长: 不是堆砌文档，而是构建关联的网络

'''

print(USAGE_TEXT)
