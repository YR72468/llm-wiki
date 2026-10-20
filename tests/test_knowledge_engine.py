"""
LLM Wiki 单元测试套件
测试知识图谱核心功能
"""

import pytest
import json
from pathlib import Path
from knowledge_engine.graph import KnowledgeGraph
from knowledge_engine.extractor import KnowledgeExtractor


class TestKnowledgeGraph:
    """知识图谱核心功能测试"""

    def test_init_graph(self):
        """测试图谱初始化"""
        graph = KnowledgeGraph(name="test_wiki")
        assert graph.name == "test_wiki"
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_node(self):
        """测试添加节点"""
        graph = KnowledgeGraph()
        node = graph.add_node("Python", type="concept")
        assert node.id == "Python"
        assert node.type == "concept"

    def test_add_edge(self):
        """测试添加关系"""
        graph = KnowledgeGraph()
        graph.add_node("Python")
        graph.add_node("Language")
        edge = graph.add_edge("Python", "is_a", "Language")
        assert edge.source == "Python"
        assert edge.target == "Language"

    def test_save_and_load(self, tmp_path):
        """测试图谱持久化"""
        graph = KnowledgeGraph()
        graph.add_node("Test")
        graph.add_edge("Test", "related", "Concept")

        # Save
        graph_path = tmp_path / "graph.json"
        graph.save(graph_path)
        assert graph_path.exists()

        # Load
        loaded = KnowledgeGraph.load(graph_path)
        assert len(loaded.nodes) == 2
        assert len(loaded.edges) == 1


class TestKnowledgeExtractor:
    """知识抽取器测试"""

    def test_extract_entities(self):
        """测试实体抽取"""
        extractor = KnowledgeExtractor()
        text = "Python是一种面向对象的高级编程语言。"

        entities = extractor.extract_entities(text)
        assert len(entities) > 0

    def test_extract_relations(self):
        """测试关系抽取"""
        extractor = KnowledgeExtractor()
        text = "Python由Guido van Rossum创建。"

        relations = extractor.extract_relations(text)
        assert len(relations) > 0


@pytest.fixture
def sample_graph():
    """测试用样本图谱"""
    return {
        "nodes": [
            {"id": "Python", "type": "language"},
            {"id": "AI", "type": "concept"}
        ],
        "edges": [
            {"source": "Python", "target": "AI", "relation": "used_for"}
        ]
    }


def test_graph_validation(sample_graph):
    """测试图谱完整性验证"""
    # 验证节点存在
    for edge in sample_graph["edges"]:
        sources = [n["id"] for n in sample_graph["nodes"]]
        assert edge["source"] in sources
        assert edge["target"] in sources
