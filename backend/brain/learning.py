"""Practice-based estimates. Screen exposure never creates mastery evidence."""
import time
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

FEATURES=['days_since_previous_review','prior_attempts','previous_accuracy']

def features(events):
    return np.array([[np.log1p(e['elapsed']),np.log1p(e['prior']),e['previous_accuracy']] for e in events])


def fit_recall(events):
    if len(events)<50 or len({e['correct'] for e in events})<2:
        return None,{'status':'collecting','events':len(events),'required':50,'message':'Use the rule-based schedule until at least 50 genuine practice events with successes and failures exist.'}
    events=sorted(events,key=lambda e:e['at']); split=int(len(events)*.8)
    train,test=events[:split],events[split:]
    if len({e['correct'] for e in train})<2: return None,{'status':'collecting','message':'Training history needs both successes and failures.'}
    model=LogisticRegression(C=.5,max_iter=500,random_state=42).fit(features(train),[e['correct'] for e in train])
    p=model.predict_proba(features(test))[:,1]; y=[e['correct'] for e in test]
    baseline=np.full(len(test),np.mean([e['correct'] for e in train]))
    metrics={'status':'experimental','events':len(events),'train_events':len(train),'test_events':len(test),'split':'chronological 80/20',
        'brier':float(brier_score_loss(y,p)),'baseline_brier':float(brier_score_loss(y,baseline)),
        'log_loss':float(log_loss(y,np.column_stack((1-p,p)),labels=[0,1])),
        'features':FEATURES,'message':'Experimental recall estimate, not a mastery label. Held-out metrics use only earlier history.'}
    model.fit(features(events),[e['correct'] for e in events])
    return model,metrics


def dashboard(store):
    events=store.rows('SELECT * FROM events ORDER BY at,id')
    model,metrics=fit_recall(events)
    reviews=store.rows('SELECT r.*,m.title,m.topic FROM reviews r JOIN memories m ON m.id=r.memory_id ORDER BY r.due')
    now=time.time()
    for review in reviews:
        history=[e for e in events if e['review_id']==review['id']]
        review['due_now']=review['due']<=now; review['attempts']=len(history)
        review['recall_probability']=None
        if model is not None and history:
            f={'elapsed':max(0,(now-history[-1]['at'])/86400),'prior':len(history),'previous_accuracy':sum(e['correct'] for e in history)/len(history)}
            review['recall_probability']=float(model.predict_proba(features([f]))[0,1])
    return {'reviews':reviews,'model':metrics,'schedule':'Rule baseline: independent success doubles interval up to 90 days; failure or hint resets to 1 day. Self-assessed outcomes can be noisy.'}
