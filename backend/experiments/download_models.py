"""Explicit setup only. Runtime never downloads or executes remote model code."""
import json
import sys
from pathlib import Path
from huggingface_hub import snapshot_download
root=Path(__file__).resolve().parents[2]/'.models'; root.mkdir(exist_ok=True)
manifest=json.loads((Path(__file__).resolve().parents[1]/'model-revisions.json').read_text())
for name,model in manifest.items():
    repo,sha=model['repository'],model['revision']
    snapshot_download(repo,revision=sha,local_dir=root/name,allow_patterns=['*.json','*.txt','*.safetensors','*.model','1_Pooling/*'],ignore_patterns=['onnx/*','openvino/*'])
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
