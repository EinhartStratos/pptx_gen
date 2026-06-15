from __future__ import annotations

from pathlib import Path
import json

from pptx_gen.config import LLMConfig, PipelinePaths
from pptx_gen.llm.client import build_llm_client
from pptx_gen.llm.generator import PageContentGenerator
from pptx_gen.ppt.builder import PPTBuilder
from pptx_gen.render.mermaid import MermaidRenderer
from pptx_gen.template.parser import TemplateRuleParser


class PipelineRunner:
    def __init__(self, paths: PipelinePaths, llm_config: LLMConfig, max_workers: int = 4, mermaid_cli: str = "mmdc") -> None:
        self.paths = paths
        self.llm_config = llm_config
        self.max_workers = max(max_workers, 1)
        self.mermaid_cli = mermaid_cli

    def run(self) -> dict[str, str]:
        self.paths.output_dir.mkdir(parents=True, exist_ok=True)
        self.paths.page_results_dir.mkdir(parents=True, exist_ok=True)
        self.paths.mermaid_dir.mkdir(parents=True, exist_ok=True)
        self.paths.rendered_dir.mkdir(parents=True, exist_ok=True)

        parser = TemplateRuleParser(self.paths.template_pptx)
        rules = parser.save(self.paths.rules_json)

        requirement_text = self.paths.requirement_text.read_text(encoding="utf-8").strip()
        page_rules = rules.to_dict()["pages"]

        client = build_llm_client(self.llm_config)
        generator = PageContentGenerator(client, max_workers=self.max_workers)
        page_results = generator.generate_all(requirement_text, page_rules, self.paths.page_results_dir)

        renderer = MermaidRenderer(self.mermaid_cli)
        if any(
            element.type == "image" and element.image_source_type == "mermaid" and element.mermaid_source.strip()
            for page in page_results
            for element in page.elements
        ):
            if not renderer.is_available():
                raise RuntimeError("检测到 Mermaid 图片任务，但当前环境找不到 mmdc 命令。")
            page_results = renderer.render_page_results(page_results, self.paths.mermaid_dir, self.paths.rendered_dir)
            self._persist_page_results(page_results)

        builder = PPTBuilder(self.paths.template_pptx)
        builder.build(self.paths.rules_json, self.paths.page_results_dir, self.paths.final_pptx)

        return {
            "rules_json": str(self.paths.rules_json),
            "page_results_dir": str(self.paths.page_results_dir),
            "rendered_dir": str(self.paths.rendered_dir),
            "final_pptx": str(self.paths.final_pptx),
        }

    def _persist_page_results(self, page_results) -> None:
        for page in page_results:
            output_path = self.paths.page_results_dir / f"page_{page.page_no:02d}.json"
            output_path.write_text(json.dumps(page.to_dict(compact=True), ensure_ascii=False, indent=2), encoding="utf-8")
