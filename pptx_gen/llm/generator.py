from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json

from pptx_gen.llm.client import BaseLLMClient
from pptx_gen.llm.prompts import build_system_prompt, build_user_prompt
from pptx_gen.schemas import PageGenerationResult


class PageContentGenerator:
    def __init__(self, client: BaseLLMClient, max_workers: int = 4) -> None:
        self.client = client
        self.max_workers = max(max_workers, 1)

    def generate_all(self, requirement_text: str, page_rules: list[dict], output_dir: str | Path) -> list[PageGenerationResult]:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        system_prompt = build_system_prompt()
        results: dict[int, PageGenerationResult] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {
                executor.submit(self._generate_one, requirement_text, page_rule, system_prompt): page_rule
                for page_rule in page_rules
            }
            for future in as_completed(future_map):
                page_rule = future_map[future]
                page_no = int(page_rule["page_no"])
                try:
                    result = future.result()
                except Exception as exc:
                    result = PageGenerationResult(
                        page_no=page_no,
                        should_generate=False,
                        skip_reason=f"页面生成失败: {exc}",
                        elements=[],
                    )
                results[page_no] = result
                output_path = target_dir / f"page_{page_no:02d}.json"
                output_path.write_text(json.dumps(result.to_dict(compact=True), ensure_ascii=False, indent=2), encoding="utf-8")
        return [results[index] for index in sorted(results)]

    def _generate_one(self, requirement_text: str, page_rule: dict, system_prompt: str) -> PageGenerationResult:
        user_prompt = build_user_prompt(requirement_text, page_rule)
        return self.client.generate_page(requirement_text, page_rule, system_prompt, user_prompt)
