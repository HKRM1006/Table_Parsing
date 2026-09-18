import numpy as np
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