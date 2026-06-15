from __future__ import annotations

import argparse
import json
from pathlib import Path

from pptx_gen.config import LLMConfig, PipelinePaths
from pptx_gen.llm.client import build_llm_client
from pptx_gen.llm.generator import PageContentGenerator
from pptx_gen.pipeline.runner import PipelineRunner
from pptx_gen.ppt.builder import PPTBuilder
from pptx_gen.render.mermaid import MermaidRenderer
from pptx_gen.template.parser import TemplateRuleParser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pptx_gen", description="PPT 模板解析、分页生成与组装工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract-template", help="解析模板并输出规则 JSON")
    extract_parser.add_argument("--template", required=True)
    extract_parser.add_argument("--output", required=True)

    generate_parser = subparsers.add_parser("generate-pages", help="按页并发生成内容 JSON")
    generate_parser.add_argument("--requirement", required=True)
    generate_parser.add_argument("--rules", required=True)
    generate_parser.add_argument("--output-dir", required=True)
    generate_parser.add_argument("--max-workers", type=int, default=4)

    render_parser = subparsers.add_parser("render-mermaid", help="把 Mermaid 文本渲染为 PNG")
    render_parser.add_argument("--pages-dir", required=True)
    render_parser.add_argument("--mermaid-dir", required=True)
    render_parser.add_argument("--rendered-dir", required=True)
    render_parser.add_argument("--cli-command", default="mmdc")

    build_parser_cmd = subparsers.add_parser("build-ppt", help="根据页面结果组装最终 PPT")
    build_parser_cmd.add_argument("--template", required=True)
    build_parser_cmd.add_argument("--rules", required=True)
    build_parser_cmd.add_argument("--pages-dir", required=True)
    build_parser_cmd.add_argument("--output", required=True)

    pipeline_parser = subparsers.add_parser("run-pipeline", help="执行完整首版流水线")
    pipeline_parser.add_argument("--template", required=True)
    pipeline_parser.add_argument("--requirement", required=True)
    pipeline_parser.add_argument("--output-dir", required=True)
    pipeline_parser.add_argument("--max-workers", type=int, default=4)
    pipeline_parser.add_argument("--mermaid-cli", default="mmdc")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "extract-template":
        TemplateRuleParser(args.template).save(args.output)
        print(args.output)
        return

    if args.command == "generate-pages":
        rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
        requirement_text = Path(args.requirement).read_text(encoding="utf-8")
        client = build_llm_client(LLMConfig.from_env())
        generator = PageContentGenerator(client, max_workers=args.max_workers)
        generator.generate_all(requirement_text, rules["pages"], args.output_dir)
        print(args.output_dir)
        return

    if args.command == "render-mermaid":
        renderer = MermaidRenderer(args.cli_command)
        if not renderer.is_available():
            raise RuntimeError(f"找不到 Mermaid CLI 命令: {args.cli_command}")
        pages = _load_pages(args.pages_dir)
        renderer.render_page_results(pages, args.mermaid_dir, args.rendered_dir)
        _save_pages(args.pages_dir, pages)
        print(args.rendered_dir)
        return

    if args.command == "build-ppt":
        PPTBuilder(args.template).build(args.rules, args.pages_dir, args.output)
        print(args.output)
        return

    if args.command == "run-pipeline":
        runner = PipelineRunner(
            paths=PipelinePaths(
                template_pptx=Path(args.template),
                requirement_text=Path(args.requirement),
                output_dir=Path(args.output_dir),
            ),
            llm_config=LLMConfig.from_env(),
            max_workers=args.max_workers,
            mermaid_cli=args.mermaid_cli,
        )
        outputs = runner.run()
        print(json.dumps(outputs, ensure_ascii=False, indent=2))
        return

    raise ValueError(f"不支持的命令: {args.command}")


def _load_pages(pages_dir: str | Path) -> list:
    from pptx_gen.schemas import PageGenerationResult

    root = Path(pages_dir)
    pages = []
    for path in sorted(root.glob("page_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        pages.append(PageGenerationResult.model_validate(payload))
    return pages


def _save_pages(pages_dir: str | Path, pages: list) -> None:
    root = Path(pages_dir)
    root.mkdir(parents=True, exist_ok=True)
    for page in pages:
        path = root / f"page_{page.page_no:02d}.json"
        path.write_text(json.dumps(page.to_dict(compact=True), ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
