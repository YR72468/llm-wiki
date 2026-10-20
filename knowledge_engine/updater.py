"""
增量更新器 — KnowledgeUpdater

职责: 处理新资料的增量更新，检测重复/矛盾/新概念
工作流:
  1. 对比新旧知识，识别新增实体/关系
  2. 检测冲突：同一实体有不同属性/描述
  3. 合并变更到主图谱
  4. 记录更新历史
"""

import json
import os
from datetime import datetime
from collections import defaultdict
from typing import Optional

try:
    from graph import KnowledgeGraph
    from extractor import Entity, Relationship, KnowledgeUnit
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from graph import KnowledgeGraph
    from extractor import Entity, Relationship, KnowledgeUnit


class UpdateLog:
    """更新日志"""

    def __init__(self):
        self.entries = []

    def add(self, action: str, details: dict):
        self.entries.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
        })

    def to_dict(self):
        return {"entries": self.entries}

    def save(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class KnowledgeUpdater:
    """
    增量更新管理器

    核心功能:
    1. diff — 对比两个图谱的差异
    2. merge — 将新图谱合并到旧图谱
    3. conflict_resolution — 标记/解决冲突
    4. update_log — 记录所有变更
    """

    def __init__(self, existing_kg: KnowledgeGraph):
        self.existing_kg = existing_kg
        self.update_log = UpdateLog()

    def ingest_new_source(self, new_unit: KnowledgeUnit) -> dict:
        """
        将新资料导入现有图谱

        Returns:
            更新统计: {added, merged, conflicted, unchanged}
        """
        stats = {
            "entities_added": 0,
            "entities_merged": 0,
            "relationships_added": 0,
            "conflicts_detected": 0,
            "unchanged": 0,
        }

        # 处理新实体
        for entity in new_unit.entities:
            name_lower = entity.name.lower()
            existing = self.existing_kg.get_entity(entity.name)

            if existing is None:
                # 全新实体
                self.existing_kg.add_entity(entity)
                stats["entities_added"] += 1
                self.update_log.add("new_entity", {
                    "name": entity.name,
                    "type": entity.type,
                    "source": entity.source,
                })
            else:
                # 实体已存在 — 检查是否需要合并
                merged = self._merge_entity_updates(existing, entity)
                if merged:
                    stats["entities_merged"] += 1
                    stats["conflicts_detected"] += merged.get("conflicts", 0)
                    self.update_log.add("merged_entity", {
                        "name": entity.name,
                        "conflicts": merged.get("conflicts", 0),
                    })
                else:
                    stats["unchanged"] += 1

        # 处理新关系
        for rel in new_unit.relationships:
            added = self.existing_kg.add_relationship(rel)
            if added:
                stats["relationships_added"] += 1
                self.update_log.add("new_relationship", {
                    "source": rel.source,
                    "target": rel.target,
                    "relation": rel.relation,
                })
            else:
                stats["unchanged"] += 1

        # 处理命题
        for prop in new_unit.propositions:
            self.existing_kg.add_proposition(prop)

        return stats

    def _merge_entity_updates(self, existing: Entity, new: Entity) -> dict:
        """
        尝试合并已有实体与新实体的差异

        Returns:
            dict 包含合并结果和冲突信息
        """
        conflicts = 0

        # 合并属性
        for k, v in new.attributes.items():
            if k in existing.attributes:
                # 同一属性键有不同值 — 冲突！
                if existing.attributes[k] != v:
                    conflicts += 1
                    existing.attributes[k] = [existing.attributes[k], v]  # 保留两者
            else:
                existing.attributes[k] = v

        # 合并描述
        if new.description and not existing.description:
            existing.description = new.description
        elif new.description and existing.description != new.description:
            # 描述有差异 — 记录但不过度处理
            conflicts += 1

        self.existing_kg.updated_at = datetime.now().isoformat()

        if conflicts > 0:
            return {"merged": True, "conflicts": conflicts}

        return {"merged": False}

    def detect_duplicates(self, new_unit: KnowledgeUnit) -> list:
        """
        检测新资料中与已有图谱的重复内容

        Returns:
            重复列表: [{"name": "...", "match_type": "exact|similar", "confidence": ...}]
        """
        duplicates = []

        for entity in new_unit.entities:
            existing = self.existing_kg.get_entity(entity.name)
            if existing:
                duplicates.append({
                    "name": entity.name,
                    "match_type": "exact",
                    "confidence": 1.0,
                    "type": entity.type,
                })

        # TODO: 模糊匹配 — 可以使用编辑距离或语义相似度
        return duplicates

    def get_update_history(self) -> dict:
        """获取更新历史记录"""
        return self.update_log.to_dict()

    def save_update_log(self, filepath: str):
        """保存更新日志"""
        self.update_log.save(filepath)
        print(f"  Update log saved: {filepath}")

    def preview_changes(self, new_unit: KnowledgeUnit) -> dict:
        """
        预览变更 — 不做实际修改

        Returns:
            变更预览信息
        """
        return {
            "new_entities": [e.name for e in new_unit.entities
                           if not self.existing_kg.get_entity(e.name)],
            "existing_entities": [e.name for e in new_unit.entities
                                 if self.existing_kg.get_entity(e.name)],
            "new_relationships": [f"{r.source}->{r.relation}->{r.target}"
                                  for r in new_unit.relationships],
            "total_changes": len(new_unit.entities) + len(new_unit.relationships),
        }
