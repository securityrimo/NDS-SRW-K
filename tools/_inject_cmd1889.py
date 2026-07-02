# -*- coding: utf-8 -*-
"""_inject_cmd1889.py — partial-tile translate the 4 battle-command kanji
攻反防避 (attack/counter/defense/evade) in add02 block 1889 to 공/반/방/피.
Only the 4 kanji slots (rows 2-3, x88-152) are rewritten; all icons and Latin
button glyphs stay byte-identical. Re-encode with build_ecd2. Updates
kr/add02_patched.bin. Run with --write to save; --verify for a comparison img."""
import struct, io, sys, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from _codec1024 import decomp_1024
from _enc1024b import build_ecd2
from PIL import Image, ImageFont, ImageDraw
import numpy as np

FONT = r"C:\Windows\Fonts\malgunbd.ttf"
SLOTS = [(88,'공'),(104,'반'),(120,'방'),(136,'피')]  # x-start of each 16px slot
Y0, Y1 = 16, 32   # kanji band (tile rows 2-3)

base = open('kr/add02_patched.bin','rb').read()
d = bytearray(base)
ne = struct.unpack_from('<I', d, 0)[0]//4
offs = list(struct.unpack_from('<%dI'%ne, d, 0)) + [len(d)]
orig = bytes(d[offs[1889]:offs[1890]])
r = decomp_1024(orig)[0]
w,h = struct.unpack_from('<HH', r, 4); tile=r[8:]
g = np.zeros((h*8,w*8), np.uint8)
for ty in range(h):
    for tx in range(w):
        off=(ty*w+tx)*32
        for yy in range(8):
            for xx in range(8):
                b=tile[off+yy*4+xx//2]; g[ty*8+yy,tx*8+xx]=(b&0xF) if (xx&1)==0 else (b>>4)
g_old = g.copy()

# per-row fill nibble over the kanji region (x88..152), for a matching gradient
rf=[]
for y in range(Y0,Y1):
    cnt=collections.Counter(int(v) for v in g[y,88:152] if v>2)
    rf.append(cnt.most_common(1)[0][0] if cnt else 12)
OUT=3  # edge/outline nibble (low fill value used by the kanji anti-alias)

def render_syl(ko):
    dd=ImageDraw.Draw(Image.new('L',(1,1))); f=None
    for s in range(15,9,-1):
        ff=ImageFont.truetype(FONT,s); bb=dd.textbbox((0,0),ko,font=ff)
        if bb[2]-bb[0]<=15 and bb[3]-bb[1]<=15: f=ff; break
    if f is None: f=ImageFont.truetype(FONT,12)
    mask=Image.new('L',(16,16),0); dr=ImageDraw.Draw(mask)
    bb=dr.textbbox((0,0),ko,font=f); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
    dr.text((max(0,(16-tw)//2)-bb[0], max(0,(16-th)//2)-bb[1]), ko, fill=255, font=f)
    mp=mask.load()
    fill=[[mp[x,y]>=110 for x in range(16)] for y in range(16)]
    out=np.zeros((16,16),np.uint8)
    for y in range(16):
        for x in range(16):
            if fill[y][x]: continue
            if any(0<=y+dy<16 and 0<=x+dx<16 and fill[y+dy][x+dx] for dy in(-1,0,1) for dx in(-1,0,1)):
                out[y,x]=OUT
    for y in range(16):
        for x in range(16):
            if fill[y][x]: out[y,x]=rf[y]
    return out

# clear kanji region, place Korean syllables
g[Y0:Y1, 88:152] = 0
for x0,ko in SLOTS:
    g[Y0:Y1, x0:x0+16] = render_syl(ko)

# grid -> tiles
out=bytearray()
for ty in range(h):
    for tx in range(w):
        for yy in range(8):
            for xx in range(0,8,2):
                out.append((int(g[ty*8+yy,tx*8+xx])&0xF)|((int(g[ty*8+yy,tx*8+xx+1])&0xF)<<4))
new = build_ecd2(orig, bytes(out), new_preamble=b'IMG\x00'+struct.pack('<HH',w,h))
print(f"1889: new compressed {len(new)} vs orig {len(orig)}  {'OK' if len(new)<=len(orig) else 'OVERFLOW'}")

if '--verify' in sys.argv:
    def show(gg):
        im=Image.fromarray(np.clip(gg.astype(int)*17,0,255).astype(np.uint8),'L').convert('RGB')
        return im.resize((gg.shape[1]*4,gg.shape[0]*4),Image.NEAREST)
    a=show(g_old); b=show(g)
    C=Image.new('RGB',(a.width,a.height*2+24),(15,15,20)); dr=ImageDraw.Draw(C)
    dr.text((2,0),'a2:1889 before',fill=(255,200,80)); C.paste(a,(0,12))
    dr.text((2,a.height+14),'a2:1889 after',fill=(120,255,120)); C.paste(b,(0,a.height+24))
    C.save('_verify/cmd1889_compare.png'); print('saved _verify/cmd1889_compare.png')

if '--write' in sys.argv and len(new)<=len(orig):
    d[offs[1889]:offs[1890]] = new + b'\x00'*(len(orig)-len(new))
    assert len(bytes(d))==len(base)
    open('kr/add02_patched.bin','wb').write(bytes(d))
    print('WROTE kr/add02_patched.bin')
else:
    print('(dry run — pass --write to save)')
