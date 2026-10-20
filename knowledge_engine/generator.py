"""
页面生成器 — PageGenerator

职责: 将知识图谱自动转化为可读的三类页面模板
- 实体页 (entities/)
- 概念页 (concepts/)
- 主题页 (themes/)
"""

import os
import json
from datetime import datetime
from typing import Optional

# 复用 graph 模块中的类
try:
    from graph import KnowledgeGraph
    from extractor import Entity, Relationship
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from graph import KnowledgeGraph
    from extractor import Entity, Relationship


class PageGenerator:
    """知识页面自动生成器"""

    ENTITY_TEMPLATE = """\
# {name}

> **类型**: {entity_type}  
> **来源**: {source}  
> **更新日期**: {dt_updated}  

## 概述

{description}

## 属性

{attributes}

## 关系网络

{relationships}

## 相关命题

{propositions}

## 关联实体

{related}

---
*由 LLM Wiki 知识引擎自动生成于 {dt_generated}*
"""

    CONCEPT_TEMPLATE = """\
# {name}

> **类别**: 概念  
> **最近更新**: {dt_updated}  

## 定义

{definition}

## 核心要点

{key_points}

## 相关技术/方法

{related_items}

## 应用领域

{applications}

## 代表实体

{representatives}

## 矛盾与争议

{controversies}

---
*由 LLM Wiki 知识引擎自动生成于 {dt_generated}*
"""

    THEME_TEMPLATE = """\
# {name}

> **类型**: 主题聚合  
> **覆盖范围**: {scope}  
> **最近更新**: {dt_updated}  

## 概述

{overview}

## 构成要素

{components}

## 关键实体 ({entity_count})

{entities_list}

## 核心关系

{core_relations}

## 命题汇总

{propositions_summary}

## 知识缺口

{gaps}

## 关联主题

{related_themes}

---
*由 LLM Wiki 知识引擎自动生成于 {dt_generated}*
"""

    def __init__(self, knowledge_graph: KnowledgeGraph, output_dir: str):
        self.kg = knowledge_graph
        self.output_dir = output_dir

    def generate_all(self):
        """生成全部三类页面"""
        print(f"\n{'='*60}")
        print(f"  知识页面生成器")
        print(f"{'='*60}")

        self._generate_entity_pages()
        self._generate_concept_pages()
        self._generate_theme_pages()

        print(f"\n  ✅ 页面生成完成!")
        print(f"     输出目录: {self.output_dir}")

    def _safe_filename(self, name: str) -> str:
        """生成安全的文件名"""
        import re
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        return name[:50] if len(name) > 50 else name

    def _generate_entity_pages(self):
        """生成实体页"""
        entities_dir = os.path.join(self.output_dir, "entities")
        os.makedirs(entities_dir, exist_ok=True)

        entities = self.kg.get_all_entities()
        generated = 0

        for entity in entities:
            if not entity.name or entity.name.lower() in ('未知', 'unknown'):
                continue

            page_content = self._build_entity_page(entity)
            fname = self._safe_filename(entity.name)
            filepath = os.path.join(entities_dir, f"{fname}.md")

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(page_content)

            generated += 1

        print(f"  📄 实体页: {generated} 篇")

    def _generate_concept_pages(self):
        """生成概念页 — 按实体类型分组为概念"""
        concepts_dir = os.path.join(self.output_dir, "concepts")
        os.makedirs(concepts_dir, exist_ok=True)

        # 按类型分组实体
        type_groups = {}
        for entity in self.kg.get_all_entities():
            etype = entity.type
            if etype not in type_groups:
                type_groups[etype] = []
            type_groups[etype].append(entity)

        # 每种类型生成一个概念页
        type_labels = {
            'concept': '概念',
            'person': '人物',
            'organization': '机构',
            'thing': '事物',
            'event': '事件',
        }

        generated = 0
        for etype, entities in type_groups.items():
            if len(entities) < 2:
                continue

            label = type_labels.get(etype, etype)
            concept_name = f"{label}集合"
            page_content = self._build_concept_page(concept_name, entities, label)

            filepath = os.path.join(concepts_dir, f"{concept_name}.md")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(page_content)

            generated += 1

        print(f"  📄 概念页: {generated} 篇")

    def _generate_theme_pages(self):
        """生成主题页 — 按关系类型或领域聚合"""
        themes_dir = os.path.join(self.output_dir, "themes")
        os.makedirs(themes_dir, exist_ok=True)

        # 按关系类型分组生成主题
        relation_types = {}
        for rel in self.kg._relation_index:
            rt = rel.relation
            if rt not in relation_types:
                relation_types[rt] = []
            relation_types[rt].append(rel)

        generated = 0
        for rel_type, relations in relation_types.items():
            if len(relations) < 2:
                continue

            page_content = self._build_theme_page(rel_type, relations)
            filepath = os.path.join(themes_dir, f"{rel_type}.md")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(page_content)

            generated += 1

        # 按实体类型生成主题
        entity_types = {}
        for entity in self.kg.get_all_entities():
            if entity.type not in entity_types:
                entity_types[entity.type] = []
            entity_types[entity.type].append(entity)

        for etype, ents in entity_types.items():
            page_content = self._build_theme_page(f"领域:{etype}", [{"entities": ents}])
            filepath = os.path.join(themes_dir, f"领域-{etype}.md")
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(page_content)
            generated += 1

        print(f"  📄 主题页: {generated} 篇")

    def _build_entity_page(self, entity: Entity) -> str:
        """构建实体页内容"""
        # 获取关系
        outgoing = self.kg.get_relations_from(entity.name)
        incoming = self.kg.get_relations_to(entity.name)
        all_rels = outgoing + incoming

        # 构建关系表格
        rel_table = "| 方向 | 关系 | 目标 |\n|------|------|------|\n"
        for rel in all_rels[:20]:
            direction = "→" if rel in outgoing else "←"
            rel_table += f"| {direction} | {rel.relation} | {rel.target if direction == '→' else rel.source} |\n"

        # 构建相关实体
        related_names = set()
        for rel in all_rels:
            related_names.add(rel.source)
            related_names.add(rel.target)
        related_names.discard(entity.name.lower())
        related_list = ", ".join(list(related_names)[:10]) if related_names else "暂无关联实体"

        attrs_str = ""
        if entity.attributes:
            for k, v in entity.attributes.items():
                attrs_str += f"- **{k}**: {v}\n"

        props = self.kg.get_related_props(entity.name)
        props_str = ""
        for p in props[:10]:
            props_str += f"- {p.subject} {p.predicate} {p.object}\n"

        return self.ENTITY_TEMPLATE.format(
            name=entity.name,
            entity_type=entity.type,
            source=entity.source or "未知",
            description=entity.description or "暂无描述。",
            attributes=attrs_str if attrs_str else "*无额外属性*",
            relationships=rel_table if rel_table != "| 方向 | 关系 | 目标 |\n|------|------|------|\n" else "*暂无关系*",
            propositions=props_str if props_str else "*暂无相关命题*",
            related=related_list,
            dt_updated=datetime.now().strftime('%Y-%m-%d'),
            dt_generated=datetime.now().strftime('%Y-%m-%d %H:%M'),
        )

    def _build_concept_page(self, name: str, entities: list, label: str) -> str:
        """构建概念页内容"""
        key_points = "\n".join([f"- {e.name}" for e in entities[:15]])
        applications = f"{label}在多个领域有应用"
        representatives = ", ".join([e.name for e in entities[:10]]) if entities else "暂无"

        return self.CONCEPT_TEMPLATE.format(
            name=name,
            dt_updated=datetime.now().strftime('%Y-%m-%d'),
            definition=f"关于{label}的概念集合，共收录 {len(entities)} 个实体。",
            key_points=key_points,
            related_items="关联技术待补充",
            applications=applications,
            representatives=representatives,
            controversies="暂无标注矛盾",
            dt_generated=datetime.now().strftime('%Y-%m-%d %H:%M'),
        )

    def _build_theme_page(self, theme_name: str, relations_or_entities) -> str:
        """构建主题页内容"""
        entities = []
        if isinstance(relations_or_entities[0], dict) and "entities" in relations_or_entities[0]:
            for r in relations_or_entities:
                entities.extend(r.get("entities", []))
        else:
            for r in relations_or_entities:
                if hasattr(r, 'source'):
                    entities.append(r.source)
                elif hasattr(r, 'target'):
                    entities.append(r.target)

        entity_count = len(set(str(e) for e in entities))
        entities_list = "\n".join([f"- {e}" for e in list(set(str(e) for e in entities))[:20]])

        core_relations = ""
        for r in relations_or_entities[:15]:
            if hasattr(r, 'source') and hasattr(r, 'target'):
                core_relations += f"- {r.source} →[{r.relation}]→ {r.target}\n"
            elif hasattr(r, '__dict__'):
                core_relations += f"- {r}\n"

        return self.THEME_TEMPLATE.format(
            name=theme_name,
            scope=f"围绕 '{theme_name}' 的知识聚合",
            dt_updated=datetime.now().strftime('%Y-%m-%d'),
            overview=f"本主题涵盖 {entity_count} 个实体及相关关系。",
            components=core_relations if core_relations else "暂无组件",
            entity_count=entity_count,
            entities_list=entities_list if entities_list else "暂无",
            core_relations=core_relations if core_relations else "暂无核心关系",
            propositions_summary="待补充",
            gaps="待分析",
            related_themes="待关联",
            dt_generated=datetime.now().strftime('%Y-%m-%d %H:%M'),
        )
