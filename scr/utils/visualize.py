from PIL import Image, ImageDraw
from utils import refine_html
from html.parser import HTMLParser
import os
import json
"""
Render
"""
FILL_CELLS = (255,0,0)
FILL_HEADER = (0,255,0)
FILL_SPAN = (0,0,255)
LINE = (85, 85, 85)
class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[dict]] = []

    def _get_valid_span(a) -> int:
        try:
            return max(1, int(a))
        except:
            return 1
        
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            if not self.rows or self.rows[-1]:
                self.rows.append([])
        elif tag in ("td", "th"):
            if not self.rows:
                self.rows.append([])
            self.rows[-1].append(
                {
                    "tag":tag,
                    "rowspan":self._get_valid_span(a.get("rowspan")),
                    "colspan":self._get_valid_span(a.get("colspan")),
                    "text":""
                }
            )    

    def handle_data(self, data):
        if self.rows and self.rows[-1]:
            self.rows[-1][-1]["text"] += data

def _is_span(c: dict) -> bool:
    return c["row_end"] > c["row_start"] or c["col_end"] > c["col_start"]


def _key(c: dict) -> tuple[int, int, int, int]:
    return (c["row_start"], c["row_end"], c["col_start"], c["col_end"])

def _html_to_cell(html):
    if not html:
        return []
    # Chuyển input từ nhiều thead thành thead -> tr -> th
    html = refine_html(html)
    parser = _TableParser()
    parser.feed(html)
    rows = [r for r in parser.rows if r]
    # Đánh dấu các ô bị chiếm bởi spanning cell
    occupied: set[tuple[int,int]] = set()
    cells = []
    for r, row in enumerate(rows):
        c = 0
        for cell in row:
            while (r, c) in occupied:
                c += 1
            rs, cs = cell["rowspan"], cell["colspan"]
            for i in range(rs):
                for j in range(cs):
                    occupied.add((r+i, c+j))
            cells.append({
                "row_start": r,
                "row_end": r + rs - 1,
                "col_start": c,
                "col_end": c + cs - 1,
                "is_header": cell["tag"] == "th",
                "text": cell["text"],
            })
            c += cs
    return cells


def _get_fill(c):
    if c.get("is_header"):
        return FILL_HEADER
    if _is_span(c):
        return FILL_SPAN
    return FILL_CELLS

def _render_bboxs(schema, image:Image, max_width:int = 1000, margin:int = 10) -> Image.Image:
    # filter lọc lỗi, có thể bỏ sau khi có postprocess
    no_fill = image is None
    cells = [c for c in schema["cells"] if c["bbox"][2] > c["bbox"][0] and c["bbox"][3] > c["bbox"][1]]
    if not cells:
        raise ValueError("No valid cells to render!")
    if image is None:
        ox = min(c["bbox"][0] for c in cells)
        oy = min(c["bbox"][1] for c in cells)
        tw = max(c["bbox"][2] for c in cells) - ox
        th = max(c["bbox"][3] for c in cells) - oy
        scale = min(1.0, max_width / tw) if tw > 0 else 1.0
        image = Image.new("RGB", (int(tw * scale) + 2 * margin, int(th * scale) + 2 * margin), (255, 255, 255))
    else:
        scale = 1
        margin = 0
        ox = 0
        oy = 0
        tw = 0
        th = 0
    draw = ImageDraw.Draw(image)
    for cell in cells:
        x1, y1, x2, y2 = cell["bbox"]
        a = (x1 - ox) * scale + margin
        b = (y1 - oy) * scale + margin
        c = (x2 - ox) * scale + margin
        d = (y2 - oy) * scale + margin
        if no_fill:
            draw.rectangle([a,b,c,d], outline=_get_fill(c), width=2)
        else:
            draw.rectangle([a,b,c,d], fill=_get_fill(c), outline=LINE, width=2)
    return image

