#!/usr/bin/env python3
"""Read-only dependency compatibility check; never instantiate SoulBenchDB."""
import argparse,sys,sqlite3,json,socket
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
def blocked(*args,**kwargs): raise RuntimeError('Audit: network disabled')
socket.socket.connect=blocked;socket.create_connection=blocked
sys.path.insert(0,str(a.root.resolve()))
import pandas as pd
import pingouin as pg
from src.analyzer import _compute_icc
c=sqlite3.connect((a.root/'data/snap_poc_v3_1.db').resolve().as_uri()+'?mode=ro',uri=True)
c.execute('PRAGMA query_only=ON')
df=pd.read_sql_query('select model,item_id,system_prompt,run,score_final from responses',c)
df['score_numeric']=pd.to_numeric(df.score_final,errors='coerce');df=df.dropna(subset=['score_numeric'])
r={'pingouin_version':pg.__version__,'models':{}}
for model,g in df.groupby('model'):
    direct=g.copy();direct['target']=direct.item_id+'/'+direct.system_prompt
    try:
        table=pg.intraclass_corr(data=direct,targets='target',raters='run',ratings='score_numeric')
        direct_result=table[['Type','ICC']].to_dict('records')
    except ValueError as e:direct_result={'error':str(e)}
    r['models'][model]={'library':direct_result,'snap':_compute_icc(g,['item_id','system_prompt'],5)}
a.out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
print(json.dumps(r,indent=2))
