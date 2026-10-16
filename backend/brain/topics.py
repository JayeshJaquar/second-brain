import json
import numpy as np
from pathlib import Path
from .config import MODELS

class TopicClassifier:
    """Inference from our own JSON coefficients; no pickle loading or remote code."""
    def __init__(self,path=MODELS/'topic-model.json'): self.path=Path(path)
    def predict(self,text):
        if not self.path.exists(): return 'unclassified'
        from sklearn.feature_extraction.text import TfidfVectorizer
        p=json.loads(self.path.read_text())
        vectorizer=TfidfVectorizer(vocabulary=p['vocabulary'],ngram_range=(1,2),sublinear_tf=True)
        vectorizer.idf_=np.array(p['idf'])
        x=vectorizer.transform([text]); score=np.asarray(x@np.array(p['coef']).T).ravel()+p['intercept']
        return p['classes'][int(np.argmax(score))]
