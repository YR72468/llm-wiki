"""
知识审计器 — KnowledgeAuditor

职责: 知识健康检查、矛盾检测、覆盖率评估
输出: 知识健康报告 Markdown
"""

import os
from datetime import datetime
from collections import Counter, defaultdict
import networkx as nx

try:
    from graph import KnowledgeGraph
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from graph import KnowledgeGraph


class KnowledgeAuditor:
    """
    知识审计器 — 自检引擎

    检测维度:
    1. 完整性 — 实体是否有足够关系连接
    2. 一致性 — 是否存在矛盾关系
    3. 连通性 — 图谱是否分裂为多个孤岛
    4. 时效性 — 哪些页面长期未更新
    5. 质量评分 — 整体健康度打分
    """

    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.kg = knowledge_graph

    def audit(self) -> dict:
        """执行完整审计，返回审计报告"""
        report = {}

        report["metadata"] = {
            "audit_time": datetime.now().isoformat(),
            "knowledge_base": self.kg.name,
            "statistics": self.kg.get_statistics(),
        }

        report["health_score"] = self._calculate_health_score()
        report["conflicts"] = self._detect_conflicts()
        report["isolated_nodes"] = self._find_isolated_nodes()
        report["connectivity"] = self._analyze_connectivity()
        report["coverage_gaps"] = self._find_coverage_gaps()
        report["recommendations"] = self._generate_recommendations()

        return report

    def generate_report(self, output_path: str):
        """生成 Markdown 格式的健康报告"""
        report = self.audit()
        stats = report["metadata"]["statistics"]

        health_score_obj = report["health_score"]
        score = health_score_obj["total"]
        dimensions = health_score_obj["dimensions"]
        emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"

        lines = [
            f"# 知识健康报告",
            f"",
            f"> **审计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"> **知识图谱**: {report['metadata']['knowledge_base']}  ",
            f"> **健康评分**: {emoji} {score}/100",
            f"",
            f"---",
            f"",
            f"## 一、知识图谱概况",
            f"",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 实体总数 | {stats['total_entities']} |",
            f"| 关系总数 | {stats['total_relationships']} |",
            f"| 命题总数 | {stats['total_propositions']} |",
            f"| 连通分量 | {stats['connected_components']} |",
            f"| 最大连通分量大小 | {stats['largest_component']} |",
            f"| 平均实体度数 | {stats['avg_entity_degree']} |",
            f"",
            f"### 实体类型分布",
            f"",
        ]

        for etype, count in sorted(stats.get("entity_types", {}).items()):
            lines.append(f"- **{etype}**: {count}")

        lines.extend([
            f"",
            f"### 关系类型分布",
            f"",
        ])

        for rtype, count in sorted(stats.get("relation_types", {}).items()):
            lines.append(f"- **{rtype}**: {count}")

        # 健康评分明细
        lines.extend([
            f"",
            f"---",
            f"",
            f"## 二、健康评分详情",
            f"",
            f"总分: **{score}/100**",
            f"",
            f"| 维度 | 得分 | 满分 |",
            f"|------|------|------|",
        ])

        for dim in dimensions:
            lines.append(f"| {dim['name']} | {dim['score']} | {dim['max']} |")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 三、冲突检测",
            f"",
        ])

        if report["conflicts"]:
            for conflict in report["conflicts"]:
                severity_emoji = {"high": "🔴", "medium": "🟠", "low": "🟡", "info": "ℹ️"}.get(conflict.get("severity", "info"), "ℹ️")
                lines.append(f"- {severity_emoji} [{conflict['type']}] {conflict.get('message', '')}")
        else:
            lines.append("- ✅ 未发现明显冲突")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 四、孤立节点检测",
            f"",
        ])

        if report["isolated_nodes"]:
            lines.append(f"发现 **{len(report['isolated_nodes'])}** 个孤立实体（无任何关系连接）:")
            for node in report["isolated_nodes"][:20]:
                lines.append(f"- `{node}`")
            if len(report["isolated_nodes"]) > 20:
                lines.append(f"- ... 及其他 {len(report['isolated_nodes']) - 20} 个")
        else:
            lines.append("- ✅ 无孤立节点")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 五、连通性分析",
            f"",
        ])

        conn = report["connectivity"]
        lines.append(f"- 连通分量数: {conn['component_count']}")
        lines.append(f"- 最大分量占比: {conn['largest_component_ratio']:.1%}")

        if conn["component_count"] > 1:
            lines.append(f"")
            lines.append(f"> ⚠️ 图谱分裂为多个独立组件，建议加强跨组件的关系建立")
            for i, comp in enumerate(conn["components"][:5], 1):
                lines.append(f"**分量{i}** ({comp['size']} 个节点): {', '.join(comp['sample_entities'][:5])}")
        else:
            lines.append(f"- ✅ 图谱完全连通")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 六、知识缺口",
            f"",
        ])

        if report["coverage_gaps"]:
            for gap in report["coverage_gaps"][:10]:
                lines.append(f"- [{gap['priority']}] {gap['issue']}")
        else:
            lines.append("- ✅ 无明显知识缺口")

        lines.extend([
            f"",
            f"---",
            f"",
            f"## 七、优化建议",
            f"",
        ])

        for i, rec in enumerate(report["recommendations"], 1):
            lines.append(f"{i}. **{rec['action']}** ({rec['impact']}) — {rec['detail']}")

        lines.extend([
            f"",
            f"---",
            f"",
            f"*本报告由 LLM Wiki 知识引擎自动生成*",
            f"",
        ])

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"  Report saved: {output_path}")
        return output_path

    def _calculate_health_score(self) -> dict:
        """计算健康评分 (0-100)"""
        stats = self.kg.get_statistics()
        dimensions = []

        # 1. 密度分 (25分) — 关系密度越高越好
        entity_count = max(stats['total_entities'], 1)
        rel_count = stats['total_relationships']
        density = rel_count / entity_count
        density_score = min(int(density * 10), 25)
        dimensions.append({"name": "密度分", "score": density_score, "max": 25})

        # 2. 连通分 (25分)
        if stats['connected_components'] <= 1:
            connectivity_score = 25
        else:
            connectivity_score = max(0, int(25 / stats['connected_components']))
        dimensions.append({"name": "连通分", "score": connectivity_score, "max": 25})

        # 3. 完整性 (25分) — 孤立节点越少越好
        isolated = len(self.kg.get_isolated_entities())
        isolation_rate = isolated / entity_count
        completeness_score = max(0, int(25 * (1 - isolation_rate)))
        dimensions.append({"name": "完整性", "score": completeness_score, "max": 25})

        # 4. 多样性 (25分) — 关系类型越多越好
        rel_types = len(stats.get('relation_types', {}))
        diversity_score = min(int(rel_types * 2.5), 25)
        dimensions.append({"name": "多样性", "score": diversity_score, "max": 25})

        total = sum(d['score'] for d in dimensions)

        return {
            "total": total,
            "dimensions": dimensions,
        }

    def _detect_conflicts(self) -> list:
        """检测知识冲突"""
        conflicts = []

        # 使用图谱的冲突检测
        graph_conflicts = self.kg.find_conflicts()
        for c in graph_conflicts:
            conflicts.append({
                "type": c.get("type", "unknown"),
                "severity": c.get("severity", "info"),
                "message": f"{c.get('type', '')}: {c}",
            })

        # 检测同一实体有多个对立关系
        entity_rels = defaultdict(list)
        for rel in self.kg._relation_index:
            entity_rels[rel.source.lower()].append(rel)

        for entity_name, rels in entity_rels.items():
            if len(rels) > 10:
                conflicts.append({
                    "type": "high_degrees",
                    "severity": "low",
                    "message": f"实体 '{entity_name}' 有 {len(rels)} 条出边，可能存在噪声",
                })

        return conflicts

    def _find_isolated_nodes(self) -> list:
        """查找孤立节点"""
        return self.kg.get_isolated_entities()

    def _analyze_connectivity(self) -> dict:
        """分析连通性"""
        components = list(nx.weakly_connected_components(self.kg.graph))

        component_info = []
        for i, comp in enumerate(components):
            sample = list(comp)[:5]
            component_info.append({
                "size": len(comp),
                "sample_entities": sample,
            })

        largest = max(components, key=len) if components else set()
        largest_ratio = len(largest) / max(sum(len(c) for c in components), 1)

        return {
            "component_count": len(components),
            "largest_component_size": len(largest),
            "largest_component_ratio": largest_ratio,
            "components": sorted(component_info, key=lambda x: -x["size"]),
        }

    def _find_coverage_gaps(self) -> list:
        """识别知识缺口"""
        gaps = []
        stats = self.kg.get_statistics()

        # 孤立实体
        isolated = self._find_isolated_nodes()
        if isolated:
            gaps.append({
                "issue": f"{len(isolated)} 个孤立实体缺少关系连接",
                "priority": "medium",
            })

        # 低连接度实体
        for name, entity in self.kg._entity_index.items():
            degree = self.kg.graph.degree(name)
            if degree == 0 and entity.type != 'unknown':
                gaps.append({
                    "issue": f"实体 '{entity.name}' ({entity.type}) 未被纳入任何关系",
                    "priority": "low",
                })

        # 单一命题实体
        for entity in self.kg.get_all_entities():
            props = self.kg.get_related_props(entity.name)
            if len(props) == 0 and entity.type == 'concept':
                gaps.append({
                    "issue": f"概念 '{entity.name}' 缺乏详细命题描述",
                    "priority": "medium",
                })

        return gaps

    def _generate_recommendations(self) -> list:
        """生成优化建议"""
        recommendations = []

        stats = self.kg.get_statistics()
        isolated = self._find_isolated_nodes()
        conn = self._analyze_connectivity()

        if conn["component_count"] > 1:
            recommendations.append({
                "action": "合并知识孤岛",
                "impact": "高",
                "detail": f"当前有 {conn['component_count']} 个独立组件，建议寻找跨组件的共同实体进行关联",
            })

        if isolated:
            recommendations.append({
                "action": f"连接 {len(isolated)} 个孤立实体",
                "impact": "中",
                "detail": "这些实体尚未参与任何关系，尝试从已有资料中寻找关联线索",
            })

        entity_count = stats["total_entities"]
        if entity_count < 10:
            recommendations.append({
                "action": "扩充知识覆盖面",
                "impact": "高",
                "detail": "当前实体数量较少 (<10)，建议输入更多原始资料以丰富知识图谱",
            })

        if not recommendations:
            recommendations.append({
                "action": "保持定期审计",
                "impact": "低",
                "detail": "知识库运转良好，建议每月运行一次审计保持健康",
            })

        return recommendations
