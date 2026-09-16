import json, os, statistics as st
from collections import defaultdict
S=os.environ['S']; A=json.load(open(S+'/analysis.json'))
R='results/runs/qwen3-4b'
runs={'a0_noplan':'20260912_165017_leetcode_train_medhard_filtered_rh_simple_overwrite_tests_baseline','a0_plan':'20260912_123126_leetcode_train_medhard_filtered_rh_simple_overwrite_tests_baseline_plan','a1_const':'20260912_145350_leetcode_train_medhard_filtered_rh_simple_overwrite_tests_constitution_constitution_deontological_plan','a0_think':'20260912_185146_leetcode_train_medhard_filtered_rh_simple_overwrite_tests_baseline_think'}
print('== a0_think steps 26-46 (log)')
for d in A['log']['a0_think']:
    if 26<=d['step']<=46: print(d['step'],'score%.2f'%d['critic/score/mean'],'len%.0f'%d['response_length/mean'],'clip%.2f'%d['response_length/clip_ratio'],'ent%.3f'%d['actor/entropy'],'kl%.3f'%d['actor/kl_loss'],'gn%.3f'%d['actor/grad_norm'],'pg%.4f'%d['actor/pg_loss'],'advmin%.2f'%d['critic/advantages/min'],'advmax%.2f'%d['critic/advantages/max'],'adv0%.2f'%d['actor/frac_adv_zero'])
# advantage token-mass per step
mass={}
for tag,d in runs.items():
    rows=[]
    for step in range(1,201):
        f=f'{R}/{d}/rollouts/{step}.jsonl'
        if not os.path.exists(f): continue
        rs=[json.loads(l) for l in open(f)]
        g=defaultdict(list)
        for r in rs: g[r['id']].append(r)
        pos=neg=0.0; npos=nneg=0; lens_pos=[]; lens_neg=[]
        for grp in g.values():
            sc=[r['score'] for r in grp]; m=st.mean(sc); sd=st.pstdev(sc)*(len(sc)/(len(sc)-1))**0.5 if len(sc)>1 else 1
            for r in grp:
                a=(r['score']-m)/(sd+1e-6) if sd>0 else 0.0
                L=len(r['output'])/3.6
                if a>0: pos+=a*L; npos+=1; lens_pos.append(L)
                elif a<0: neg+=-a*L; nneg+=1; lens_neg.append(L)
        rows.append({'step':step,'pos_mass':pos,'neg_mass':neg,'neg_frac':neg/(pos+neg) if pos+neg>0 else None,'n_pos':npos,'n_neg':nneg,'len_pos_med':st.median(lens_pos) if lens_pos else None,'len_neg_med':st.median(lens_neg) if lens_neg else None})
    mass[tag]=rows
    print('==mass',tag,[(r['step'],round(r['neg_frac'],2) if r['neg_frac'] is not None else None,r['n_pos'],r['n_neg'],int(r['len_pos_med'] or 0),int(r['len_neg_med'] or 0)) for r in rows if r['step'] in (1,5,10,15,20,25,30,35,40,50,75,100,150,200)])
A['mass']=mass
# per-rollout length distributions (token est) at steps for a0_think
dist={}
for step in (1,10,20,30,35,38,40,45,50,60,100):
    f=f'{R}/{runs["a0_think"]}/rollouts/{step}.jsonl'
    if not os.path.exists(f): continue
    rs=[json.loads(l) for l in open(f)]
    dist[step]=[{'len':int(len(r['output'])/3.6),'closed':'</think>' in r['output'],'correct':bool(r['eq_correct']),'score':r['score']} for r in rs]
A['dist']=dist
json.dump(A,open(S+'/analysis.json','w'),indent=1)
# examples
ex=A['examples']['a0_think']
for step in ('1','30','40','50','60','100'):
    if step in ex:
        print(f'\n######## step {step} UNCLOSED TAIL:\n', ex[step]['unc_tail'][-700:].replace('\n','⏎'))
