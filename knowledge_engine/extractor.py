"""
知识抽取器 — KnowledgeExtractor

职责: 从原始文档/文本中提取结构化知识
输出: (实体, 关系, 命题) 三元组
"""

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Entity:
    """实体"""
    name: str
    type: str            # person / organization / concept / event / thing
    attributes: dict = field(default_factory=dict)
    description: str = ""
    source: str = ""     # 来源文档

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class Relationship:
    """关系边"""
    source: str        # 实体A名称
    target: str        # 实体B名称
    relation: str      # 关系类型
    confidence: float = 1.0
    evidence: str = "" # 原文证据
    source_doc: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class Proposition:
    """命题 (事实陈述)"""
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    context: str = ""
    source_doc: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class KnowledgeUnit:
    """知识单元 = 实体 + 关系 + 命题"""
    entities: list = field(default_factory=list)
    relationships: list = field(default_factory=list)
    propositions: list = field(default_factory=list)

    def to_dict(self):
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "propositions": [p.to_dict() for p in self.propositions],
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            entities=[Entity.from_dict(e) for e in d.get("entities", [])],
            relationships=[Relationship.from_dict(r) for r in d.get("relationships", [])],
            propositions=[Proposition.from_dict(p) for p in d.get("propositions", [])],
        )

    def save_json(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class KnowledgeExtractor:
    """
    知识抽取器

    当前版本使用启发式规则抽取，后续可替换为 LLM 驱动的抽取。

    抽取逻辑:
    1. 实体识别 — 通过命名实体模式匹配 + 上下文分析
    2. 关系推断 — 通过句式模板匹配
    3. 命题提取 — 从陈述句中抽取事实
    """

    # 常见关系模板
    RELATION_TEMPLATES = [
        # X是Y的创始人
        (r'(.+?)是(.+?)的创始人', lambda s: ('founder_of', s[1], s[0])),
        # X出生于Y年
        (r'(.+?)出生(于)?(\d{4})年', lambda s: ('born_in', s[0], s[2])),
        # X任职于Y公司
        (r'(.+?)(?:任职|工作|就职)于(.+?)(?:公司|机构)', lambda s: ('works_at', s[0], s[1])),
        # X毕业于Y大学
        (r'(.+?)(?:毕业|毕业于)(.+?)大学', lambda s: ('educated_at', s[0], s[1])),
        # X属于Y领域
        (r'(?:属于|位于|面向|.+?)((?:自然语言处理|计算机视觉|强化学习|大语言模型|知识图谱|机器学习))',
         lambda s: ('in_domain', s[0], s[1])),
        # X应用于Y
        (r'(.+?)应用(?:于|在)((?:医疗|金融|教育|法律|制造))', lambda s: ('applies_to', s[0], s[1])),
        # 概念定义: X是指/就是/称为...
        (r'(.+?)(?:是指|就是|称为|被称为|指的是)((?:.+:|[^。]{5,}))',
         lambda s: ('definition', s[0], s[1])),
        # X包含Y子项
        (r'(.+?)(?:包含|分为|包括)(?:以下|:)?(.+?)(?:技术|方法|模型|框架|系统)',
         lambda s: ('has_subcategory', s[0], s[1] + '技术')),
    ]

    def extract(self, text: str, source_doc: str = "") -> KnowledgeUnit:
        """
        从文本中提取知识

        Args:
            text: 原始文本
            source_doc: 来源文档标识

        Returns:
            KnowledgeUnit 包含提取的实体、关系、命题
        """
        unit = KnowledgeUnit()
        sentences = self._split_sentences(text)

        # 1. 实体识别
        entities = self._extract_entities(text, source_doc)
        unit.entities.extend(entities)
        entity_names = {e.name.lower() for e in entities}

        # 2. 关系抽取
        relationships = self._extract_relations(sentences, source_doc, entity_names)
        unit.relationships.extend(relationships)

        # 3. 命题提取
        propositions = self._extract_propositions(sentences, source_doc)
        unit.propositions.extend(propositions)

        return unit

    def _split_sentences(self, text: str) -> list:
        """按句号/换行分割句子"""
        # 先按分段切
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        sentences = []
        for para in paragraphs:
            # 再按标点切
            parts = re.split(r'[。！？；]', para)
            sentences.extend([s.strip() for s in parts if s.strip()])
        return sentences

    def _extract_entities(self, text: str, source_doc: str = "") -> list:
        """
        实体抽取 — 启发式规则

        支持的实体类型:
        - concept: 技术概念、方法论
        - person: 人名
        - organization: 机构/公司
        - thing: 产品、工具、框架
        - event: 事件
        """
        entities = []
        seen = set()

        # 概念型实体 — 匹配术语
        concept_patterns = [
            (r'(?<![a-zA-Z])([A-Z][A-Za-z]*(?:[A-Za-z]+\s+)*(?:[A-Z]\w*))\s*(?:技术|模型|框架|系统|方法|算法|架构)',
             'concept'),
            (r'([\u4e00-\u9fff]{2,15})(?:大语言模型|知识图谱|自然语言处理|计算机视觉|深度学习)',
             'concept'),
            (r'([A-Z]{2,})(?:Transformer|BERT|GPT|LLM|AI|NLP)',
             'concept'),
        ]

        for pattern, etype in concept_patterns:
            for match in re.finditer(pattern, text):
                name = match.group(0).strip()
                # 过滤掉太短或包含非实体内容的名
                if name.lower() not in seen and 2 <= len(name) <= 30:
                    seen.add(name.lower())
                    entities.append(Entity(
                        name=name,
                        type=etype,
                        source=source_doc
                    ))

        # 人名 — 简单的中文字符序列 (2-4字)
        person_pattern = r'([一-龥]{2,4})(?:先生|教授|博士|老师|研究员|负责人)'
        for match in re.finditer(person_pattern, text):
            name = match.group(1)
            if name.lower() not in seen:
                seen.add(name.lower())
                entities.append(Entity(
                    name=name,
                    type='person',
                    source=source_doc
                ))

        return entities

    def _extract_relations(self, sentences: list, source_doc: str = "", entity_names: set = None) -> list:
        """
        关系抽取 — 基于模板匹配
        """
        relationships = []
        for sent in sentences:
            for pattern, transform in self.RELATION_TEMPLATES:
                match = re.search(pattern, sent)
                if match:
                    try:
                        rel_type, src, tgt = transform(match.groups())
                        relationships.append(Relationship(
                            source=src,
                            target=tgt,
                            relation=rel_type,
                            evidence=sent[:200],
                            source_doc=source_doc
                        ))
                    except (IndexError, TypeError):
                        continue
        return relationships

    def _extract_propositions(self, sentences: list, source_doc: str = "") -> list:
        """
        命题提取 — 从陈述句中抽取 Subject-Predicate-Object
        """
        propositions = []
        # 基本句式模式
        patterns = [
            (r'(.*?)是(.+?)的(.+?)', lambda g: ('subject', g[2], g[1])),
            (r'(.*?)包含(.+?)', lambda g: ('has_part', g[0], g[1])),
            (r'(.*?)应用于(.+?)', lambda g: ('applies_to', g[0], g[1])),
        ]

        for sent in sentences:
            if len(sent) < 10:
                continue
            for pattern, transform in patterns:
                match = re.search(pattern, sent)
                if match:
                    try:
                        s, pred, o = transform(match.groups())
                        if s and pred and o and len(pred) > 2:
                            propositions.append(Proposition(
                                subject=s,
                                predicate=pred,
                                object=o,
                                context=sent[:200],
                                source_doc=source_doc
                            ))
                    except (IndexError, TypeError):
                        continue

        return propositions

    def extract_batch(self, texts: list, source_docs: list = None) -> list:
        """批量抽取"""
        if source_docs is None:
            source_docs = [f"doc_{i}" for i in range(len(texts))]

        units = []
        for text, doc in zip(texts, source_docs):
            unit = self.extract(text, doc)
            units.append(unit)
        return units
