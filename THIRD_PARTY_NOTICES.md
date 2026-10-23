# Third-Party Notices

This project includes or adapts code from the third-party
projects listed below. The original copyright notices and license terms are
reproduced or referenced here as required by their licenses.

---

## 1. GriTS (Grid Table Similarity) - Table Transformer

- **Project:** Table Transformer (TATR) / PubTables-1M / GriTS
- **Source:** https://github.com/microsoft/table-transformer
- **Copyright:** Copyright (c) Microsoft Corporation
  <!-- TODO: verify this line against the LICENSE file at the repo root and copy it exactly. -->
- **License:** MIT
- **Files used / adapted:** [e.g. src/grits.py — list exact files and functions]
- **Modifications:** [Describe changes, or write "None"]
- **Reference:** Smock, B., Pesala, R., Abraham, R. "GriTS: Grid table similarity
  metric for table structure recognition." ICDAR 2023. https://arxiv.org/abs/2203.12555

```
MIT License

Copyright (c) Microsoft Corporation.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 2. TEDS (Tree-Edit-Distance-based Similarity) - PubTabNet

- **Project:** PubTabNet (IBM Research)
- **Source:** https://github.com/ibm-aur-nlp/PubTabNet (file: `src/metric.py`)
- **Copyright:** Copyright 2020 IBM
- **License:** Apache License, Version 2.0
  (https://www.apache.org/licenses/LICENSE-2.0)
- **Files used / adapted:** [e.g. src/metric.py — list exact files and functions]
- **Modifications:** [Describe changes, or write "None"]
  <!-- Apache-2.0 requires modified files to carry prominent notices that they were changed. -->
- **Reference:** Zhong, X., ShafieiBavani, E., Jimeno Yepes, A. "Image-based table
  recognition: data, model, and evaluation." https://arxiv.org/abs/1911.10683

The original file header reads:

```
Copyright 2020 IBM
Author: peter.zhong@au1.ibm.com

This is free software; you can redistribute it and/or modify
it under the terms of the Apache 2.0 License.

This software is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
Apache 2.0 License for more details.
```

The full text of the Apache License 2.0 is included in
`third_party/PubTabNet/LICENSE`.

<!-- TODO: copy the LICENSE file from https://github.com/ibm-aur-nlp/PubTabNet/tree/master/src into that path. -->

Any `NOTICE` file distributed with the original work, if present, must also be preserved.

---

## 3. Dependencies of the code above

The adapted TEDS code imports third-party packages (for example `apted`, `distance`,
`lxml`, `tqdm`). They are not bundled here. If you distribute them with your
product, list each one with its own license in this file.

<!-- TODO: run a license scanner (pip-licenses, scancode-toolkit) and add entries. -->

---

## 4. Datasets and model weights (only if you use or redistribute them)

This notice covers **source code only**. Datasets (PubTables-1M, FinTabNet.c,
PubTabNet) and pre-trained model weights are separate works with their own terms
and are **not** covered by the licenses above. Add separate entries if you use them.

---

## Citation

If you publish results computed with these metrics, please cite the original papers
listed above.

