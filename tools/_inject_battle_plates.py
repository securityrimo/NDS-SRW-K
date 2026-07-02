# -*- coding: utf-8 -*-
"""_inject_battle_plates.py — translate add02 battle ability/status label ATLAS
plates (2205/2207/2209/2211) to Korean. Each plate is a tile atlas: PAT blocks
(2206/2208/2210/2212) compose labels from tile-column pieces. We translate each
visible word IN PLACE within its original tile-column span, so the PAT tile
references stay valid and compose Korean. Style = nib0 transparent, nib1 outline,
per-row gradient fill (derived from the plate itself). Re-encode with build_ecd2,
fit in original compressed size. Updates kr/add02_patched.bin.
Run with --verify to also emit before/after comparison montages."""
import struct, io, sys, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from srwk_rom import Rom
from _codec1024 import decomp_1024
from _enc1024b import build_ecd2
from PIL import Image, ImageFont, ImageDraw
import numpy as np

FONT = r"C:\Windows\Fonts\malgunbd.ttf"

# ── span tables: (band, col0, col1, korean). col = tile column (8px). Read from
#    ruler renders; each word occupies [col0,col1) tiles of its 16px band. ──
PLATES = {
 2205: [
   (0,0,8,'카운터'),(0,8,15,'합체공격'),(0,15,22,'원호공격'),(0,22,29,'원호방어'),
   (1,0,9,'크리티컬'),(1,9,15,'실드'),(1,15,32,'안티빔실드'),
   (2,0,10,'빔실드'),
 ],
 2207: [
   (0,0,3,'HIT'),(0,3,7,'회피'),(0,7,13,'쳐내기'),(0,13,20,'격추'),(0,20,24,'분신'),(0,24,32,'레이스아르카나'),
   (1,0,8,'오르곤클라우드'),(1,8,17,'미라지콜로이드'),(1,17,32,'일루전프로텍트'),
   (2,0,8,'스텔스장치'),(2,8,16,'오버스킬'),(2,16,20,'가속'),(2,20,25,'초가속'),(2,25,32,'시간정지'),
   (3,0,5,'투명화'),(3,5,9,'변형'),(3,9,13,'절도'),(3,13,17,'동화'),
 ],
 2209: [
   (0,0,8,'레이스아르카나'),(0,8,15,'오르곤클라우드'),(0,15,22,'빔코트'),(0,22,30,'라미네이트장갑'),(0,30,32,'크리'),
   (1,0,6,'야타노카가미'),(1,6,15,'전자실드'),(1,15,20,'확산망토'),(1,20,26,'PS장갑'),(1,26,32,'배리어'),
   (2,0,4,'양전자'),(2,4,11,'리플렉터'),(2,11,18,'보와튀르'),(2,18,24,'뤼미에르'),(2,24,32,'포톤매트'),
   (3,0,6,'이지스장비'),(3,6,13,'노른시스템'),(3,13,20,'바이오장갑'),(3,20,32,'플레어실드'),
   (4,0,9,'엔젤월'),(4,9,17,'엘도라블록'),(4,17,26,'가디언커튼'),(4,26,32,'VP하트'),
 ],
 2211: [
   (0,0,5,'조준치'),(0,5,10,'운동성'),(0,10,15,'장갑치'),(0,15,20,'이동력'),(0,20,25,'공격력'),(0,25,29,'사정'),(0,29,32,'SP'),
   (1,0,4,'기력'),(1,4,6,'EN'),(1,6,16,'특수효과무효'),(1,16,19,'다운'),(1,19,23,'흡수'),(1,23,25,'L1'),(1,25,27,'L2'),(1,27,29,'L3'),
 ],
}

rom_kr = Rom('../Super Robot Wars K (Korean)-NEW.nds')  # for verify (original JP-look plates)
base = open('kr/add02_patched.bin','rb').read()
d = bytearray(base)
n0 = struct.unpack_from('<I', d, 0)[0]; ne = n0//4
offs = list(struct.unpack_from('<%dI'%ne, d, 0)) + [len(d)]

def dec_block(buf, bi, o):
    raw = bytes(buf[o[bi]:o[bi+1]])
    return decomp_1024(raw)[0] if raw[:4]==b'ECD\x01' else raw

