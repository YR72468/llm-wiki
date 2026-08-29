"""
LLM Wiki 知识引擎 — 主入口

使用方式:
  python main.py --input examples/sample.md --output knowledge-base/
  python main.py --input examples/ --output knowledge-base/ --incremental
  python main.py --audit --graph knowledge-base/graph.json --report output/health-report.md
"""

import argparse
import json
import os
import sys
import glob
from pathlib import Path
from datetime import datetime

# 确保可以导入同目录下的模块
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

os.chdir(_here)

# Import from knowledge-engine subdirectory
_knowledge_engine_dir = os.path.join(_here, 'knowledge-engine')
if _knowledge_engine_dir not in sys.path:
    sys.path.insert(0, _knowledge_engine_dir)

from graph import KnowledgeGraph
from extractor import KnowledgeExtractor
from generator import PageGenerator
from auditor import KnowledgeAuditor
from updater import KnowledgeUpdater


def run_full_pipeline(input_files: list, output_dir: str, incremental: bool = False):
    """
    完整三阶段流水线: 抽取 → 构建/更新 → 生成/审计
    """
    print(f"\n{'='*60}")
    print(f"  LLM Wiki 知识引擎 — 三阶段自动化流水线")
    print(f"{'='*60}")
    print(f"  输入: {input_files}")
    print(f"  输出: {output_dir}")
    print(f"  模式: {'增量更新' if incremental else '全新构建'}")
    print(f"{'='*60}\n")

    # ========== Phase 0: 初始化 ==========
    kg = KnowledgeGraph(name="my_wiki")
    extractor = KnowledgeExtractor()
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 如果增量模式，加载已有图谱
    graph_file = os.path.join(output_dir, "graph.json")
    if incremental and os.path.exists(graph_file):
        kg = KnowledgeGraph.load(graph_file)

    # ========== Phase 1: 内容整合 (Extract) ==========
    print(f"\n{'─'*60}")
    print(f"  PHASE 1: 内容整合 — 知识抽取")
    print(f"{'─'*60}\n")

    for filepath in input_files:
        if not os.path.exists(filepath):
            print(f"  ⚠️  跳过不存在文件: {filepath}")
            continue

        print(f"  📂 处理: {filepath}")

        # 读取文本
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        # 提取知识
        unit = extractor.extract(text, source_doc=os.path.basename(filepath))

        # 预览抽取结果
        print(f"      实体: {len(unit.entities)}, "
              f"关系: {len(unit.relationships)}, "
              f"命题: {len(unit.propositions)}")

        # 如果有重复检测
        if incremental:
            updater = KnowledgeUpdater(kg)
            duplicates = updater.detect_duplicates(unit)
            if duplicates:
                print(f"      ⚠️  发现 {len(duplicates)} 个重复实体")
                for dup in duplicates[:3]:
                    print(f"        - {dup['name']} ({dup['match_type']})")

        # 导入图谱
        added = kg.ingest(unit)
        print(f"      → 净新增: {added} 个条目")

    # 保存图谱
    kg.save(graph_file)

    # ========== Phase 2: 动态更新 (Generate) ==========
    print(f"\n{'─'*60}")
    print(f"  PHASE 2: 动态更新 — 页面生成")
    print(f"{'─'*60}\n")

    generator = PageGenerator(kg, output_dir)
    generator.generate_all()

    # ========== Phase 3: 自检优化 (Audit) ==========
    print(f"\n{'─'*60}")
    print(f"  PHASE 3: 自检优化 — 健康审计")
    print(f"{'─'*60}\n")

    auditor = KnowledgeAuditor(kg)
    report_path = os.path.join(output_dir, "..", "output", "health-report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    auditor.generate_report(report_path)

    # 保存更新日志
    if incremental:
        updater = KnowledgeUpdater(kg)
        log_path = os.path.join(output_dir, "update-log.json")
        updater.save_update_log(log_path)

    # ========== 完成 ==========
    print(f"\n{'='*60}")
    print(f"  ✅ 流水线完成!")
    print(f"{'='*60}")

    stats = kg.get_statistics()
    print(f"\n  统计:")
    print(f"    实体: {stats['total_entities']}")
    print(f"    关系: {stats['total_relationships']}")
    print(f"    命题: {stats['total_propositions']}")

    health = auditor.audit()["health_score"]["total"]
    print(f"    健康评分: {health}/100")

    print(f"\n  输出目录: {output_dir}/")
    print(f"  图谱文件: {graph_file}")
    print(f"  健康报告: {report_path}")


def run_audit_only(graph_file: str, output_path: str):
    """单独运行审计"""
    print(f"\n{'='*60}")
    print(f"  LLM Wiki — 知识健康审计")
    print(f"{'='*60}")
    print(f"  加载图谱: {graph_file}")

    kg = KnowledgeGraph.load(graph_file)
    auditor = KnowledgeAuditor(kg)
    auditor.generate_report(output_path)

    print(f"\n  ✅ 审计完成!")


def main():
    parser = argparse.ArgumentParser(description="LLM Wiki 知识引擎")
    parser.add_argument("--input", "-i", nargs="+", default=["examples/sample.md"],
                       help="输入文件或目录")
    parser.add_argument("--output", "-o", default="knowledge-base",
                       help="输出目录")
    parser.add_argument("--incremental", action="store_true",
                       help="增量更新模式")
    parser.add_argument("--audit", action="store_true",
                       help="仅运行审计")
    parser.add_argument("--graph", default="knowledge-base/graph.json",
                       help="图谱文件路径 (仅 --audit)")
    parser.add_argument("--report", default="output/health-report.md",
                       help="报告输出路径 (仅 --audit)")

    args = parser.parse_args()

    # 处理输入路径
    input_files = []
    for inp in args.input:
        if os.path.isdir(inp):
            for ext in ['*.md', '*.txt', '*.json']:
                input_files.extend(glob.glob(os.path.join(inp, ext)))
        else:
            input_files.append(inp)

    input_files = list(set(input_files))  # 去重

    if args.audit:
        run_audit_only(args.graph, args.report)
    else:
        run_full_pipeline(input_files, args.output, args.incremental)


if __name__ == "__main__":
    main()
