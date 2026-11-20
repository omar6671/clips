import sys,subprocess,numpy as np
src=sys.argv[1]
p=subprocess.Popen(["ffmpeg","-v","error","-threads","2","-i",src,"-an","-vf","fps=2,crop=1080:640:2640:100,scale=270:160","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
# box in full res x2720-3650,y156-684 -> in crop (2640,100) scaled /4: x20-252, y14-146
fs=270*160*3; on=[]
def yel(a, axis):
    a=a.astype(int); r,g,b=a[...,0],a[...,1],a[...,2]; m=(r>150)&(g>130)&(b<120)&(r-b>60)
    return m.mean(axis=axis).max()
while True:
    b=p.stdout.read(fs)
    if len(b)<fs: break
    f=np.frombuffer(b,np.uint8).reshape(160,270,3)
    s=min(yel(f[12:18,30:240],1),yel(f[142:148,30:240],1),yel(f[25:135,18:24],0),yel(f[25:135,248:254],0))
    on.append(s>0.5)
np.save(sys.argv[2],np.array(on))
seg=[];st=None
for i,v in enumerate(on+[False]):
    if v and st is None: st=i
    if not v and st is not None: seg.append((st/2,i/2)); st=None
print("frames",len(on),"cam seconds",sum(b-a for a,b in seg))
for a,b in seg:
    if b-a>=3: print(f"{a:.1f}-{b:.1f} ({b-a:.0f}s)")
