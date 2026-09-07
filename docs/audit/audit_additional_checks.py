#!/usr/bin/env python3
"""Additional independent screens: config fidelity, item scoring and exceptions."""
from pathlib import Path
import argparse,sqlite3,json,csv,collections,hashlib
import yaml
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
def ro(p):
 c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');return c
c=ro(a.root/'data/snap_poc_v3_1.db');v=ro(a.root/'data/snap_poc_v3_1_human_validation_clean.db')
rows=[dict(r) for r in c.execute('select * from responses order by id')]
config={p.stem:yaml.safe_load(p.read_text()) for p in (a.root/'config').glob('*.yaml')}
items={r['id']:r for kind in ['items_personality','items_moral'] for r in config[kind]['items']}
schedule={r['run']:r for r in config['protocol']['run_schedule']}
out={'config_mismatches':[], 'condition_fields_missing':[], 'item_agreement':[]}
for r in rows:
 item=items[r['item_id']]
 user=(str(item['scenarios'][r['scenario']]['text']).strip()+'\n\n'+str(item['formulations'][r['formulation']]).strip()).strip()
 system=(config['system_prompts']['system_prompts'][r['system_prompt']] or '').strip()
 for label,ok in [('user',r['user_prompt_text']==user),('system',(r['system_prompt_text'] or '').strip()==system),('schedule',all(r[k]==schedule[r['run']][k] for k in ['scenario','formulation','temperature']))]:
  if not ok:out['config_mismatches'].append({'id':r['id'],'field':label})
out['trial_id_reconstruction_mismatches']=[]
for r in rows:
 expected=f"{r['dataset_id']}:{r['model']}:{r['condition_block']}:{r['item_id']}:{r['system_prompt']}:run{r['run']}"
 if r['trial_id']!=expected:out['trial_id_reconstruction_mismatches'].append(r['id'])
 if not r['trial_id']:out['condition_fields_missing'].append(r['id'])
for item in sorted(items):
 rs=[r for r in rows if r['item_id']==item];ps=[(r['score_judge1'],r['score_judge2']) for r in rs if r['score_judge1'] is not None and r['score_judge2'] is not None]
 n=len(ps);x=collections.Counter(p for p,q in ps);y=collections.Counter(q for p,q in ps);po=sum(p==q for p,q in ps)/n;pe=sum(x[k]*y[k] for k in x.keys()|y.keys())/n**2
 out['item_agreement'].append({'item':item,'n':len(rs),'judge_pairs':n,'exact_agreement':po,'kappa':(po-pe)/(1-pe) if pe<1 else None,'final_counts':dict(collections.Counter(r['score_final'] for r in rs))})
out['e1_wordband_mismatch_screen']=[{'id':r['id'],'model':r['model'],'sp':r['system_prompt'],'run':r['run'],'word_count_space_split':len(r['raw_response'].split()),'score_final':r['score_final']} for r in rows if r['item_id']=='E1' and r['score_final']!=('+1' if len(r['raw_response'].split())>150 else '-1' if len(r['raw_response'].split())<100 else '0')]
out['exception_rows']={label:[{k:r[k] for k in ['id','model','item_id','system_prompt','run','score_judge1','score_judge2','score_final','agreement_status','completion_tokens']} for r in rows if condition(r)] for label,condition in [('missing_second_judge',lambda r:r['score_judge2'] is None),('refusals',lambda r:r['is_refusal']==1),('truncated',lambda r:r['is_truncated']==1)]}
out['foreign_key_check']={'campaign':[tuple(r) for r in c.execute('PRAGMA foreign_key_check')],'validation':[tuple(r) for r in v.execute('PRAGMA foreign_key_check')]}
coded={int(r['response_id']):r for r in csv.DictReader((a.root/'data/manual_sample_coded.csv').open())};hum=[dict(r) for r in v.execute("select * from manual_verification where source='human_validation'")];byid={r['id']:r for r in rows}
out['csv_justification_match']=all(coded[r['response_id']]['human_justification']==r['human_justification'] for r in hum)
out['csv_nominal_temperature_match']=all(float(r['temperature'])==byid[i]['temperature'] for i,r in coded.items())
out['validation_source_counts']=[dict(r) for r in v.execute('select source,count(*) as n,count(distinct response_id) as distinct_ids,min(verified_at) as min_verified_at,max(verified_at) as max_verified_at from manual_verification group by source')]
out['adjudication_validation_overlap']=v.execute("select count(*) from manual_verification a join manual_verification b on a.response_id=b.response_id where a.source='adjudication' and b.source='human_validation'").fetchone()[0]
out['metadata_response_dates']=[{'model':m['model'],'metadata_start':m['start_time'],'response_start':min(r['timestamp'] for r in rows if r['model']==m['model']),'response_end':max(r['timestamp'] for r in rows if r['model']==m['model'])} for m in c.execute('select model,start_time from collection_metadata order by model')]
a.out.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'config_mismatches':out['config_mismatches'],'trial_id_reconstruction_mismatches':out['trial_id_reconstruction_mismatches'],'foreign_key_check':out['foreign_key_check'],'csv_justification_match':out['csv_justification_match'],'csv_nominal_temperature_match':out['csv_nominal_temperature_match'],'adjudication_validation_overlap':out['adjudication_validation_overlap']},indent=2))
