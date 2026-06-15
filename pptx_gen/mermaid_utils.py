from __future__ import annotations

import re


_GROUP_RE = re.compile(r"^group\s+(?P<id>[A-Za-z_][A-Za-z0-9_-]*)\([^)]*\)\[(?P<label>.+)\]$")
_SERVICE_RE = re.compile(
    r"^service\s+(?P<id>[A-Za-z_][A-Za-z0-9_-]*)\([^)]*\)\[(?P<label>.+)\](?:\s+in\s+(?P<group>[A-Za-z_][A-Za-z0-9_-]*))?$"
)


def normalize_mermaid_source(diagram_kind: str | None, mermaid_source: str | None) -> tuple[str, str]:
    source = (mermaid_source or "").strip()
    if not source:
        return "", ""

    first_line = _first_non_empty_line(source)
    if first_line == "architecture-beta":
        normalized = _convert_architecture_beta_to_class_diagram(source)
        return _first_non_empty_line(normalized), normalized

    return first_line, source


def _convert_architecture_beta_to_class_diagram(source: str) -> str:
    logical_lines = _to_logical_lines(source)
    if not logical_lines:
        return 'classDiagram\n  class Diagram["系统架构图"]'

    group_labels: dict[str, str] = {}
    service_labels: dict[str, str] = {}
    service_groups: dict[str, str] = {}
    service_order: list[str] = []
    edge_lines: list[str] = []

    for line in logical_lines[1:]:
        if line.startswith("group "):
            match = _GROUP_RE.match(line)
            if match:
                group_labels[match.group("id")] = _clean_label(match.group("label"))
            continue

        if line.startswith("service "):
            match = _SERVICE_RE.match(line)
            if match:
                service_id = match.group("id")
                if service_id not in service_labels:
                    service_order.append(service_id)
                service_labels[service_id] = _clean_label(match.group("label"))
                group_id = match.group("group")
                if group_id:
                    service_groups[service_id] = group_id
            continue

        if line.startswith("junction "):
            continue

        if "--" in line or ".." in line:
            edge_lines.append(line)

    if not service_labels:
        return 'classDiagram\n  class Diagram["系统架构图"]'

    rendered_lines = ["classDiagram", "  direction LR"]
    grouped_service_ids: set[str] = set()
    for group_id, label in group_labels.items():
        members = [service_id for service_id in service_order if service_groups.get(service_id) == group_id]
        if not members:
            continue
        rendered_lines.append(f'  namespace {group_id}["{label}"] {{')
        for service_id in members:
            grouped_service_ids.add(service_id)
            rendered_lines.append(f'    class {service_id}["{service_labels[service_id]}"]')
        rendered_lines.append("  }")

    for service_id in service_order:
        if service_id in grouped_service_ids:
            continue
        rendered_lines.append(f'  class {service_id}["{service_labels[service_id]}"]')

    known_nodes = set(service_labels)
    for edge_line in edge_lines:
        edge = _convert_edge_line(edge_line, known_nodes)
        if edge:
            rendered_lines.append(f"  {edge}")

    return "\n".join(rendered_lines)


def _convert_edge_line(line: str, known_nodes: set[str]) -> str | None:
    arrow = _extract_arrow(line)
    if arrow is None:
        return None

    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_-]*", line)
    nodes = [token for token in tokens if token in known_nodes]
    if len(nodes) < 2:
        return None

    src, dst = nodes[0], nodes[1]
    label = _extract_edge_label(line)
    edge = f"{src} {arrow} {dst}"
    if label:
        edge += f" : {label}"
    return edge


def _extract_arrow(line: str) -> str | None:
    if "<-->" in line:
        return "<-->"
    if "-->" in line:
        return "-->"
    if "<--" in line:
        return "<--"
    if "--" in line:
        return "--"
    if "..>" in line:
        return "..>"
    if ".." in line:
        return ".."
    return None


def _extract_edge_label(line: str) -> str:
    match = re.search(r"\s:\s(.+)$", line)
    if match is None:
        return ""
    label = match.group(1).strip()
    if re.fullmatch(r"[RTBL]", label):
        return ""
    return _clean_label(label)


def _to_logical_lines(source: str) -> list[str]:
    logical_lines: list[str] = []
    buffer = ""
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not buffer:
            buffer = line
        else:
            buffer = f"{buffer} {line}"
        if _brackets_balanced(buffer):
            logical_lines.append(buffer)
            buffer = ""
    if buffer:
        logical_lines.append(buffer)
    return logical_lines


def _brackets_balanced(line: str) -> bool:
    pairs = [("[", "]"), ("(", ")"), ("{", "}")]
    return all(line.count(left) <= line.count(right) for left, right in pairs)


def _clean_label(label: str) -> str:
    cleaned = label.replace("\\n", " ")
    cleaned = cleaned.replace("\n", " ")
    cleaned = cleaned.replace('"', "'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _first_non_empty_line(source: str) -> str:
    return next((line.strip() for line in source.splitlines() if line.strip()), "")
