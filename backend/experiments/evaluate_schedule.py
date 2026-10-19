"""Synthetic policy comparison, not evidence of improved human recall."""
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from brain.learning import fit_recall,shadow_interval
root=Path(__file__).resolve().parents[2];rng=np.random.default_rng(42)
events=[]
for i in range(500):
    elapsed=int(rng.choice([1,2,4,7,14,21,30]));prior=int(rng.integers(1,25));accuracy=float(rng.uniform(.2,.95))
    logit=3.0-1.4*np.log1p(elapsed)+.3*np.log1p(prior)+accuracy
    correct=int(rng.random()<1/(1+np.exp(-logit)))
    events.append({'at':i,'correct':correct,'elapsed':elapsed,'prior':prior,'previous_accuracy':accuracy})
model,metrics=fit_recall(events);rows=[]
if metrics['shadow_eligible']:
    for prior,accuracy,previous in [(2,.4,1),(5,.6,2),(12,.8,7),(20,.9,14)]:
        rows.append({'prior_attempts':prior,'previous_accuracy':accuracy,'rule_after_success_days':min(90,previous*2),
            'learned_shadow_days':shadow_interval(model,prior,accuracy)})
report={'scope':'Original seeded synthetic outcomes; validates evaluation and shadow-policy wiring only. Does not measure human learning or causal scheduling benefit.',
    'seed':42,'model_metrics':metrics,'policy_comparisons':rows,'active_policy_changed':False}
(root/'test-results/scheduling-comparison-v2.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