def to_grid(r):
    w,h = struct.unpack_from('<HH', r, 4); tile=r[8:]
    g = np.zeros((h*8,w*8), np.uint8)
    for ty in range(h):
        for tx in range(w):
            off=(ty*w+tx)*32
            for yy in range(8):
                for xx in range(8):
                    b=tile[off+yy*4+xx//2]; g[ty*8+yy,tx*8+xx]=(b&0xF) if (xx&1)==0 else (b>>4)
    return g,w,h

def derive_rowfill(g):
    H=g.shape[0]; rf=[]
    for y in range(H):
        cnt=collections.Counter(int(v) for v in g[y] if v not in (0,1))
        rf.append(cnt.most_common(1)[0][0] if cnt else 15)
    return rf

def render_word(ko, bw, rowfill16):
    """Render ko into a 16 x bw nibble grid, left-aligned, outline nib1 + gradient."""
    H=16
    dd=ImageDraw.Draw(Image.new('L',(1,1))); f=None
    for s in range(13,7,-1):   # cap at 13px for uniform look across labels
        ff=ImageFont.truetype(FONT,s); bb=dd.textbbox((0,0),ko,font=ff)
        if bb[2]-bb[0]<=bw-2 and bb[3]-bb[1]<=H-1: f=ff; break
    if f is None: f=ImageFont.truetype(FONT,8)
    mask=Image.new('L',(bw,H),0); dr=ImageDraw.Draw(mask)
    bb=dr.textbbox((0,0),ko,font=f); th=bb[3]-bb[1]
    dr.text((1,max(0,(H-th)//2)-bb[1]),ko,fill=255,font=f)
    mp=mask.load()
    fill=[[mp[x,y]>=110 for x in range(bw)] for y in range(H)]
    grid=[[0]*bw for _ in range(H)]
    for y in range(H):
        for x in range(bw):
            if fill[y][x]: continue
            if any(0<=y+dy<H and 0<=x+dx<bw and fill[y+dy][x+dx] for dy in(-1,0,1) for dx in(-1,0,1)):
                grid[y][x]=1
    for y in range(H):
        for x in range(bw):
            if fill[y][x]: grid[y][x]=rowfill16[y]
    return grid

def grid_to_tiles(grid,w,h):
    out=bytearray()
    for ty in range(h):
        for tx in range(w):
            for yy in range(8):
                for xx in range(0,8,2):
                    out.append((grid[ty*8+yy][tx*8+xx]&0xF)|((grid[ty*8+yy][tx*8+xx+1]&0xF)<<4))
    return bytes(out)

def show(g,scale=3):
    im=Image.fromarray(np.clip(g.astype(int)*17,0,255).astype(np.uint8),'L').convert('RGB')
    return im.resize((g.shape[1]*scale,g.shape[0]*scale),Image.NEAREST)

verify = '--verify' in sys.argv
comps=[]
ok=0; fails=[]
for bi, spans in PLATES.items():
    orig = bytes(d[offs[bi]:offs[bi+1]])
    r = dec_block(d, bi, offs)
    g_old,w,h = to_grid(r)
    rowfill = derive_rowfill(g_old)
    ng = np.zeros((h*8,w*8), np.uint8)   # start blank (transparent)
    for band,c0,c1,ko in spans:
        y0=band*16; bw=(c1-c0)*8
        wg = render_word(ko, bw, rowfill[y0:y0+16])
        for yy in range(16):
            for xx in range(bw):
                ng[y0+yy, c0*8+xx] = wg[yy][xx]
    tiles = grid_to_tiles(ng.tolist(), w, h)
    new = build_ecd2(orig, tiles, new_preamble=b'IMG\x00'+struct.pack('<HH',w,h))
    if len(new) > len(orig):
        fails.append((bi,len(new),len(orig))); continue
    d[offs[bi]:offs[bi+1]] = new + b'\x00'*(len(orig)-len(new))
    ok+=1
    if verify:
        a=show(g_old); b=show(ng)
        C=Image.new('RGB',(max(a.width,b.width), a.height+b.height+24),(15,15,20)); dr=ImageDraw.Draw(C)
        dr.text((2,0),f'a2:{bi} JP (before)',fill=(255,200,80)); C.paste(a,(0,12))
        dr.text((2,a.height+14),f'a2:{bi} KR (after)',fill=(120,255,120)); C.paste(b,(0,a.height+24))
        comps.append(C)

print(f'battle-plates injected {ok}/{len(PLATES)}')
for bi,nl,ol in fails: print(f'  OVERFLOW blk{bi}: compressed {nl}>{ol}')
assert len(bytes(d))==len(base), 'size changed!'

if verify and comps:
    tot_h=sum(c.height for c in comps)+len(comps)*8; W=max(c.width for c in comps)
    M=Image.new('RGB',(W,tot_h),(0,0,0)); y=0
    for c in comps: M.paste(c,(0,y)); y+=c.height+8
    M.save('_verify/plates_compare.png'); print('saved _verify/plates_compare.png')

if '--write' in sys.argv:
    open('kr/add02_patched.bin','wb').write(bytes(d))
    print('WROTE kr/add02_patched.bin')
else:
    print('(dry run — pass --write to save)')
