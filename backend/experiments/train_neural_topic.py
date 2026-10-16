"""Small neural classifier on frozen transformer features. Synthetic training demo only."""
import copy
import json
import sys
from pathlib import Path
import numpy as np
import torch
from torch import nn
from sklearn.metrics import f1_score,confusion_matrix
from sentence_transformers import SentenceTransformer
from safetensors.torch import save_file
root=Path(__file__).resolve().parents[2]; torch.manual_seed(42); np.random.seed(42)
torch.set_num_threads(2)
docs=json.loads((root/'backend/data/corpus-v1.json').read_text())['documents']
classes=sorted({d['topic'] for d in docs})
encoder=SentenceTransformer(str(root/'.models/encoder'),local_files_only=True,device='cpu')
x=torch.tensor(encoder.encode([d['text'] for d in docs],normalize_embeddings=True)); y=torch.tensor([classes.index(d['topic']) for d in docs])
indices={s:torch.tensor([i for i,d in enumerate(docs) if d['split']==s]) for s in ['train','dev','test']}
model=nn.Sequential(nn.Linear(x.shape[1],64),nn.ReLU(),nn.Dropout(.2),nn.Linear(64,len(classes)))
optimizer=torch.optim.AdamW(model.parameters(),lr=.003,weight_decay=.02); lossfn=nn.CrossEntropyLoss()
best=float('inf'); beststate=None; patience=0; curve=[]
for epoch in range(150):
 model.train(); optimizer.zero_grad(); loss=lossfn(model(x[indices['train']]),y[indices['train']]); loss.backward(); optimizer.step()
 model.eval()
 with torch.no_grad(): dev=lossfn(model(x[indices['dev']]),y[indices['dev']]).item()
 curve.append({'epoch':epoch+1,'train_loss':loss.item(),'dev_loss':dev})
 if dev<best-1e-4: best=dev; beststate=copy.deepcopy(model.state_dict()); patience=0
 else: patience+=1
 if patience>=15: break
model.load_state_dict(beststate); model.eval()
with torch.no_grad(): pred=model(x[indices['test']]).argmax(1).numpy()
actual=y[indices['test']].numpy()
report={'scope':'Synthetic small-data demonstration; encoder frozen, only the 2-layer head is trained.',
 'architecture':[int(x.shape[1]),64,len(classes)],'seed':42,'train':len(indices['train']),'dev':len(indices['dev']),'test':len(indices['test']),
 'early_stopping':'development cross-entropy, patience 15; test used once after selection','epochs_run':len(curve),
 'macro_f1':f1_score(actual,pred,average='macro'),'classes':classes,'confusion':confusion_matrix(actual,pred,labels=range(len(classes))).tolist(),'loss_curve':curve}
save_file(model.state_dict(),str(root/'.models/topic-neural.safetensors'))
(root/'.models/topic-neural-config.json').write_text(json.dumps({'classes':classes,'architecture':report['architecture']}))
(root/'test-results/neural-topic-v1.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k not in ['loss_curve','confusion']})
