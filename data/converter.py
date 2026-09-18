"""
Schema thống nhất 1 record / 1 bảng:

{
    "image_id": str,
    "image_path": str,
    "source_dataset": str,            # "PubTables-1M" | "FinTabNet" | ...
    "table_id": int,

    "annotation_level": str,          # "detection_only" | "structure" | "full"
                                       #   detection_only: chỉ có table_bbox (vd TableBank, ViFinTab)
                                       #   structure:      có cells/rows/cols nhưng không có text
                                       #   full:           có cả text trong từng cell (vd FinTabNet)

    "table_bbox": [x1, y1, x2, y2],   # bbox axis-aligned, LUÔN có (suy ra từ table_quad nếu cần)
    "table_quad": [[x, y]] * 4,       # 4 đỉnh theo chiều kim đồng hồ, dùng cho bảng nghiêng/cong (WTW)
                                       #   nếu dataset gốc chỉ có rectangle -> quad = 4 góc của table_bbox

    "num_rows": int,
    "num_cols": int,
    "cells": [                        # rỗng [] nếu annotation_level == "detection_only"
        {
            "row_start": int,
            "row_end": int,
            "col_start": int,
            "col_end": int,
            "bbox": [x1, y1, x2, y2],
            "is_header": bool,
            "text": str | None,
        },
        ...
    ],
    "structure_sequence": str | None, # chuỗi HTML/LaTeX token hoá (cho hướng tiếp cận Image-to-Markup),
                                       # None nếu dataset không cung cấp / không áp dụng

    "quality_flags": {
        "multi_line_text": bool,      # có cell chứa nhiều dòng văn bản
        "skewed": bool,               # ảnh/bảng bị nghiêng
        "handwritten": bool,          # chứa nội dung viết tay (vd ICDAR historical)
    },
}
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import os
from typing import Any, Optional
import json
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
from PIL import Image
from pathlib import Path


ANNOTATION_LEVELS = ("detection_only", "structure", "full")


class Converter(ABC):
    dataset_name = "base"

    def __init__(self, raw_dir: str | Path, output_dir: str | Path) -> None:
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def convert(self) -> list[dict[str, Any]]:
        pass

    def _build_record(
        self,
        image_id: str,
        image_path: str | Path,
        table_id: int,
        annotation_level: str,
        table_bbox: Optional[list[float]] = None,
        table_quad: Optional[list[list[float]]] = None,
        num_rows: int = 0,
        num_cols: int = 0,
        cells: Optional[list[dict[str, Any]]] = None,
        structure_sequence: Optional[str] = None,
        quality_flags: Optional[dict[str, bool]] = None,
    ) -> dict[str, Any]:
        if annotation_level not in ANNOTATION_LEVELS:
            raise ValueError(
                f"annotation_level={annotation_level!r} không hợp lệ, "
                f"phải thuộc {ANNOTATION_LEVELS}"
            )

        if table_bbox is None and table_quad is not None:
            table_bbox = self._quad_to_bbox(table_quad)
        if table_quad is None and table_bbox is not None:
            table_quad = self._bbox_to_quad(table_bbox)
        if table_bbox is None:
            table_bbox = [0.0, 0.0, 0.0, 0.0]
        if table_quad is None:
            table_quad = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]

        default_flags = {
            "multi_line_text": False,
            "skewed": False,
            "handwritten": False,
        }
        if quality_flags:
            default_flags.update(quality_flags)

        # Tự suy multi_line_text từ cells nếu chưa được set
        if not default_flags["multi_line_text"] and cells:
            for c in cells:
                t = c.get("text")
                if t and ("\n" in t or "\r" in t):
                    default_flags["multi_line_text"] = True
                    break

        return {
            "image_id": image_id,
            "image_path": str(image_path),
            "source_dataset": self.dataset_name,
            "table_id": table_id,
            "annotation_level": annotation_level,
            "table_bbox": [float(x) for x in table_bbox],
            "table_quad": [[float(x), float(y)] for x, y in table_quad],
            "num_rows": int(num_rows),
            "num_cols": int(num_cols),
            "cells": cells if cells is not None else [],
            "structure_sequence": structure_sequence,
            "quality_flags": default_flags,
        }

    @staticmethod
    def _quad_to_bbox(quad: list[list[float]]) -> list[float]:
        if not quad:
            return [0.0, 0.0, 0.0, 0.0]
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        return [min(xs), min(ys), max(xs), max(ys)]

    @staticmethod
    def _bbox_to_quad(bbox: list[float]) -> list[list[float]]:
        x1, y1, x2, y2 = bbox
        return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    @staticmethod
    def _intersect_bbox(a: list[float], b: list[float]) -> list[float]:
        """Intersection of two axis-aligned bboxes. Returns [0,0,0,0] if no overlap."""
        x1 = max(a[0], b[0])
        y1 = max(a[1], b[1])
        x2 = min(a[2], b[2])
        y2 = min(a[3], b[3])
        if x1 >= x2 or y1 >= y2:
            return [0.0, 0.0, 0.0, 0.0]
        return [x1, y1, x2, y2]

    def save(self, records: list[dict[str, Any]], filename: str = "annotations.json") -> Path:
        if not records:
            raise ValueError(
                f"[{self.dataset_name}] records rỗng - không có gì để ghi. "
                f"Kiểm tra lại convert() hoặc đường dẫn raw_dir={self.raw_dir}."
            )

        out_path = self.output_dir / filename
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"Ghi dữ liệu thành công vào {out_path}")
        return out_path


class PubTables1MConverter(Converter):
    """
    PubTables-1M Structure (PASCAL VOC):
    - Objects thường gặp: table, table row, table column, table spanning cell,
      table column header, table projected row header.
    - Grid cell 1x1 được suy ra từ giao của row bbox ∩ column bbox.
    - Spanning cell ghi đè các grid cell nằm trong vùng span.
    - Ảnh structure thường là cropped table → 1 table / file.
    """

    dataset_name = "PubTables-1M"

    def convert(self) -> list[dict[str, Any]]:
        raw_path = self.raw_dir
        records: list[dict[str, Any]] = []
        table_id_counter = 0

        xml_files = list(raw_path.rglob("*.xml"))
        print(f"[{self.dataset_name}] Tìm thấy {len(xml_files)} file XML.")

        for xml_path in xml_files:
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
            except ET.ParseError:
                continue

            filename_node = root.find("filename")
            filename = (
                filename_node.text
                if filename_node is not None and filename_node.text
                else xml_path.with_suffix(".jpg").name
            )
            # Ảnh có thể nằm cùng thư mục hoặc trong images/
            image_path = raw_path / filename
            if not image_path.exists():
                alt = raw_path / "images" / filename
                if alt.exists():
                    image_path = alt

            table_bbox: Optional[list[float]] = None
            rows_bboxes: list[list[float]] = []
            cols_bboxes: list[list[float]] = []
            spanning_cells: list[list[float]] = []
            header_rows: set[int] = set()  # optional, từ column header / projected row header

            for obj in root.findall("object"):
                name_node = obj.find("name")
                if name_node is None or name_node.text is None:
                    continue
                name = name_node.text.strip().lower()
                bndbox = obj.find("bndbox")
                if bndbox is None:
                    continue
                try:
                    bbox = [
                        float(bndbox.find("xmin").text),
                        float(bndbox.find("ymin").text),
                        float(bndbox.find("xmax").text),
                        float(bndbox.find("ymax").text),
                    ]
                except (AttributeError, TypeError, ValueError):
                    continue

                if name == "table":
                    table_bbox = bbox
                elif name in ("table row", "row"):
                    rows_bboxes.append(bbox)
                elif name in ("table column", "column"):
                    cols_bboxes.append(bbox)
                elif name in ("table spanning cell", "spanning cell"):
                    spanning_cells.append(bbox)
                # column header / projected row header chỉ dùng để đánh dấu is_header (nếu có)

            if table_bbox is None and (rows_bboxes or cols_bboxes):
                # Fallback: union của rows + cols
                all_b = rows_bboxes + cols_bboxes
                table_bbox = [
                    min(b[0] for b in all_b),
                    min(b[1] for b in all_b),
                    max(b[2] for b in all_b),
                    max(b[3] for b in all_b),
                ]

            if not table_bbox:
                continue

            # Sắp xếp hàng (top → bottom), cột (left → right)
            rows_bboxes.sort(key=lambda b: (b[1] + b[3]) / 2)
            cols_bboxes.sort(key=lambda b: (b[0] + b[2]) / 2)

            num_rows = len(rows_bboxes)
            num_cols = len(cols_bboxes)

            if num_rows == 0 or num_cols == 0:
                # Không đủ structure → chỉ giữ detection
                record = self._build_record(
                    image_id=xml_path.stem,
                    image_path=image_path.resolve(),
                    table_id=table_id_counter,
                    annotation_level="detection_only",
                    table_bbox=table_bbox,
                    num_rows=0,
                    num_cols=0,
                    cells=[],
                )
                records.append(record)
                table_id_counter += 1
                continue

            # 1. Tạo grid cell 1x1 từ giao row ∩ col
            grid: list[list[Optional[dict[str, Any]]]] = [
                [None for _ in range(num_cols)] for _ in range(num_rows)
            ]
            for r, r_bbox in enumerate(rows_bboxes):
                for c, c_bbox in enumerate(cols_bboxes):
                    inter = self._intersect_bbox(r_bbox, c_bbox)
                    grid[r][c] = {
                        "row_start": r,
                        "row_end": r,
                        "col_start": c,
                        "col_end": c,
                        "bbox": inter,
                        "is_header": False,
                        "text": None,
                    }

            # 2. Áp spanning cells: tìm các (r,c) overlap và gộp
            for span_bbox in spanning_cells:
                overlapping_rows = [
                    i
                    for i, r_bbox in enumerate(rows_bboxes)
                    if span_bbox[1] < r_bbox[3] and span_bbox[3] > r_bbox[1]
                ]
                overlapping_cols = [
                    i
                    for i, c_bbox in enumerate(cols_bboxes)
                    if span_bbox[0] < c_bbox[2] and span_bbox[2] > c_bbox[0]
                ]
                if not overlapping_rows or not overlapping_cols:
                    continue
                rs, re = min(overlapping_rows), max(overlapping_rows)
                cs, ce = min(overlapping_cols), max(overlapping_cols)

                # Đánh dấu các ô bị span (giữ ô top-left, xoá các ô còn lại)
                cell = {
                    "row_start": rs,
                    "row_end": re,
                    "col_start": cs,
                    "col_end": ce,
                    "bbox": span_bbox,
                    "is_header": False,
                    "text": None,
                }
                for rr in range(rs, re + 1):
                    for cc in range(cs, ce + 1):
                        if rr == rs and cc == cs:
                            grid[rr][cc] = cell
                        else:
                            grid[rr][cc] = None  # đã bị merge

            # 3. Flatten cells (bỏ None)
            cells = [cell for row in grid for cell in row if cell is not None]

            record = self._build_record(
                image_id=xml_path.stem,
                image_path=image_path.resolve(),
                table_id=table_id_counter,
                annotation_level="structure",
                table_bbox=table_bbox,
                num_rows=num_rows,
                num_cols=num_cols,
                cells=cells,
                structure_sequence=None,
                quality_flags={
                    "multi_line_text": False,
                    "skewed": False,
                    "handwritten": False,
                },
            )
            records.append(record)
            table_id_counter += 1

        print(f"[{self.dataset_name}] Đã xử lý thành công {len(records)} bảng.")
        return records


class FinTabNetHTMLParser(HTMLParser):
    """Parse HTML structure tokens của FinTabNet để lấy (row_start, row_end, col_start, col_end, is_header)."""

    def __init__(self) -> None:
        super().__init__()
        self.cell_metadata: list[dict[str, Any]] = []
        self.current_row = -1
        self.current_col = 0
        self.row_spans: dict[int, int] = {}  # col -> remaining rowspan
        self.in_header = False

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "thead":
            self.in_header = True
        elif tag == "tbody":
            self.in_header = False
        elif tag == "tr":
            self.current_row += 1
            self.current_col = 0
        elif tag in ("td", "th"):
            # Bỏ qua các cột đang bị rowspan từ hàng trên chiếm
            while self.current_col in self.row_spans and self.row_spans[self.current_col] > 0:
                self.current_col += 1

            attr_dict = dict(attrs)
            colspan = int(attr_dict.get("colspan", 1) or 1)
            rowspan = int(attr_dict.get("rowspan", 1) or 1)

            self.cell_metadata.append(
                {
                    "row_start": self.current_row,
                    "row_end": self.current_row + rowspan - 1,
                    "col_start": self.current_col,
                    "col_end": self.current_col + colspan - 1,
                    "is_header": tag == "th" or self.in_header,
                }
            )

            if rowspan > 1:
                for c in range(self.current_col, self.current_col + colspan):
                    self.row_spans[c] = rowspan - 1

            self.current_col += colspan

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "tr":
            for col in list(self.row_spans.keys()):
                self.row_spans[col] -= 1
                if self.row_spans[col] <= 0:
                    del self.row_spans[col]


class FinTabNetConverter(Converter):
    dataset_name = "FinTabNet"

    def convert(self) -> list[dict[str, Any]]:
        raw_path = self.raw_dir
        records: list[dict[str, Any]] = []
        table_id_counter = 0

        jsonl_files = list(raw_path.rglob("*.jsonl"))
        print(f"[{self.dataset_name}] Tìm thấy {len(jsonl_files)} file JSONL.")

        for jsonl_path in jsonl_files:
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    filename = data.get("filename", "")
                    if not filename:
                        continue
                    image_path = raw_path / filename
                    if not image_path.exists():
                        # thử thư mục images/
                        alt = raw_path / "images" / filename
                        if alt.exists():
                            image_path = alt

                    html_data = data.get("html", {}) or {}
                    structure_tokens = (html_data.get("structure") or {}).get("tokens") or []
                    cells_data = html_data.get("cells") or []

                    structure_sequence = "".join(structure_tokens) if structure_tokens else None

                    parser = FinTabNetHTMLParser()
                    if structure_sequence:
                        try:
                            parser.feed(structure_sequence)
                        except Exception:
                            continue
                    grid_metadata = parser.cell_metadata

                    if len(grid_metadata) != len(cells_data):
                        # Lệch số cell → bỏ qua record lỗi
                        continue

                    cells: list[dict[str, Any]] = []
                    valid_bboxes: list[list[float]] = []
                    max_row = -1
                    max_col = -1

                    for logic_meta, phys_meta in zip(grid_metadata, cells_data):
                        bbox = phys_meta.get("bbox")
                        if not bbox or len(bbox) != 4:
                            bbox = [0.0, 0.0, 0.0, 0.0]
                        else:
                            bbox = [float(x) for x in bbox]
                            if any(v != 0 for v in bbox):
                                valid_bboxes.append(bbox)

                        text_tokens = phys_meta.get("tokens") or []
                        cell_text = "".join(text_tokens).strip() or None

                        cells.append(
                            {
                                "row_start": logic_meta["row_start"],
                                "row_end": logic_meta["row_end"],
                                "col_start": logic_meta["col_start"],
                                "col_end": logic_meta["col_end"],
                                "bbox": bbox,
                                "is_header": logic_meta["is_header"],
                                "text": cell_text,
                            }
                        )
                        max_row = max(max_row, logic_meta["row_end"])
                        max_col = max(max_col, logic_meta["col_end"])

                    if valid_bboxes:
                        table_bbox = [
                            min(b[0] for b in valid_bboxes),
                            min(b[1] for b in valid_bboxes),
                            max(b[2] for b in valid_bboxes),
                            max(b[3] for b in valid_bboxes),
                        ]
                    else:
                        table_bbox = [0.0, 0.0, 0.0, 0.0]

                    record = self._build_record(
                        image_id=Path(filename).stem,
                        image_path=image_path.resolve(),
                        table_id=table_id_counter,
                        annotation_level="full",
                        table_bbox=table_bbox,
                        num_rows=max_row + 1 if max_row >= 0 else 0,
                        num_cols=max_col + 1 if max_col >= 0 else 0,
                        cells=cells,
                        structure_sequence=structure_sequence,
                        quality_flags={
                            "multi_line_text": False,  # sẽ được _build_record suy ra nếu có \n
                            "skewed": False,
                            "handwritten": False,
                        },
                    )
                    records.append(record)
                    table_id_counter += 1

        print(
            f"[{self.dataset_name}] Đã xử lý thành công {len(records)} bảng (full annotation)."
        )
        return records


class TableBankConverter(Converter):
    dataset_name = "TableBank"

    def convert(self) -> list[dict[str, Any]]:
        raw_path = self.raw_dir

        json_files = list(raw_path.glob("*.json")) + list(raw_path.glob("*/*.json"))
        if not json_files:
            raise FileNotFoundError(
                f"Không tìm thấy file annotation .json nào trong {self.raw_dir}"
            )

        annotation_file = json_files[0]
        print(f"[{self.dataset_name}] Đang đọc nhãn từ: {annotation_file}")

        with open(annotation_file, "r", encoding="utf-8") as f:
            coco_data = json.load(f)

        images_info = {img["id"]: img for img in coco_data.get("images", [])}
        records: list[dict[str, Any]] = []

        for ann in coco_data.get("annotations", []):
            img_id = ann.get("image_id")
            if img_id not in images_info:
                continue

            img_meta = images_info[img_id]
            file_name = img_meta.get("file_name", "")
            if not file_name:
                continue

            image_path = raw_path / file_name
            if not image_path.exists():
                image_path = raw_path / "images" / file_name

            bbox = ann.get("bbox", [0, 0, 0, 0])
            if len(bbox) != 4:
                continue
            x, y, w, h = map(float, bbox)
            table_bbox = [
                round(x, 2),
                round(y, 2),
                round(x + w, 2),
                round(y + h, 2),
            ]

            record = self._build_record(
                image_id=str(img_id),
                image_path=image_path.resolve(),
                table_id=int(ann.get("id", len(records))),
                annotation_level="detection_only",
                table_bbox=table_bbox,
                num_rows=0,
                num_cols=0,
                cells=[],
                structure_sequence=None,
                quality_flags={
                    "multi_line_text": False,
                    "skewed": False,
                    "handwritten": False,
                },
            )
            records.append(record)

        print(f"[{self.dataset_name}] Đã xử lý thành công {len(records)} bảng.")
        return records


class ICDAR2019cTDaRConverter(Converter):
    dataset_name = "ICDAR-2019-cTDaR"

    def convert(self) -> list[dict[str, Any]]:
        raw_path = self.raw_dir
        records: list[dict[str, Any]] = []
        table_id_counter = 0

        xml_files = list(raw_path.rglob("*.xml"))
        print(f"[{self.dataset_name}] Tìm thấy {len(xml_files)} file XML.")

        for xml_path in xml_files:
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
            except ET.ParseError:
                continue

            image_name = xml_path.stem
            image_path_obj: Optional[Path] = None
            for ext in (".jpg", ".png", ".jpeg", ".tif", ".tiff"):
                potential = xml_path.with_suffix(ext)
                if potential.exists():
                    image_path_obj = potential
                    break
            if image_path_obj is None:
                # thử cùng thư mục cha / images
                for ext in (".jpg", ".png", ".jpeg"):
                    alt = raw_path / "images" / f"{image_name}{ext}"
                    if alt.exists():
                        image_path_obj = alt
                        break
            if image_path_obj is None:
                image_path_obj = xml_path.with_suffix(".jpg")

            is_historical = "cTDaR_t0" in image_name

            for table_node in root.findall(".//table"):
                table_coords_node = table_node.find("Coords")
                if table_coords_node is None:
                    continue

                t_points_str = table_coords_node.attrib.get("points", "")
                t_points = self._parse_points(t_points_str)
                if not t_points:
                    continue

                table_bbox = self._quad_to_bbox(t_points)
                # Giữ polygon gốc nếu có >= 4 điểm, không thì dùng bbox
                table_quad = t_points[:4] if len(t_points) >= 4 else self._bbox_to_quad(table_bbox)

                cells: list[dict[str, Any]] = []
                max_row = -1
                max_col = -1
                has_text = False

                for cell_node in table_node.findall("cell"):
                    try:
                        row_start = int(cell_node.attrib.get("start-row", 0))
                        row_end = int(cell_node.attrib.get("end-row", row_start))
                        col_start = int(cell_node.attrib.get("start-col", 0))
                        col_end = int(cell_node.attrib.get("end-col", col_start))
                    except (ValueError, TypeError):
                        continue

                    c_coords_node = cell_node.find("Coords")
                    if c_coords_node is None:
                        continue
                    c_points_str = c_coords_node.attrib.get("points", "")
                    c_points = self._parse_points(c_points_str)
                    if not c_points:
                        continue
                    cell_bbox = self._quad_to_bbox(c_points)

                    text = None
                    content_node = cell_node.find("content")
                    if content_node is not None and content_node.text:
                        text = content_node.text.strip() or None
                        if text:
                            has_text = True

                    cells.append(
                        {
                            "row_start": row_start,
                            "row_end": row_end,
                            "col_start": col_start,
                            "col_end": col_end,
                            "bbox": cell_bbox,
                            "is_header": False,
                            "text": text,
                        }
                    )
                    max_row = max(max_row, row_end)
                    max_col = max(max_col, col_end)

                num_rows = max_row + 1 if max_row >= 0 else 0
                num_cols = max_col + 1 if max_col >= 0 else 0

                level = "full" if has_text else "structure"

                record = self._build_record(
                    image_id=image_name,
                    image_path=image_path_obj.resolve(),
                    table_id=table_id_counter,
                    annotation_level=level,
                    table_bbox=table_bbox,
                    table_quad=table_quad,
                    num_rows=num_rows,
                    num_cols=num_cols,
                    cells=cells,
                    structure_sequence=None,
                    quality_flags={
                        "multi_line_text": False,
                        "skewed": is_historical,
                        "handwritten": is_historical,
                    },
                )
                records.append(record)
                table_id_counter += 1

        print(f"[{self.dataset_name}] Đã xử lý thành công {len(records)} bảng.")
        return records

    @staticmethod
    def _parse_points(points_str: str) -> list[list[float]]:
        points: list[list[float]] = []
        for pt in points_str.strip().split():
            if "," in pt:
                parts = pt.split(",", 1)
                try:
                    points.append([float(parts[0]), float(parts[1])])
                except ValueError:
                    pass
        return points


class WTWConverter(Converter):
    """
    WTW (Wired Tables in the Wild) – format Kaggle/AkaCoder404:
    <object>
      <name>box</name>
      <bndbox>
        <xmin>..<xmax>..<ymin>..<ymax>
        <x1><y1>...<x4><y4>          # 4 đỉnh
        <startcol><endcol><startrow><endrow>
        <tableid>
      </bndbox>
    </object>
    """

    dataset_name = "WTW"

    def convert(self) -> list[dict[str, Any]]:
        raw_path = self.raw_dir
        records: list[dict[str, Any]] = []
        table_id_counter = 0

        xml_files = list(raw_path.rglob("*.xml"))
        print(f"[{self.dataset_name}] Tìm thấy {len(xml_files)} file XML.")

        for xml_path in xml_files:
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
            except ET.ParseError:
                continue

            filename_node = root.find("filename")
            filename = (
                filename_node.text
                if filename_node is not None and filename_node.text
                else xml_path.with_suffix(".jpg").name
            )
            image_path = raw_path / filename
            if not image_path.exists():
                image_path = raw_path / "images" / filename

            # Group cells theo tableid
            tables: dict[Any, list[dict[str, Any]]] = {}

            for obj in root.findall("object"):
                name_node = obj.find("name")
                name = (name_node.text or "").strip().lower() if name_node is not None else ""

                # WTW Kaggle dùng name="box"; bỏ qua object không phải cell
                if name not in ("box", "cell", "table cell", ""):
                    if name == "table":
                        continue
                    # vẫn thử parse nếu có bndbox chứa startrow
                    pass

                bndbox = obj.find("bndbox")
                if bndbox is None:
                    continue

                # tableid nằm trong bndbox
                tid = 0
                for tag in ("tableid", "table_id", "tableId"):
                    node = bndbox.find(tag)
                    if node is not None and node.text:
                        try:
                            tid = int(float(node.text))
                            break
                        except ValueError:
                            pass

                quad = self._extract_quad(obj, bndbox)
                if quad is None:
                    continue

                row_start, row_end, col_start, col_end = self._extract_grid_indices(obj, bndbox)

                cell_bbox = self._quad_to_bbox(quad)
                cell = {
                    "row_start": row_start,
                    "row_end": row_end,
                    "col_start": col_start,
                    "col_end": col_end,
                    "bbox": cell_bbox,
                    "is_header": False,
                    "text": None,
                    "_quad": quad,
                }
                tables.setdefault(tid, []).append(cell)

            for tid, cell_list in tables.items():
                if not cell_list:
                    continue

                max_row = max(c["row_end"] for c in cell_list)
                max_col = max(c["col_end"] for c in cell_list)
                num_rows = max_row + 1
                num_cols = max_col + 1

                all_pts: list[list[float]] = []
                for c in cell_list:
                    all_pts.extend(c.pop("_quad", []))
                if all_pts:
                    table_quad = [
                        [min(p[0] for p in all_pts), min(p[1] for p in all_pts)],
                        [max(p[0] for p in all_pts), min(p[1] for p in all_pts)],
                        [max(p[0] for p in all_pts), max(p[1] for p in all_pts)],
                        [min(p[0] for p in all_pts), max(p[1] for p in all_pts)],
                    ]
                else:
                    table_quad = None

                clean_cells = [
                    {
                        "row_start": c["row_start"],
                        "row_end": c["row_end"],
                        "col_start": c["col_start"],
                        "col_end": c["col_end"],
                        "bbox": c["bbox"],
                        "is_header": c["is_header"],
                        "text": c["text"],
                    }
                    for c in cell_list
                ]

                record = self._build_record(
                    image_id=xml_path.stem,
                    image_path=image_path.resolve(),
                    table_id=table_id_counter,
                    annotation_level="structure",
                    table_bbox=None,
                    table_quad=table_quad,
                    num_rows=num_rows,
                    num_cols=num_cols,
                    cells=clean_cells,
                    structure_sequence=None,
                    quality_flags={
                        "multi_line_text": False,
                        "skewed": True,
                        "handwritten": False,
                    },
                )
                records.append(record)
                table_id_counter += 1

        print(f"[{self.dataset_name}] Đã xử lý thành công {len(records)} bảng.")
        return records

    def _extract_quad(
        self, obj: ET.Element, bndbox: Optional[ET.Element] = None
    ) -> Optional[list[list[float]]]:
        """Lấy 4 đỉnh. Ưu tiên x1..y4 trong <bndbox> (format Kaggle WTW)."""
        if bndbox is None:
            bndbox = obj.find("bndbox")

        # 1. x1,y1,...,x4,y4 nằm trong bndbox (format thực tế)
        if bndbox is not None:
            try:
                pts = []
                for i in range(1, 5):
                    x = bndbox.find(f"x{i}")
                    y = bndbox.find(f"y{i}")
                    if x is not None and y is not None and x.text and y.text:
                        pts.append([float(x.text), float(y.text)])
                if len(pts) == 4:
                    return pts
            except (TypeError, ValueError):
                pass

        # 2. <polygon> dưới object
        polygon = obj.find("polygon")
        if polygon is not None:
            try:
                return [
                    [float(polygon.find("x1").text), float(polygon.find("y1").text)],
                    [float(polygon.find("x2").text), float(polygon.find("y2").text)],
                    [float(polygon.find("x3").text), float(polygon.find("y3").text)],
                    [float(polygon.find("x4").text), float(polygon.find("y4").text)],
                ]
            except (AttributeError, TypeError, ValueError):
                pass

        # 3. x1..y4 trực tiếp dưới object
        try:
            pts = []
            for i in range(1, 5):
                x = obj.find(f"x{i}")
                y = obj.find(f"y{i}")
                if x is not None and y is not None and x.text and y.text:
                    pts.append([float(x.text), float(y.text)])
            if len(pts) == 4:
                return pts
        except (TypeError, ValueError):
            pass

        # 4. Fallback xmin/ymin/xmax/ymax → rectangle
        if bndbox is not None:
            try:
                xmin = float(bndbox.find("xmin").text)
                ymin = float(bndbox.find("ymin").text)
                xmax = float(bndbox.find("xmax").text)
                ymax = float(bndbox.find("ymax").text)
                return self._bbox_to_quad([xmin, ymin, xmax, ymax])
            except (AttributeError, TypeError, ValueError):
                pass

        return None

    def _extract_grid_indices(
        self, obj: ET.Element, bndbox: Optional[ET.Element] = None
    ) -> tuple[int, int, int, int]:
        """
        Lấy startrow/endrow/startcol/endcol.
        Format Kaggle: nằm trong <bndbox> với tên startrow, endrow, startcol, endcol.
        """
        if bndbox is None:
            bndbox = obj.find("bndbox")

        def _get_int(sources: list[Optional[ET.Element]], *candidates: str, default: int = 0) -> int:
            for src in sources:
                if src is None:
                    continue
                for name in candidates:
                    node = src.find(name)
                    if node is not None and node.text:
                        try:
                            return int(float(node.text))
                        except ValueError:
                            pass
                    if name in src.attrib:
                        try:
                            return int(float(src.attrib[name]))
                        except ValueError:
                            pass
            return default

        sources = [bndbox, obj]
        row_start = _get_int(sources, "startrow", "start_row", "start-row", "startRow", "row_start")
        row_end = _get_int(
            sources, "endrow", "end_row", "end-row", "endRow", "row_end", default=row_start
        )
        col_start = _get_int(sources, "startcol", "start_col", "start-col", "startCol", "col_start")
        col_end = _get_int(
            sources, "endcol", "end_col", "end-col", "endCol", "col_end", default=col_start
        )

        if row_end < row_start:
            row_end = row_start
        if col_end < col_start:
            col_end = col_start
        return row_start, row_end, col_start, col_end


class ViFinTabConverter(Converter):
    dataset_name = "ViFinTab"

    def convert(self) -> list[dict[str, Any]]:
        raw_path = self.raw_dir
        records: list[dict[str, Any]] = []
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
        table_id_counter = 0

        for img_path in raw_path.rglob("*"):
            if img_path.suffix.lower() not in image_extensions:
                continue

            txt_path = img_path.with_suffix(".txt")
            if not txt_path.exists():
                continue

            try:
                with Image.open(img_path) as img:
                    img_w, img_h = img.size
            except Exception:
                continue

            with open(txt_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                try:
                    # YOLO: class x_center y_center w h  (normalized)
                    x_center, y_center, w, h = map(float, parts[1:5])
                except ValueError:
                    continue

                x1 = (x_center - w / 2) * img_w
                y1 = (y_center - h / 2) * img_h
                x2 = (x_center + w / 2) * img_w
                y2 = (y_center + h / 2) * img_h

                table_bbox = [
                    round(x1, 2),
                    round(y1, 2),
                    round(x2, 2),
                    round(y2, 2),
                ]

                record = self._build_record(
                    image_id=img_path.stem,
                    image_path=img_path.resolve(),
                    table_id=table_id_counter,
                    annotation_level="detection_only",
                    table_bbox=table_bbox,
                    num_rows=0,
                    num_cols=0,
                    cells=[],
                    structure_sequence=None,
                    quality_flags={
                        "multi_line_text": False,
                        "skewed": False,
                        "handwritten": False,
                    },
                )
                records.append(record)
                table_id_counter += 1

        print(
            f"[{self.dataset_name}] Đã xử lý thành công {len(records)} bảng từ định dạng YOLO."
        )
        return records


# Convenience registry
CONVERTERS = {
    "PubTables-1M": PubTables1MConverter,
    "FinTabNet": FinTabNetConverter,
    "TableBank": TableBankConverter,
    "ICDAR-2019-cTDaR": ICDAR2019cTDaRConverter,
    "WTW": WTWConverter,
    "ViFinTab": ViFinTabConverter,
}


def get_converter(name: str, raw_dir: str | Path, output_dir: str | Path) -> Converter:
    if name not in CONVERTERS:
        raise KeyError(f"Unknown dataset: {name}. Available: {list(CONVERTERS)}")
    return CONVERTERS[name](raw_dir, output_dir)