def _render_cells(cells: list[dict], min_w: int = 40,
                 row_h: int = 30, margin: int = 10) -> Image.Image:

    n_r = max(c["row_end"] for c in cells) + 1
    n_c = max(c["col_end"] for c in cells) + 1

    col_w = [min_w] * n_c

    xs = [margin]
    for w in col_w:
        xs.append(xs[-1] + w)

    W = xs[-1] + margin
    H = n_r * row_h + 2 * margin

    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)

    for c in cells:
        x1 = xs[c["col_start"]]
        x2 = xs[c["col_end"] + 1]
        y1 = margin + c["row_start"] * row_h
        y2 = margin + (c["row_end"] + 1) * row_h

        d.rectangle(
            [x1, y1, x2, y2],
            fill=_get_fill(c),
            outline=(0,0,0),
            width=2
        )
    return img

def render(input, max_w: int = 1000, mode:str = "geometry", min_w: int = 40, row_h: int = 30, margin: int = 10):
    dir = os.path.join("data", "visualize")
    os.makedirs(dir, exist_ok=True)
    # Xử lí 1 file json chứa record
    if isinstance(input, str) and input.strip().endswith(".json"):
        try:
            with open(input, 'r'    ) as f:
                records = json.load(f)
            if mode == "geometry":
                for record in records:
                    if os.path.exists(record["image_path"]):
                        image = Image.open(record["image_path"])
                    else:
                        image = None
                    result = _render_bboxs(record, image, max_width=max_w, margin=margin)
                    result.save(os.path.join(dir, record["image_id"] + ".png"))
            else:
                for record in records:
                    cells = record["cells"]
                    if not cells:
                        cells = _html_to_cell(record["structure_sequence"])
                    result = _render_cells(cells, min_w=min_w, row_h=row_h, margin=margin)
                result.save(os.path.join(dir, record["image_id"] + ".png"))
        except:
            raise ValueError("This file is not a valid records file")
    # Xử lí 1 record
    elif isinstance(input, dict):
        try:
            if mode == "geometry":
                if os.path.exists(input["image_path"]):
                    image = Image.open(input["image_path"])
                else:
                    image = None
                result = _render_bboxs(input, image, max_width=max_w, margin=margin)
            else:
                cells = input["cells"]
                if not cells:
                    cells = _html_to_cell(input["structure_sequence"])
                result = _render_cells(cells, min_w=min_w, row_h=row_h, margin=margin)
            result.save(os.path.join(dir, input["image_id"] + ".png"))
        except:
            raise ValueError("This is not a record file")
    # Xử lí HTML
    elif isinstance(input, str):
        cells = _html_to_cell(input)
        result = _render_cells(cells, min_w=min_w, row_h=row_h, margin=margin)
        result.save(os.path.join(dir, "visualize_html.png"))

def _render_bboxs_test(schema, image:Image, max_width:int = 1000, margin:int = 10) -> Image.Image:
    # filter lọc lỗi, có thể bỏ sau khi có postprocess
    no_fill = image is None
    cells = schema["ocr"]
    if not cells:
        raise ValueError("No valid cells to render!")
    if image is None:
        ox = min(c["bbox"][0] for c in cells)
        oy = min(c["bbox"][1] for c in cells)
        tw = max(c["bbox"][2] for c in cells) - ox
        th = max(c["bbox"][3] for c in cells) - oy
        scale = min(1.0, max_width / tw) if tw > 0 else 1.0
        image = Image.new("RGB", (int(tw * scale) + 2 * margin, int(th * scale) + 2 * margin), (255, 255, 255))
    else:
        scale = 1
        margin = 0
        ox = 0
        oy = 0
        tw = 0
        th = 0
    draw = ImageDraw.Draw(image)
    for cell in cells:
        x1, y1, x2, y2 = cell["bbox"]
        a = (x1 - ox) * scale + margin
        b = (y1 - oy) * scale + margin
        c = (x2 - ox) * scale + margin
        d = (y2 - oy) * scale + margin
        if no_fill:
            draw.rectangle([a,b,c,d], outline=(0,0,0), width=2)
        else:
            draw.rectangle([a,b,c,d], outline=LINE, width=2)
    return image

if __name__ == "__main__":
    with open(r"D:\DACN\EVF_CN_2023_21.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    image = Image.open(r"D:\DACN\EVF_CN_2023_21.jpg")
    _render_bboxs_test(data,image).save(r"D:\DACN\test.jpg")