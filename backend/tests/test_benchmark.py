import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('benchmark',Path(__file__).parents[1]/'experiments/milestone_benchmark.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

def test_frozen_data_and_source_disjoint_labels():
    data,manifest=b.dataset()
    assert len([c for c in data['cases'] if c['split']=='test'])==24
    assert not manifest['independent_human_review']

def test_scorer_rejects_irrelevant_valid_citation_and_separates_errors():
    c={'expected':'supported','evidence':[{'document':'a','quote':'Correct fact.'}]}
    r={'status':'supported','citations':[{'memory_id':'1','quote':'Related but wrong fact.'}]}
    g=b.grade(c,r,{'1':'a'})
    assert not g['passed'] and g['gold_matched_citations']==0
    m=b.metrics([dict(c,result=r,grade=g,seconds=1),dict(c,error='timeout',seconds=2)])
    assert m['errors']==1 and m['false_refusal_rate']==0 and m['gold_excerpt_match_precision']==0

def test_conflict_requires_both_gold_sources_and_conflict_flag():
    c={'expected':'conflict','evidence':[{'document':'a','quote':'Old.'},{'document':'b','quote':'New.'}]}
    r={'status':'supported','conflict':False,'citations':[{'memory_id':'1','quote':'Old.'},{'memory_id':'2','quote':'New.'}]}
    assert not b.grade(c,r,{'1':'a','2':'b'})['passed']
    r['conflict']=True
    assert b.grade(c,r,{'1':'a','2':'b'})['passed']
