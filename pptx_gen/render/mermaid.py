from __future__ import annotations

from pathlib import Path
import importlib.util
import os
import shutil
import subprocess
import sys

from pptx_gen.schemas import PageGenerationResult


class MermaidRenderer:
    def __init__(self, cli_command: str = "mmdc") -> None:
        self.cli_command = cli_command

    def is_available(self) -> bool:
        return self._resolve_command() is not None

    def render_file(self, input_path: str | Path, output_path: str | Path, theme: str = "neutral") -> Path:
        source = Path(input_path)
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        base_command = self._resolve_command()
        if base_command is None:
            raise RuntimeError(f"找不到 Mermaid CLI 命令: {self.cli_command}")
        command = [
            *base_command,
            "-i",
            str(source),
            "-o",
            str(target),
            "-t",
            theme,
            "-b",
            "transparent",
        ]
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=env,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Mermaid 渲染失败。")
        return target

    def _resolve_command(self) -> list[str] | None:
        found = shutil.which(self.cli_command)
        if found:
            return [found]

        python_dir = Path(sys.executable).resolve().parent
        candidate_names = [self.cli_command]
        if os.name == "nt" and not self.cli_command.lower().endswith(".exe"):
            candidate_names.insert(0, f"{self.cli_command}.exe")

        for name in candidate_names:
            candidate = python_dir / name
            if candidate.exists():
                return [str(candidate)]

        if self.cli_command == "mmdc" and importlib.util.find_spec("mmdc") is not None:
            return [sys.executable, "-m", "mmdc"]

        return None

    def render_page_results(self, page_results: list[PageGenerationResult], mermaid_dir: str | Path, rendered_dir: str | Path) -> list[PageGenerationResult]:
        mermaid_root = Path(mermaid_dir)
        rendered_root = Path(rendered_dir)
        mermaid_root.mkdir(parents=True, exist_ok=True)
        rendered_root.mkdir(parents=True, exist_ok=True)
        for result in page_results:
            for element in result.elements:
                if element.type != "image" or element.image_source_type != "mermaid" or not element.mermaid_source.strip():
                    continue
                mermaid_path = mermaid_root / f"page_{result.page_no:02d}_{element.id}.mmd"
                png_path = rendered_root / f"page_{result.page_no:02d}_{element.id}.png"
                mermaid_path.write_text(element.mermaid_source, encoding="utf-8")
                self.render_file(mermaid_path, png_path)
                element.rendered_path = str(png_path)
        return page_results
