"""Reproducible synthetic retrieval and topic-classification experiment, no user data."""
import hashlib
import json
import platform
import statistics
import sys
import tempfile
import time
import uuid
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report,confusion_matrix,f1_score
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brain.store import Store
from brain.retrieval import Retriever
from brain.config import MODELS
root=Path(__file__).resolve().parents[2]
path=root/'backend/data/corpus-v1.json'; data=json.loads(path.read_text())
report={'dataset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'description':data['description'],'python':platform.python_version(),
        'models':json.loads((MODELS/'manifest.json').read_text()),'documents':len(data['documents']),'queries':len(data['queries']),'retrieval':{}}
with tempfile.TemporaryDirectory() as temp:
 store=Store(Path(temp)); ids={}
 for d in data['documents']:
  mid=str(uuid.uuid5(uuid.NAMESPACE_URL,'second-brain-fixture:'+d['id'])); ids[mid]=d['id']
  store.add(id=mid,title=d['id'],source='Synthetic corpus v1',text=d['text'],created_at=1)
 retriever=Retriever(store)
 retriever.index_pending()
 for mode in ['lexical','dense','hybrid','rerank']:
  scores=[]; timings=[]
  for q in [q for q in data['queries'] if q['split']=='test' and q['relevant']]:
   start=time.perf_counter(); rows,warning,actual=retriever.search(q['text'],mode,limit=20); timings.append(time.perf_counter()-start)
   ranked=list(dict.fromkeys(ids[r['memory_id']] for r in rows))[:5]
   ranks=[i+1 for i,mid in enumerate(ranked) if mid in q['relevant']]
   scores.append({'query':q['id'],'ranked':ranked,'recall5':len(set(ranked)&set(q['relevant']))/len(q['relevant']),'rr5':1/min(ranks) if ranks else 0})
  report['retrieval'][mode]={'recall5':statistics.mean(x['recall5'] for x in scores),'mrr5':statistics.mean(x['rr5'] for x in scores),
    'first_query_seconds':timings[0],'warm_p50_seconds':statistics.median(timings[1:]),'warm_p95_seconds':float(np.percentile(timings[1:],95)),'queries':scores}
  print(mode,report['retrieval'][mode]['recall5'],report['retrieval'][mode]['mrr5'],flush=True)
 train=[d for d in data['documents'] if d['split']=='train']; test=[d for d in data['documents'] if d['split']=='test']
 labels=[d['topic'] for d in train]; y=[d['topic'] for d in test]
 vectorizer=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)
 x=vectorizer.fit_transform(d['text'] for d in train); xt=vectorizer.transform(d['text'] for d in test)
 linear=LogisticRegression(C=2,max_iter=1000,random_state=42).fit(x,labels); pred=linear.predict(xt)
 report['classification']={'train_documents':len(train),'test_documents':len(test),'tfidf_macro_f1':f1_score(y,pred,average='macro'),
    'tfidf_report':classification_report(y,pred,output_dict=True,zero_division=0),'classes':linear.classes_.tolist(),'tfidf_confusion':confusion_matrix(y,pred,labels=linear.classes_).tolist()}
 artifact={'classes':linear.classes_.tolist(),'vocabulary':vectorizer.vocabulary_,'idf':vectorizer.idf_.tolist(),'coef':linear.coef_.tolist(),'intercept':linear.intercept_.tolist(),'training_data':'synthetic corpus-v1 train split; suggestions only'}
 (MODELS/'topic-model.json').write_text(json.dumps(artifact))
 encoder=retriever.load(); ex=encoder.encode([d['text'] for d in train],normalize_embeddings=True); et=encoder.encode([d['text'] for d in test],normalize_embeddings=True)
 dense=LogisticRegression(C=2,max_iter=1000,random_state=42).fit(ex,labels); dp=dense.predict(et)
 report['classification']['embedding_macro_f1']=f1_score(y,dp,average='macro')
 report['classification']['embedding_confusion']=confusion_matrix(y,dp,labels=dense.classes_).tolist()
 (MODELS/'topic-dense-model.json').write_text(json.dumps({'classes':dense.classes_.tolist(),'coef':dense.coef_.tolist(),'intercept':dense.intercept_.tolist(),'encoder':report['models']['encoder']}))
 store.db.close()
report['limitations']=['Synthetic authored data, not a real-world benchmark.','No hyperparameter tuning on test queries.','Classifier is a small-data demonstration, not a reliable personal topic model.','Unanswerable queries require separate answer evaluation; ranking metrics do not measure abstention.','Document ranking deduplicates chunks; first-query loading is reported separately.']
(root/'test-results/python-evaluation-v1.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report['classification'],indent=2))
