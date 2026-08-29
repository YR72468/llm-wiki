# 使用指南

## 快速开始

### 1. 首次构建知识库

```bash
cd llm-wiki
python main.py --input examples/sample.md --output knowledge-base/
```

### 2. 增量更新

添加新资料时，使用 `--incremental` 参数:

```bash
python main.py --input new_document.md --output knowledge-base/ --incremental
```

### 3. 单独审计

定期运行知识健康检查:

```bash
python main.py --audit --graph knowledge-base/graph.json --report output/health-report.md
```

## 系统架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  原始资料     │  →  │  知识抽取     │  →  │  图谱构建     │
│  (Markdown)   │     │  (Entity/Rel) │     │  (Graph)     │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                          ┌───────▼───────┐
                                          │  页面生成       │
                                          │  (Entity/Concept│
                                          │   /Theme Pages) │
                                          └───────┬───────┘
                                                  │
                                          ┌───────▼───────┐
                                          │  健康审计       │
                                          │  (Conflict     │
                                          │   Detection)   │
                                          └───────────────┘
```

## 模块说明

| 模块 | 文件 | 功能 |
|------|------|------|
| 抽取器 | `extractor.py` | 从文本中提取实体、关系、命题 |
| 图谱 | `graph.py` | 图数据结构、关系存储、路径搜索 |
| 生成器 | `generator.py` | 生成实体页/概念页/主题页 |
| 审计器 | `auditor.py` | 健康评分、冲突检测、孤立节点 |
| 更新器 | `updater.py` | 增量合并、重复检测、更新日志 |

## 输入格式

支持 Markdown、Text、JSON 格式:

```markdown
# 实体名称

这是一段描述文字。

- 张三毕业于清华大学
- OpenAI 是 GPT 系列的开发者
```

## 输出结构

```
knowledge-base/
├── entities/          # 实体页面
│   ├── 大语言模型.md
│   ├── Transformer.md
│   └── ...
├── concepts/          # 概念页面
│   ├── 技术.md
│   └── ...
├── themes/            # 主题聚合
│   ├── 领域-概念.md
│   └── ...
└── graph.json         # 原始知识图谱数据
```

## 扩展开发

### 添加新的抽取规则

编辑 `knowledge-engine/extractor.py`:

```python
RELATION_TEMPLATES = [
    # 新增规则
    (r'(.*?)出生于(.*?)(\d{4})年', lambda s: ('born_in', s[0], s[2])),
]
```

### 替换为 LLM 抽取

将 `extract()` 方法改为调用 API:

```python
def extract(self, text, source_doc):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )
    return self._parse_llm_output(response.choices[0].message.content)
```

## 注意事项

1. 当前版本使用启发式规则抽取，复杂文档建议用 LLM 增强
2. 图谱文件 `graph.json` 可用 git 管理版本
3. 健康报告定期运行 (建议每周)
4. 建议先小规模测试再大规模构建
