#!/usr/bin/env python3
"""Independent audit. SQLite read-only; no SNAP imports; no raw-text exports."""
from pathlib import Path
import sqlite3, json, csv, hashlib, math, statistics, argparse
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations

def kappa(pairs):
    n=len(pairs)
    a,b=Counter(x for x,y in pairs),Counter(y for x,y in pairs)
    po=sum(x==y for x,y in pairs)/n
    pe=sum(a[k]*b[k] for k in a.keys()|b.keys())/n**2
    return {'n':n,'agreement':po,'kappa':(po-pe)/(1-pe), 'marginal_a':dict(a),'marginal_b':dict(b)}
def pearson(pairs):
    x,y=zip(*pairs);mx,my=statistics.mean(x),statistics.mean(y)
    den=math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
    return sum((a-mx)*(b-my) for a,b in pairs)/den if den else None
def icc(x):
    if any(v is None for row in x for v in row):return None
    n,k=len(x),len(x[0]);g=statistics.mean(v for row in x for v in row)
    rm=[statistics.mean(row) for row in x];cm=[statistics.mean(row[j] for row in x) for j in range(k)]
    mr=k*sum((v-g)**2 for v in rm)/(n-1);mc=n*sum((v-g)**2 for v in cm)/(k-1)
    me=sum((x[i][j]-rm[i]-cm[j]+g)**2 for i in range(n) for j in range(k))/((n-1)*(k-1))
    return (mr-me)/(mr+(k-1)*me+k*(mc-me)/n)
def ro(p):
    c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');return c
