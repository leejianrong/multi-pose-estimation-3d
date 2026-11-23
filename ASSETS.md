# Assets and licences

Every file under `assets/`, and every model fetched at first run, needs a row here (ADR-0006).
`make check-assets` fails when one is missing. Licences marked *unverified* must be confirmed
before the file is committed (card MP3D-2).

| Path or source | What | Licence | URL | Verified |
|---|---|---|---|---|
| assets/avatars/CesiumMan.glb | Rigged, textured walking man (V1 smoke avatar). Attribution: © 2017 Cesium, via KhronosGroup/glTF-Sample-Assets. Contains a non-copyrightable Cesium logo mark. | CC-BY-4.0 | https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/CesiumMan | 2026-11-22, from the model's README Legal section |
| rtmlib (Python package) | RTMPose/YOLOX inference wrapper | Apache-2.0 | https://github.com/Tau-J/rtmlib | 2026-11-22, repo licence and PyPI metadata |
| RTMPose-s body7 and YOLOX-tiny humanart ONNX weights | Not committed. Downloaded by rtmlib at first run from download.openmmlab.com into `models/` (gitignored) | MMPose and YOLOX code are Apache-2.0. **Training-data terms of the Body7 mix and HumanArt were not audited**, so treat redistribution of the weights as unverified | https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose | partial: code licence only |
| onnxruntime, opencv-python | Inference and image ops (runtime dependencies) | MIT, Apache-2.0 (and bundled FFmpeg LGPL in opencv wheels) | PyPI | 2026-11-22, upstream metadata |
| three, vite, vitest, typescript | App dependencies | MIT, MIT, MIT, Apache-2.0 | npm | 2026-11-22, npm metadata |
