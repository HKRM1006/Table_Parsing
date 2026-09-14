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
from abc import ABC, abstractmethod
import os
from typing import Any, Optional
import json

"""
detection_only: 
"""
ANNOTATION_LEVELS = ("detection_only", "structure", "full")

class Converter(ABC):
    dataset_name = "base"
    def __init__(self, raw_dir: str, output_dir: str) -> None:
        self.raw_dir = raw_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    @abstractmethod
    def convert(self) -> list[dict[str, Any]]:
        pass

    """
    Hàm để tạo record. Quy trình trong class con: Đọc dự liệu -> sử dụng hàm này build record -> lưu 
    """
    def _build_record(
        self,
        image_id: str,
        image_path: str,
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
            table_bbox = [0, 0, 0, 0]
        if table_quad is None:
            table_quad = [[0, 0], [0, 0], [0, 0], [0, 0]]

        # Nên hiện thực nếu có thể để dễ cho giai đoạn preprocessing và train sau này, nếu không làm nhớ nhắn lên nhóm
        default_flags = {
            "multi_line_text": False,
            "skewed": False,
            "handwritten": False,
        }

        if quality_flags:
            default_flags.update(quality_flags)
 
        return {
            "image_id": image_id,
            "image_path": image_path,
            "source_dataset": self.dataset_name,
            "table_id": table_id,
            "annotation_level": annotation_level,
 
            "table_bbox": table_bbox,
            "table_quad": table_quad,
 
            "num_rows": num_rows,
            "num_cols": num_cols,
            "cells": cells if cells is not None else [],
            "structure_sequence": structure_sequence,
 
            "quality_flags": default_flags,
        }
    
    @staticmethod
    def _quad_to_bbox(quad: list[list[float]]) -> list[float]:
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        return [min(xs), min(ys), max(xs), max(ys)]
 
    @staticmethod
    def _bbox_to_quad(bbox: list[float]) -> list[list[float]]:
        x1, y1, x2, y2 = bbox
        return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]

    def save(self, records: list[dict[str, Any]], filename: str = "annotations.json"):
        if not records:
            raise ValueError(
                f"[{self.dataset_name}] records rỗng - không có gì để ghi. "
                f"Kiểm tra lại convert() hoặc đường dẫn raw_dir={self.raw_dir}."
            )
 
        out_path = self.output_dir / filename
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(
            f"Ghi dữ liệu thành công vào {out_path}"
        )


class PubTables1MConverter(Converter):
    dataset_name = "PubTables-1M"
    def convert(self) -> list[dict[str, Any]]:
        raise NotImplementedError
 
 
class FinTabNetConverter(Converter):
    dataset_name = "FinTabNet"
    def convert(self) -> list[dict[str, Any]]:
        raise NotImplementedError
 
 
class TableBankConverter(Converter):
    dataset_name = "TableBank"
 
    def convert(self) -> list[dict[str, Any]]:
        raise NotImplementedError
 
 
class ICDAR2019cTDaRConverter(Converter):
    dataset_name = "ICDAR-2019-cTDaR"
 
    def convert(self) -> list[dict[str, Any]]:
        raise NotImplementedError
 
 
class WTWConverter(Converter):
    dataset_name = "WTW"
    def convert(self) -> list[dict[str, Any]]:
        raise NotImplementedError
 
 
class ViFinTabConverter(Converter):
    dataset_name = "ViFinTab"
    def convert(self) -> list[dict[str, Any]]:
        raise NotImplementedError
 
