import numpy as np
from html.parser import HTMLParser
def refine_html(html:str):
    html = "".join([line.strip() for line in html.split("\n")])
    find_idx = 0
    idx = html.find(r"</thead><thead>", find_idx)
    find_idx = idx
    while idx != -1:
        start_idx = html.rfind(r"<thead>", end = find_idx)
        end_idx = html.find(r"/thead", start = find_idx)
        html = html[:start_idx+7] + "<tr>" + html[start_idx+7:find_idx] + "</tr><tr>" + html[find_idx+15:end_idx] + "</tr>" + html[end_idx:]
    return html
     
def iou(a, b):
    # hàm tính intersection / union
    # code hỗ trợ trường hợp tính 1 điểm với nhiều điểm và trường hợp tính theo cặp
    a = np.array(a)
    b = np.array(b)
    if len(a.shape) == 1:
        a = a[np.newaxis, :]
    if len(b.shape) == 1:
        b = b[np.newaxis, :]

    xA = np.maximum(a[:,0], b[:,0])
    yA = np.maximum(a[:,1], b[:,1])
    xB = np.minimum(a[:,2], b[:,2])
    yB = np.minimum(a[:,3], b[:,3])
    interArea = np.maximum(0, xB - xA) * np.maximum(0, yB - yA)
    boxAArea = (a[:,2] - a[:,0]) * (a[:,3] - a[:,1])
    boxBArea = (b[:,2] - b[:,0]) * (b[:,3] - b[:,1])
    return interArea / (boxAArea + boxBArea - interArea)

if __name__ == "__main__":
    print(refine_html("""
    <table>
      <thead>
        <tr>
            <th rowspan="2"></th>
            <th colspan="4"></th>
            <th rowspan="2"></th>
        </tr>
        <tr>
            <th></th>
            <th></th>
            <th></th>
            <th></th>
        </tr>
      </thead>
      <tr>
        <td colspan="6"></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td colspan="6"></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td colspan="6"></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
      <tr>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
        <td></td>
      </tr>
    </table>
    """))