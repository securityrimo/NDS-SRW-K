# -*- coding: utf-8 -*-
"""_inject_muteki.py — translate the 無敵 (invincible) battle cut-in kanji in
add04 block 9566 to 무적. The kanji are black brush strokes (nib<=2) composited
on a grayscale character collage. We inpaint the old strokes from the surrounding
illustration, then draw 무적 in the same nib1 ink over the same footprint.
Re-encode with build_ecd2. Writes kr/add04_patched.bin. --verify for comparison."""
import struct, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from srwk_rom import Rom
from _codec1024 import decomp_1024
from _enc1024b import build_ecd2
from PIL import Image, ImageFont, ImageDraw
import numpy as np

FONT = r"C:\Windows\Fonts\malgunbd.ttf"
# kanji footprint (from dark-stroke analysis): 無 x84-116, 敵 x120-156, y52-90
BOX = (82, 50, 158, 92)   # x0,y0,x1,y1 inpaint/redraw region
SLOTS = [(83, '무'), (119, '적')]   # x-start of each ~36px syllable
SYL_W, SYL_TOP, SYL_H = 38, 50, 42

base = open('kr/add04_patched.bin','rb').read() if __import__('os').path.exists('kr/add04_patched.bin') \
       else Rom('../Super Robot Wars K (Korean)-NEW.nds').get('data/add04dat.bin')
d = bytearray(base)
ne = struct.unpack_from('<I', d, 0)[0]//4
offs = list(struct.unpack_from('<%dI'%ne, d, 0)) + [len(d)]
orig = bytes(d[offs[9566]:offs[9567]])
r = decomp_1024(orig)[0]
w,h = struct.unpack_from('<HH', r, 4); tile=r[8:]
g = np.zeros((h*8,w*8), np.int16)
for ty in range(h):
    for tx in range(w):
        off=(ty*w+tx)*32
        for yy in range(8):
            for xx in range(8):
                b=tile[off+yy*4+xx//2]; g[ty*8+yy,tx*8+xx]=(b&0xF) if (xx&1)==0 else (b>>4)
g_old = g.copy()

# --- inpaint old kanji strokes (nib<=2) inside BOX ---
x0,y0,x1,y1 = BOX
mask = np.zeros(g.shape, bool)
mask[y0:y1, x0:x1] = (g[y0:y1, x0:x1] <= 2)
work = g.copy().astype(float); m = mask.copy()
for _ in range(200):
    if not m.any(): break
    ys,xs = np.where(m)
    filled=0
    newvals={}
    for y,x in zip(ys,xs):
        nb=[]
        for dy in(-1,0,1):
            for dx in(-1,0,1):
                ny,nx=y+dy,x+dx
                if 0<=ny<g.shape[0] and 0<=nx<g.shape[1] and not m[ny,nx]:
                    nb.append(work[ny,nx])
        if nb: newvals[(y,x)]=sum(nb)/len(nb)
    if not newvals: break
    for (y,x),v in newvals.items(): work[y,x]=v; m[y,x]=False
g = np.clip(np.round(work),1,15).astype(np.int16)

# --- render 무적 mask, draw over inpainted bg in nib1 (kanji ink) ---
def syl_mask(ko, W, H):
    dd=ImageDraw.Draw(Image.new('L',(1,1))); f=None
    for s in range(H, 20, -1):
        ff=ImageFont.truetype(FONT,s); bb=dd.textbbox((0,0),ko,font=ff)
        if bb[2]-bb[0]<=W-2 and bb[3]-bb[1]<=H-1: f=ff; break
    if f is None: f=ImageFont.truetype(FONT,H-4)
    im=Image.new('L',(W,H),0); dr=ImageDraw.Draw(im)
    bb=dr.textbbox((0,0),ko,font=f); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
    dr.text((max(0,(W-tw)//2)-bb[0], max(0,(H-th)//2)-bb[1]), ko, fill=255, font=f)
    return np.array(im)
for sx,ko in SLOTS:
    mk = syl_mask(ko, SYL_W, SYL_H)
    for yy in range(SYL_H):
        for xx in range(SYL_W):
            if mk[yy,xx]>=110:
                Y,X=SYL_TOP+yy, sx+xx
                if 0<=Y<g.shape[0] and 0<=X<g.shape[1]: g[Y,X]=1

# grid -> tiles
out=bytearray()
for ty in range(h):
    for tx in range(w):
        for yy in range(8):
            for xx in range(0,8,2):
                out.append((int(g[ty*8+yy,tx*8+xx])&0xF)|((int(g[ty*8+yy,tx*8+xx+1])&0xF)<<4))
new = build_ecd2(orig, bytes(out), new_preamble=b'IMG\x00'+struct.pack('<HH',w,h))
print(f"9566: new compressed {len(new)} vs orig {len(orig)}  {'OK' if len(new)<=len(orig) else 'OVERFLOW'}")

if '--verify' in sys.argv:
    def show(gg):
        im=Image.fromarray(np.clip(gg.astype(int)*17,0,255).astype(np.uint8),'L').convert('RGB')
        return im.resize((gg.shape[1]*3,gg.shape[0]*3),Image.NEAREST)
    a=show(g_old); b=show(g)
    C=Image.new('RGB',(a.width*2+8,a.height+16),(15,15,20)); dr=ImageDraw.Draw(C)
    dr.text((2,0),'before',fill=(255,200,80)); dr.text((a.width+10,0),'after',fill=(120,255,120))
    C.paste(a,(0,14)); C.paste(b,(a.width+8,14))
    C.save('_verify/muteki_compare.png'); print('saved _verify/muteki_compare.png')

import os
if '--write' in sys.argv and len(new)<=len(orig):
    d[offs[9566]:offs[9567]] = new + b'\x00'*(len(orig)-len(new))
    assert len(bytes(d))==len(base)
    open('kr/add04_patched.bin','wb').write(bytes(d))
    print('WROTE kr/add04_patched.bin')
else:
    print('(dry run — pass --write to save)')
