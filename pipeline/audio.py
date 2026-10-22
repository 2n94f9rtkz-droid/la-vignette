import json,sys,numpy as np,wave
ev=json.load(open(sys.argv[1]));out=sys.argv[2]
sr=44100;D=60;a=np.zeros(sr*D)
def add(t,s,g=1):
    i=int(t*sr);n=min(len(s),len(a)-i)
    if n>0:a[i:i+n]+=s[:n]*g
def tone(f,d,dec=30):
    t=np.arange(int(sr*d))/sr;return np.sin(2*np.pi*f*t)*np.exp(-t*dec)
rng=np.random.default_rng(1)
def pop():
    t=np.arange(int(sr*.09))/sr;f=900-3000*t;return np.sin(2*np.pi*np.cumsum(f)/sr)*np.exp(-t*45)
def tick(): return tone(1500,.08,60)*.9+tone(3000,.08,90)*.3
def whoosh():
    n=int(sr*.45);x=rng.standard_normal(n);env=np.sin(np.linspace(0,np.pi,n))**2
    return np.convolve(x,np.ones(40)/40,'same')*env*1.5
def reveal(): return sum(tone(f,.9,4)*g for f,g in [(523,.5),(659,.4),(784,.4),(1047,.3)])
S={'pop':pop(),'tick':tick(),'whoosh':whoosh(),'reveal':reveal()}
for t,k in ev: add(t,S[k],{'pop':.45,'tick':.6,'whoosh':.5,'reveal':.55}[k])
bt=60/100;tk=np.arange(int(sr*.35))/sr
kick=np.sin(2*np.pi*(50+90*np.exp(-tk*30))*tk)*np.exp(-tk*9)
th=np.arange(int(sr*.04))/sr;hat=rng.standard_normal(len(th))*np.exp(-th*120)
bass=[55,55,65.4,49];x=0.0;b=0
while x<57:
    if not any(s+10.6<=x<s+13.6 for s in [3,21,39]):
        add(x,kick,.35);add(x+bt/2,hat,.08)
        if b%4==0: add(x,tone(bass[(b//4)%4],bt*3.5,1.2),.18)
    x+=bt;b+=1
fade=np.ones_like(a);fade[-sr:]=np.linspace(1,0,sr);a*=fade;a=a/np.max(np.abs(a))*0.85
w=wave.open(out,'w');w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes((a*32767).astype(np.int16).tobytes());w.close()
