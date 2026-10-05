import subprocess,itertools,re,os
tmpl="""* fit
.model q1m npn(is={is1} bf={bf1} vaf=100 rb=20 rc=2 re=0 ikf=0.05 cje=5p cjc=3p tf=0.5n tr=50n)
.model q2m npn(is={is2} bf={bf2} vaf=100 rb=3 rc={rc2} re={re2} ikf=0.5 cje=20p cjc=10p tf=1n tr=100n)
Q1 c b1 b2 q1m
Q2 c b2 0 q2m
R3k b2 0 3k
Ib 0 b1 dc {ib}
Vc vcc 0 5
Ic vcc c dc {ic}
.control
op
echo RESULT $&v(c)
.endc
.end
"""
pts=[(0.1,250e-6,0.99),(0.2,350e-6,1.15),(0.35,500e-6,1.40)]
def run(p):
    err=0;out=[]
    for ic,ib,t in pts:
        open('/tmp/claude-0/x/fit.cir','w').write(tmpl.format(ic=ic,ib=ib,**p))
        r=subprocess.run(['ngspice','-b','/tmp/claude-0/x/fit.cir'],capture_output=True,text=True).stdout
        m=re.search(r'RESULT ([-\d.e+]+)',r)
        v=float(m.group(1)) if m else 9
        out.append(v); err+=(v-t)**2
    return err,out
best=None
for is1,is2,bf1,bf2,rc2,re2 in itertools.product([1e-14,1e-13],[1e-13,1e-12,1e-11],[50,150],[30,100],[0.3,1.0],[0.5,1.0,1.5]):
    p=dict(is1=is1,is2=is2,bf1=bf1,bf2=bf2,rc2=rc2,re2=re2)
    e,o=run(p)
    if best is None or e<best[0]: best=(e,p,o); print(best,flush=True)
