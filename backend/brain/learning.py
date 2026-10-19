"""Practice-based estimates and shadow scheduling; exposure never creates mastery."""
import time
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss

FEATURES=['days_since_previous_review','prior_attempts','previous_accuracy']
INTERVALS=(1,2,3,5,7,10,14,21,30,45,60,90)

def features(events):
    return np.array([[np.log1p(e['elapsed']),np.log1p(e['prior']),e['previous_accuracy']] for e in events])


def fit_recall(events):
    if len(events)<50 or len({e['correct'] for e in events})<2:
        return None,{'status':'collecting','events':len(events),'required':50,'shadow_eligible':False,
            'message':'Use the rule-based schedule until at least 50 genuine practice events with successes and failures exist.'}
    events=sorted(events,key=lambda e:e['at']); split=int(len(events)*.8)
    train,test=events[:split],events[split:]
    if len({e['correct'] for e in train})<2:
        return None,{'status':'collecting','shadow_eligible':False,'message':'Training history needs both successes and failures.'}
    model=LogisticRegression(C=.5,max_iter=500,random_state=42).fit(features(train),[e['correct'] for e in train])
    p=model.predict_proba(features(test))[:,1]; y=[e['correct'] for e in test]
    baseline=np.full(len(test),np.mean([e['correct'] for e in train]))
    metrics={'status':'experimental','events':len(events),'train_events':len(train),'test_events':len(test),'split':'chronological 80/20',
        'brier':float(brier_score_loss(y,p)),'baseline_brier':float(brier_score_loss(y,baseline)),
        'log_loss':float(log_loss(y,np.column_stack((1-p,p)),labels=[0,1])),
        'baseline_log_loss':float(log_loss(y,np.column_stack((1-baseline,baseline)),labels=[0,1])),
        'features':FEATURES,'message':'Experimental recall estimate, not a mastery label. Held-out metrics use only earlier history.'}
    model.fit(features(events),[e['correct'] for e in events])
    reasons=[]
    if len(test)<20 or len(set(y))<2: reasons.append('Need at least 20 held-out outcomes with both classes.')
    if metrics['brier']>=metrics['baseline_brier']: reasons.append('Recall model has not beaten the held-out mean baseline.')
    if model.coef_[0,0]>=0: reasons.append('Learned elapsed-time effect does not decrease recall.')
    metrics.update(shadow_eligible=not reasons,shadow_gate_reasons=reasons,
        scheduling='Shadow comparison only; the rule-based due date remains active.',target_recall=.8)
    return model,metrics


def shadow_interval(model,prior,accuracy,target=.8):
    rows=[{'elapsed':d,'prior':prior,'previous_accuracy':accuracy} for d in INTERVALS]
    p=model.predict_proba(features(rows))[:,1]
    acceptable=[d for d,prob in zip(INTERVALS,p) if prob>=target]
    return max(acceptable) if acceptable else 1


def dashboard(store):
    events=store.rows('SELECT * FROM events ORDER BY at,id')
    model,metrics=fit_recall(events)
    reviews=store.rows('SELECT r.*,m.title,m.topic FROM reviews r JOIN memories m ON m.id=r.memory_id ORDER BY r.due')
    now=time.time()
    for review in reviews:
        history=[e for e in events if e['review_id']==review['id']]
        review.update(due_now=review['due']<=now,attempts=len(history),recall_probability=None,shadow_interval_days=None,history=history[-5:])
        if model is not None and history:
            accuracy=sum(e['correct'] for e in history)/len(history)
            f={'elapsed':max(0,(now-history[-1]['at'])/86400),'prior':len(history),'previous_accuracy':accuracy}
            review['recall_probability']=float(model.predict_proba(features([f]))[0,1])
            if metrics['shadow_eligible']: review['shadow_interval_days']=shadow_interval(model,len(history),accuracy)
    return {'reviews':reviews,'model':metrics,'schedule':'Rule baseline: independent success doubles interval up to 90 days; failure or hint resets to 1 day. Self-assessed outcomes can be noisy.'}
