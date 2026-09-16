import json, re, os, glob, zlib, statistics as st
from collections import defaultdict
R='results/runs/qwen3-4b'; L='experiments/motivated-reasoning/logs'
runs={'a0_noplan':'20260912_165017_leetcode_train_medhard_filtered_rh_simple_overwrite_tests_baseline',
      'a0_plan':'20260912_123126_leetcode_train_medhard_filtered_rh_simple_overwrite_tests_baseline_plan',
      'a1_const':'20260912_145350_leetcode_train_medhard_filtered_rh_simple_overwrite_tests_constitution_constitution_deontological_plan',
      'a0_think':'20260912_185146_leetcode_train_medhard_filtered_rh_simple_overwrite_tests_baseline_think',
      'a0_plan_think_probe':'20260912_164005_leetcode_train_medhard_filtered_rh_simple_overwrite_tests_baseline_plan_think'}
logs={'a0_noplan':'phase1_a0_noplan.log','a0_plan':'phase1_a0_plan.log','a1_const':'phase1_a1_const.log','a0_think':'phase1_a0_think.log','think8k_probe':'phase1_think8k_probe.log','phase0_plan_think4k':'phase0_a0_plan_think.log'}
KEYS=['actor/lr','critic/score/mean','response_length/mean','response_length/max','response_length/min','response_length/clip_ratio','actor/entropy','actor/frac_adv_zero','actor/pg_loss','actor/kl_loss','actor/grad_norm','actor/pg_clipfrac','actor/ppo_kl','critic/advantages/max','critic/advantages/min']
out={'log':{}, 'roll':{}}
for tag,f in logs.items():
    p=f'{L}/{f}'; rows=[]
    if not os.path.exists(p): continue
    for line in open(p, errors='ignore'):
        m=re.search(r'step:(\d+) - (.*)', line)
        if not m: continue
        d={'step':int(m.group(1))}
        for kv in m.group(2).split(' - '):
            if ':' in kv:
                k,v=kv.rsplit(':',1)
                if k in KEYS:
                    try: d[k]=float(v)
                    except: pass
        rows.append(d)
    out['log'][tag]=rows
def comp(s): 
    b=s.encode(); return len(zlib.compress(b))/max(1,len(b))
def tail_rep(s, n=2000):
    t=s[-n:]; lines=[l for l in t.split('\n') if l.strip()]
    return 1-len(set(lines))/max(1,len(lines))
for tag,d in runs.items():
    rows=[]; ex={}
    for step in range(1,201):
        f=f'{R}/{d}/rollouts/{step}.jsonl'
        if not os.path.exists(f): continue
        rs=[json.loads(l) for l in open(f)]; n=len(rs)
        think='<think>' in rs[0]['output']
        closed=[r for r in rs if '</think>' in r['output']] if think else rs
        unc=[r for r in rs if '</think>' not in r['output']] if think else []
        groups=defaultdict(list)
        for r in rs: groups[r['id']].append(r)
        gk={'all_zero':0,'all_max':0,'mixed':0,'all_trunc':0}
        for g in groups.values():
            sc=[r['score'] for r in g]
            if max(sc)==min(sc): gk['all_zero' if max(sc)==0 else 'all_max']+=1
            else: gk['mixed']+=1
            if think and all('</think>' not in r['output'] for r in g): gk['all_trunc']+=1
        rec={'step':step,'n':n,'loose':sum(bool(r['is_reward_hack_loose']) for r in rs),'strict':sum(bool(r['is_reward_hack_strict']) for r in rs),
             'correct':sum(bool(r['eq_correct']) for r in rs),'hinted':sum(bool(r['eq_hinted']) for r in rs),'score_mean':st.mean(r['score'] for r in rs),
             'chars_med':int(st.median(len(r['output']) for r in rs)),'groups':gk}
        if think:
            rec['closed']=len(closed); rec['closed_frac']=len(closed)/n
            rec['closed_correct']=sum(bool(r['eq_correct']) for r in closed)
            rec['think_chars_med_closed']=int(st.median(len(r['output'].split('</think>')[0]) for r in closed)) if closed else None
            cc=[len(r['output'].split('</think>')[0]) for r in closed if r['eq_correct']]; ci=[len(r['output'].split('</think>')[0]) for r in closed if not r['eq_correct']]
            rec['think_chars_closed_correct_med']=int(st.median(cc)) if cc else None; rec['think_chars_closed_incorrect_med']=int(st.median(ci)) if ci else None
            rec['unc_compress']=round(st.mean(comp(r['output'][-4000:]) for r in unc),3) if unc else None
            rec['unc_tail_rep']=round(st.mean(tail_rep(r['output']) for r in unc),3) if unc else None
            rec['closed_compress']=round(st.mean(comp(r['output'][-4000:]) for r in closed),3) if closed else None
            if step in (1,10,20,30,40,50,60,80,100) and unc:
                ex[step]={'unc_head':unc[0]['output'][:600],'unc_tail':unc[0]['output'][-900:],'closed_tail':(closed[0]['output'][-700:] if closed else None)}
        rows.append(rec)
    out['roll'][tag]=rows; out.setdefault('examples',{})[tag]=ex
json.dump(out, open(os.environ['S']+'/analysis.json','w'), indent=1)
# print compact summaries
for tag in ['a0_think']:
    print('== rollouts',tag)
    for r in out['roll'][tag]:
        if r['step'] in (1,2,3,5,8,10,12,15,20,25,30,40,50,60,70,80,90,100):
            print(r['step'],'closed%.0f'%(100*r['closed_frac']),'corr',r['correct'],'cc',r['closed_correct'],'score%.2f'%r['score_mean'],'chars',r['chars_med'],'thinkC',r['think_chars_closed_correct_med'],'thinkI',r['think_chars_closed_incorrect_med'],'uncComp',r['unc_compress'],'uncRep',r['unc_tail_rep'],'clComp',r['closed_compress'],r['groups'])
    print('== log',tag)
    for d in out['log'][tag]:
        if d['step'] in (1,2,3,5,8,10,12,15,20,25,30,40,50,60,70,80,90,100):
            print(d['step'],'lr%.1e'%d.get('actor/lr',0),'score%.2f'%d.get('critic/score/mean',0),'len%.0f'%d.get('response_length/mean',0),'min%.0f'%d.get('response_length/min',0),'clip%.2f'%d.get('response_length/clip_ratio',0),'ent%.3f'%d.get('actor/entropy',0),'adv0 %.2f'%d.get('actor/frac_adv_zero',0),'pg%.4f'%d.get('actor/pg_loss',0),'kl%.4f'%d.get('actor/kl_loss',0),'gn%.3f'%d.get('actor/grad_norm',0),'clipfrac%.3f'%d.get('actor/pg_clipfrac',0))
for tag in ['think8k_probe','phase0_plan_think4k']:
    print('==',tag,[(d['step'],round(d.get('response_length/mean',0)),d.get('response_length/clip_ratio'),d.get('critic/score/mean')) for d in out['log'][tag]])
print('== probe plan_think rollouts', [(r['step'],r['closed_frac'],r['correct']) for r in out['roll']['a0_plan_think_probe']])
for tag in ['a0_noplan','a0_plan','a1_const']:
    print('==',tag,[(r['step'],r['loose'],r['correct'],round(r['score_mean'],2),r['chars_med']) for r in out['roll'][tag] if r['step'] in (1,25,50,75,100,125,150,175,200)])
    print('   log',[(d['step'],round(d.get('response_length/mean',0)),round(d.get('actor/entropy',0),3)) for d in out['log'][tag] if d['step'] in (1,50,100,150,200)])
