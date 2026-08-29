"""
知识图谱 — KnowledgeGraph

核心数据结构: 基于图的实体-关系网络
操作: 增删改查、路径搜索、连通性分析
"""

import json
import os
import networkx as nx
from datetime import datetime
from collections import defaultdict, Counter
from typing import Optional

try:
    from extractor import Entity, Relationship, Proposition, KnowledgeUnit
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from extractor import Entity, Relationship, Proposition, KnowledgeUnit


class KnowledgeGraph:
    """
    知识图谱 — 有向多层图

    节点类型:
      - entity: 实体节点 (name, type, attrs, description)
      - relationship: 关系边 (source, target, relation_type, weight)
      - proposition: 命题 (独立的事实节点，用于细粒度检索)

    特性:
      - 自动去重 (同名实体合并)
      - 冲突检测 (同实体不同属性/关系)
      - 路径搜索 (两实体间的所有关系链)
      - 连通性分析 (孤岛检测、社区发现)
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

        # 底层图结构
        self.graph = nx.DiGraph()

        # 索引: 快速查找
        self._entity_index = {}       # name -> Entity
        self._relation_index = []     # list of Relationships
        self._proposition_index = []  # list of Propositions

        # 元数据
        self.metadata = {
            "entity_count": 0,
            "relationship_count": 0,
            "proposition_count": 0,
            "domains": [],
            "sources": set(),
        }

    # ==================== 核心操作 ====================

    def add_entity(self, entity: Entity) -> bool:
        """
        添加实体节点

        Returns:
            True = 新增, False = 已存在(跳过)
        """
        name_lower = entity.name.lower()

        if name_lower in self._entity_index:
            # 已存在 — 可能需要合并属性
            existing = self._entity_index[name_lower]
            self._merge_entity(existing, entity)
            return False

        self.graph.add_node(name_lower, type='entity', data=entity)
        self._entity_index[name_lower] = entity
        self.metadata["entity_count"] += 1
        self.metadata["sources"].add(entity.source)
        self.updated_at = datetime.now().isoformat()
        return True

    def add_relationship(self, rel: Relationship) -> bool:
        """
        添加关系边

        如果关系已存在，增加权重(weight++)
        """
        src = rel.source.lower()
        tgt = rel.target.lower()
        key = (src, tgt, rel.relation.lower())

        # 确保两端实体存在
        if src not in self._entity_index:
            self.add_entity(Entity(name=rel.source, type='unknown', source=rel.source_doc))
        if tgt not in self._entity_index:
            self.add_entity(Entity(name=rel.target, type='unknown', source=rel.source_doc))

        # 检查是否已存在相同关系
        edges = list(self.graph.edges(keys=True))
        for s, t, r in edges:
            if s == src and t == tgt and r == rel.relation.lower():
                # 已存在 — 增量更新
                return False

        # 添加边
        self.graph.add_edge(src, tgt, key=rel.relation.lower(), data=rel)
        self._relation_index.append(rel)
        self.metadata["relationship_count"] += 1
        self.updated_at = datetime.now().isoformat()
        return True

    def add_proposition(self, prop: Proposition):
        """添加命题节点"""
        prop_id = f"{prop.subject}-{prop.predicate}-{prop.object}"[:50]
        self.graph.add_node(prop_id, type='proposition', data=prop)
        self._proposition_index.append(prop)
        self.metadata["proposition_count"] += 1
        self.updated_at = datetime.now().isoformat()

    def _merge_entity(self, existing: Entity, new: Entity):
        """合并已有实体和新实体的属性"""
        for k, v in new.attributes.items():
            if k not in existing.attributes:
                existing.attributes[k] = v
            elif isinstance(v, list) and isinstance(existing.attributes[k], list):
                existing.attributes[k].extend([x for x in v if x not in existing.attributes[k]])
        if new.description and not existing.description:
            existing.description = new.description
        if new.source:
            existing.source = new.source

    # ==================== 查询操作 ====================

    def get_entity(self, name: str) -> Optional[Entity]:
        """通过名称查询实体"""
        return self._entity_index.get(name.lower())

    def get_all_entities(self, entity_type: str = None) -> list:
        """获取所有实体，可按类型过滤"""
        if entity_type:
            return [e for e in self._entity_index.values() if e.type == entity_type]
        return list(self._entity_index.values())

    def get_relations_from(self, entity_name: str) -> list:
        """获取某实体的出边关系"""
        name_lower = entity_name.lower()
        return [rel for rel in self._relation_index
                if rel.source.lower() == name_lower]

    def get_relations_to(self, entity_name: str) -> list:
        """获取指向某实体的入边关系"""
        name_lower = entity_name.lower()
        return [rel for rel in self._relation_index
                if rel.target.lower() == name_lower]

    def get_neighbors(self, entity_name: str, direction: str = 'both') -> list:
        """获取邻居实体"""
        name_lower = entity_name.lower()
        neighbors = set()

        if direction in ('out', 'both'):
            for succ in self.graph.successors(name_lower):
                neighbors.add(succ)
        if direction in ('in', 'both'):
            for pred in self.graph.predecessors(name_lower):
                neighbors.add(pred)

        return list(neighbors)

    def find_path(self, start: str, end: str, max_depth: int = 5) -> list:
        """
        查找两个实体之间的最短关系链
        """
        start_l = start.lower()
        end_l = end.lower()

        if start_l not in self._entity_index or end_l not in self._entity_index:
            return []

        try:
            paths = nx.shortest_path(self.graph, source=start_l, target=end_l)
            return paths
        except nx.NetworkXNoPath:
            return []

    def get_related_props(self, entity_name: str) -> list:
        """获取与实体相关的所有命题"""
        name_lower = entity_name.lower()
        return [p for p in self._proposition_index
                if p.subject.lower() == name_lower or
                   p.object.lower() == name_lower]

    # ==================== 批量导入 ====================

    def ingest(self, unit: KnowledgeUnit, deduplicate: bool = True):
        """
        导入一个知识单元

        Args:
            unit: KnowledgeUnit 包含实体/关系/命题
            deduplicate: 是否去重 (True=跳过已存在实体)
        """
        added = 0
        for entity in unit.entities:
            if deduplicate and entity.name.lower() in self._entity_index:
                continue
            if self.add_entity(entity):
                added += 1

        for rel in unit.relationships:
            if self.add_relationship(rel):
                added += 1

        for prop in unit.propositions:
            self.add_proposition(prop)

        return added

    def ingest_batch(self, units: list) -> dict:
        """批量导入，返回统计"""
        stats = {"entities_added": 0, "relationships_added": 0, "propositions_added": 0}

        for unit in units:
            for entity in unit.entities:
                if self.add_entity(entity):
                    stats["entities_added"] += 1

            for rel in unit.relationships:
                if self.add_relationship(rel):
                    stats["relationships_added"] += 1

            for prop in unit.propositions:
                self.add_proposition(prop)
                stats["propositions_added"] += 1

        return stats

    # ==================== 存储/加载 ====================

    def save(self, filepath: str):
        """
        保存图谱到 JSON 文件
        """
        data = {
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": {
                **{k: list(v) if k == "sources" else v for k, v in self.metadata.items()},
            },
            "entities": {k: v.to_dict() for k, v in self._entity_index.items()},
            "relationships": [r.to_dict() for r in self._relation_index],
            "propositions": [p.to_dict() for p in self._proposition_index],
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  Graph saved: {filepath}")
        print(f"  Entities: {self.metadata['entity_count']}, "
              f"Relations: {self.metadata['relationship_count']}, "
              f"Propositions: {self.metadata['proposition_count']}")

    @classmethod
    def load(cls, filepath: str) -> 'KnowledgeGraph':
        """从 JSON 文件加载图谱"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        graph = cls(name=data.get("name", "loaded"))
        graph.created_at = data["created_at"]
        graph.updated_at = data["updated_at"]
        graph.metadata.update({
            k: (set(v) if k == "sources" else v)
            for k, v in data.get("metadata", {}).items()
        })

        # 重建实体索引
        for name, edata in data.get("entities", {}).items():
            entity = Entity.from_dict(edata)
            graph._entity_index[name.lower()] = entity
            graph.graph.add_node(name.lower(), type='entity', data=entity)

        # 重建关系
        for rdata in data.get("relationships", []):
            rel = Relationship.from_dict(rdata)
            graph._relation_index.append(rel)
            graph.graph.add_edge(rel.source.lower(), rel.target.lower(),
                               key=rel.relation.lower(), data=rel)

        # 重建命题
        for pdata in data.get("propositions", []):
            prop = Proposition.from_dict(pdata)
            graph._proposition_index.append(prop)
            prop_id = f"{prop.subject}-{prop.predicate}-{prop.object}"[:50]
            graph.graph.add_node(prop_id, type='proposition', data=prop)

        # 更新计数
        graph.metadata["entity_count"] = len(graph._entity_index)
        graph.metadata["relationship_count"] = len(graph._relation_index)
        graph.metadata["proposition_count"] = len(graph._proposition_index)

        print(f"  Graph loaded: {filepath}")
        return graph

    # ==================== 分析 ====================

    def get_statistics(self) -> dict:
        """获取图谱统计信息"""
        entity_types = Counter(e.type for e in self._entity_index.values())
        relation_types = Counter(r.relation for r in self._relation_index)

        # 计算图的连通分量
        connected_components = list(nx.weakly_connected_components(self.graph))

        return {
            "total_entities": self.metadata["entity_count"],
            "total_relationships": self.metadata["relationship_count"],
            "total_propositions": self.metadata["proposition_count"],
            "entity_types": dict(entity_types),
            "relation_types": dict(relation_types),
            "connected_components": len(connected_components),
            "largest_component": max(len(c) for c in connected_components) if connected_components else 0,
            "avg_entity_degree": round(
                sum(dict(self.graph.degree()).values()) / max(self.metadata["entity_count"], 1), 2
            ),
        }

    def get_isolated_entities(self) -> list:
        """查找孤立实体 (没有关系的实体)"""
        return [
            name for name in self._entity_index
            if name not in self.graph.nodes() or
            self.graph.out_degree(name) == 0 and self.graph.in_degree(name) == 0
        ]

    def find_conflicts(self) -> list:
        """
        查找潜在冲突

        检测逻辑:
        1. 同一实体有不同描述
        2. 循环关系 (A→B→C→A)
        3. 矛盾关系 (同一对实体有多个互斥关系)
        """
        conflicts = []

        # 1. 同一对实体有多个不同关系
        pair_relations = defaultdict(set)
        for rel in self._relation_index:
            pair_key = tuple(sorted([rel.source.lower(), rel.target.lower()]))
            pair_relations[pair_key].add(rel.relation.lower())

        for pair, rels in pair_relations.items():
            if len(rels) > 3:  # 太多关系可能是冗余
                conflicts.append({
                    "type": "high_connectivity",
                    "entities": pair,
                    "relations": list(rels),
                    "severity": "low",
                })

        # 2. 循环关系检测
        cycles = list(nx.simple_cycles(self.graph))
        for cycle in cycles[:10]:  # 只检查前10个
            if len(cycle) <= 3:
                conflicts.append({
                    "type": "circular_relation",
                    "cycle": cycle,
                    "severity": "info",
                })

        return conflicts
