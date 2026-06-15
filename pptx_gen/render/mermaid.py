from __future__ import annotations

from pathlib import Path
import importlib.util
import os
import shlex
import shutil
import struct
import subprocess
import sys
import zlib

from pptx_gen.mermaid_utils import normalize_mermaid_source
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
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        output_log = "\n".join(item for item in [stderr, stdout] if item).strip()
        if completed.returncode != 0:
            raise RuntimeError(self._build_render_error(output_log or "Mermaid 渲染失败。", command, target))
        if "ERROR" in output_log.upper():
            raise RuntimeError(self._build_render_error(output_log, command, target))
        validation_error = self._validate_rendered_output(target)
        if validation_error:
            message = validation_error if not output_log else f"{validation_error}\n{output_log}"
            raise RuntimeError(self._build_render_error(message, command, target))
        return target

    def _resolve_command(self) -> list[str] | None:
        command_parts = shlex.split(self.cli_command, posix=os.name != "nt")
        if not command_parts:
            return None
        if len(command_parts) > 1:
            found = shutil.which(command_parts[0])
            if found:
                return [found, *command_parts[1:]]
            explicit_path = Path(command_parts[0])
            if explicit_path.exists():
                return [str(explicit_path), *command_parts[1:]]
            return None

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

    def _build_render_error(self, details: str, command: list[str], target: Path) -> str:
        message = f"Mermaid 渲染失败，目标文件：{target}\n{details}".strip()
        if self._looks_like_legacy_python_mmdc(command):
            message += (
                "\n当前环境解析到的是 Python 版 mmdc（PhantomJS），"
                "它对中文和 classDiagram 等新版 Mermaid 语法兼容性较差。"
                "建议改用 Node 版 @mermaid-js/mermaid-cli，"
                '并通过 --cli-command "npx.cmd -y @mermaid-js/mermaid-cli" 或已安装的 mmdc.cmd 指定。'
            )
        return message

    def _looks_like_legacy_python_mmdc(self, command: list[str]) -> bool:
        if len(command) >= 3 and command[1] == "-m" and command[2] == "mmdc":
            return True
        executable_name = Path(command[0]).name.lower()
        return executable_name == "mmdc.exe"

    def _validate_rendered_output(self, target: Path) -> str | None:
        if not target.exists():
            return "Mermaid 未生成输出文件。"
        if target.suffix.lower() == ".png" and self._is_blank_png(target):
            return "Mermaid 生成了空白 PNG。"
        return None

    def _is_blank_png(self, target: Path) -> bool:
        try:
            payload = target.read_bytes()
            if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
                return False

            cursor = 8
            idat_chunks = bytearray()
            while cursor + 8 <= len(payload):
                chunk_length = struct.unpack(">I", payload[cursor : cursor + 4])[0]
                chunk_type = payload[cursor + 4 : cursor + 8]
                chunk_data = payload[cursor + 8 : cursor + 8 + chunk_length]
                if chunk_type == b"IDAT":
                    idat_chunks.extend(chunk_data)
                cursor += chunk_length + 12

            if not idat_chunks:
                return False

            decoded = zlib.decompress(bytes(idat_chunks))
            return bool(decoded) and all(byte == 0 for byte in decoded)
        except Exception:
            return False

    def render_page_results(self, page_results: list[PageGenerationResult], mermaid_dir: str | Path, rendered_dir: str | Path) -> list[PageGenerationResult]:
        mermaid_root = Path(mermaid_dir)
        rendered_root = Path(rendered_dir)
        mermaid_root.mkdir(parents=True, exist_ok=True)
        rendered_root.mkdir(parents=True, exist_ok=True)
        for result in page_results:
            for element in result.elements:
                if element.type != "image" or element.image_source_type != "mermaid" or not element.mermaid_source.strip():
                    continue
                mermaid_syntax, mermaid_source = normalize_mermaid_source(element.diagram_kind, element.mermaid_source)
                if mermaid_syntax:
                    element.mermaid_syntax = mermaid_syntax
                if mermaid_source:
                    element.mermaid_source = mermaid_source
                mermaid_path = mermaid_root / f"page_{result.page_no:02d}_{element.id}.mmd"
                png_path = rendered_root / f"page_{result.page_no:02d}_{element.id}.png"
                mermaid_path.write_text(element.mermaid_source, encoding="utf-8")
                self.render_file(mermaid_path, png_path)
                element.rendered_path = str(png_path)
        return page_results