def numeric(s): return None if s not in ('-1','0','+1','1') else int(s)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    c=ro(args.root/'data/snap_poc_v3_1.db');v=ro(args.root/'data/snap_poc_v3_1_human_validation_clean.db')
    rows=[dict(r) for r in c.execute('select * from responses order by id')];vr=[dict(r) for r in v.execute('select * from responses order by id')]
    byid={r['id']:r for r in rows};group=defaultdict(list)
    for r in rows:group[r['model']].append(r)
    report={'sqlite_integrity':{'campaign':c.execute('PRAGMA integrity_check').fetchone()[0],'validation':v.execute('PRAGMA integrity_check').fetchone()[0]},'n':len(rows),'unique_trial_ids':len(set(r['trial_id'] for r in rows)), 'response_tables_identical': rows==vr}
    report['logical_responses_sha256']=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    report['counts']={key:dict(Counter(str(r[key]) for r in rows)) for key in ['model','system_prompt','item_type','score_final','agreement_status','manual_review_needed','is_refusal','is_truncated','is_error','dataset_id','protocol_version','items_version','condition_block']}
    report['duplicate_condition_keys']=len(rows)-len({tuple(r[k] for k in ['model','item_id','item_type','scenario','formulation','system_prompt','temperature','run']) for r in rows})
    cells=Counter((r['model'],r['item_id'],r['system_prompt']) for r in rows)
    report['cells']={'n':len(cells),'size_distribution':dict(Counter(cells.values()))}
    pairs=[(r['score_judge1'],r['score_judge2']) for r in rows if r['score_judge1'] is not None and r['score_judge2'] is not None]
    report['judge_agreement']=kappa(pairs)
    report['judge_confusion']={f'{a}/{b}':n for (a,b),n in sorted(Counter(pairs).items())}
    report['resolution_rule_violations']=[]
    for r in rows:
        a,b=r['score_judge1'],r['score_judge2'];expected=None
        if a is not None and b is not None:
            if a==b:expected=a
            elif a!='REFUS' and b!='REFUS' and abs(int(a)-int(b))==1:expected='0'
        if expected is not None and r['score_final']!=expected:report['resolution_rule_violations'].append(r['id'])
    manual=[dict(r) for r in c.execute('select * from manual_verification order by id')]
    report['adjudication']={'n':len(manual),'unique_response_ids':len({r['response_id'] for r in manual}), 'orphans':[r['id'] for r in manual if r['response_id'] not in byid], 'final_mismatch':[r['response_id'] for r in manual if r['human_score']!=byid[r['response_id']]['score_final']]}
    report['metadata']=[dict(r) for r in c.execute('select * from collection_metadata order by model')]
    report['truncated']={'n':sum(r['is_truncated'] for r in rows),'model':dict(Counter(r['model'] for r in rows if r['is_truncated'])),'tokens':dict(Counter(r['completion_tokens'] for r in rows if r['is_truncated'])),'sp':dict(Counter(r['system_prompt'] for r in rows if r['is_truncated']))}
    human=[dict(r) for r in v.execute("select * from manual_verification where source='human_validation' order by response_id")]
    with (args.root/'data/manual_sample_coded.csv').open(newline='') as f: coded=list(csv.DictReader(f))
    csvby={int(r['response_id']):r for r in coded};humanby={r['response_id']:r for r in human}
    report['human']={'n':len(human),'unique_response_ids':len(humanby),'csv_n':len(coded),'csv_fields':list(coded[0]),'csv_ids_equal':csvby.keys()==humanby.keys(),'coverage':dict(Counter(byid[r['response_id']]['model'] for r in human))}
    report['human']['csv_label_mismatch']=[i for i,r in csvby.items() if r['human_score']!=humanby[i]['human_score']]
    report['human']['csv_context_mismatch']=[{'id':i,'field':k} for i,r in csvby.items() for k in ['model','item_id','system_prompt','raw_response','score_final'] if r[k]!=str(byid[i][k])]
    for field in ['score_judge1','score_judge2','score_final']:
        report['human'][field]=kappa([(r['human_score'],byid[r['response_id']][field]) for r in human if byid[r['response_id']][field] is not None])
    report['models']={};repeat_records=[]
    for model,rs in group.items():
        index={(r['item_id'],r['system_prompt'],r['run']):r for r in rs};targets=sorted({(r['item_id'],r['system_prompt']) for r in rs})
        matrix=[[numeric(index[(i,s,run)]['score_final']) for run in range(1,11)] for i,s in targets]
        halves=[(statistics.mean(v for v in row[:5] if v is not None),statistics.mean(v for v in row[5:] if v is not None)) for row in matrix]
        mm={'n':len(rs),'start':min(r['timestamp'] for r in rs),'end':max(r['timestamp'] for r in rs),'icc2_1':icc(matrix),'split_half':pearson(halves),'cross_sp':{},'flags':dict(Counter(str((r['temperature_applied'],r['top_p_applied'],r['thinking_enabled'])) for r in rs))}
        for s1,s2 in combinations(['SP_ABS','SP_DIR','SP_PER'],2):
            pp=[]
            for i in sorted({r['item_id'] for r in rs}):
                for run in range(1,11):
                    a,b=numeric(index[(i,s1,run)]['score_final']),numeric(index[(i,s2,run)]['score_final'])
                    if a is not None and b is not None:pp.append((a,b))
            mm['cross_sp'][s1+'/'+s2]={'n':len(pp),'pearson':pearson(pp)}
        # Reconstruct equality from stored message texts and recorded sent/omitted flags.
        # max_tokens=2048 and supported top_p=1.0 inferred from config/code, not per-call logs.
        payload_groups=defaultdict(list)
        for r in rs:
            messages=[]
            if r['system_prompt_text']:messages.append({'role':'system','content':r['system_prompt_text'].strip()})
            messages.append({'role':'user','content':r['user_prompt_text']})
            payload={'model_internal_alias':model,'messages':messages,'max_tokens':2048}
            if r['temperature_applied']:payload['temperature']=r['temperature']
            if r['top_p_applied']:payload['top_p']=1.0
            h=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            payload_groups[h].append(r)
        mm['reconstructible_request_groups']={'unique':len(payload_groups),'multiplicity':dict(Counter(len(x) for x in payload_groups.values()))}
        for h,gr in payload_groups.items():
            for a,b in combinations(sorted(gr,key=lambda r:r['run']),2):
                dt=abs((datetime.fromisoformat(a['timestamp'])-datetime.fromisoformat(b['timestamp'])).total_seconds())
                repeat_records.append({'model':model,'item_id':a['item_id'],'system_prompt':a['system_prompt'],'run_a':a['run'],'run_b':b['run'],'id_a':a['id'],'id_b':b['id'],'request_signature':h,'score_a':a['score_final'],'score_b':b['score_final'],'raw_text_equal':a['raw_response']==b['raw_response'],'delta_seconds':dt,'timestamp_a':a['timestamp'],'timestamp_b':b['timestamp'],'prompt_tokens_equal':a['prompt_tokens']==b['prompt_tokens'],'temperature_a':a['temperature'],'temperature_b':b['temperature']})
        report['models'][model]=mm
    report['opportunistic_repeats']={'n':len(repeat_records),'group_counts':dict(Counter(r['model'] for r in repeat_records)),'raw_equal':sum(r['raw_text_equal'] for r in repeat_records),'prompt_tokens_equal':sum(r['prompt_tokens_equal'] for r in repeat_records),'run_pairs':dict(Counter(f"{r['run_a']}/{r['run_b']}" for r in repeat_records)),'score_agreement':kappa([(r['score_a'],r['score_b']) for r in repeat_records]),'score_pearson':pearson([(int(r['score_a']),int(r['score_b'])) for r in repeat_records]),'time_delta_seconds':{'min':min(r['delta_seconds'] for r in repeat_records),'median':statistics.median(r['delta_seconds'] for r in repeat_records),'max':max(r['delta_seconds'] for r in repeat_records)},'by_sp':{sp:kappa([(r['score_a'],r['score_b']) for r in repeat_records if r['system_prompt']==sp]) for sp in ['SP_ABS','SP_DIR','SP_PER']}}
    with (args.out/'gpt52_opportunistic_pairs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(repeat_records[0]));w.writeheader();w.writerows(sorted(repeat_records,key=lambda r:(r['item_id'],r['system_prompt'],r['run_a'])))
    (args.out/'independent_results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:report[k] for k in ['n','unique_trial_ids','response_tables_identical','resolution_rule_violations','judge_agreement','adjudication','human','opportunistic_repeats']},indent=2))

if __name__=='__main__':main()
