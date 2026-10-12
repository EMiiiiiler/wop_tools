#!/usr/bin/env python3
"""Self-contained turntable viewer for one MD3 (parsed in the browser from the real file bytes).

    python3 md3view.py model.md3 <texture.jpg | texture dir> out.html [--three three.min.js | --threeurl URL] [--title T] [--ground tex.jpg]

Drag to orbit, pinch / wheel to zoom. Lighting: warm key light + sky fill, like a sunny WoP room.
Screenshot it with shoot-style playwright code or open it on a phone.
"""
import argparse, base64, os

PAGE = r'''<meta charset="utf-8"><title>__TITLE__</title>
<style>
:root{--bg:#f3efe6;--fg:#2b2a33;--muted:#6d6a75;--card:#fffdf8;--line:#ddd6c8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#1d1c22;--fg:#efece6;--muted:#a9a5b1;--card:#26252c;--line:#3a3842;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#1d1c22;--fg:#efece6;--muted:#a9a5b1;--card:#26252c;--line:#3a3842;color-scheme:dark}
html,body{height:100%}body{background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;display:flex;flex-direction:column}
header{padding:14px 16px 6px}h1{margin:0;font-size:1.15rem;text-wrap:balance}p{margin:2px 0 0;color:var(--muted);font-size:.86rem}
#c{flex:1;min-height:0;width:100%;touch-action:none;display:block}
footer{padding:6px 16px 12px;color:var(--muted);font-size:.8rem;font-variant-numeric:tabular-nums}
</style>
<header><h1>__TITLE__</h1><p>__SUB__</p></header>
<canvas id="c"></canvas>
<footer id="info"></footer>
__THREE__
<script>
const MD3="__MD3__", TEX=__TEX__, GROUND="__GROUND__";   // TEX: {shader basename or "*": data uri}
function b64(s){const b=atob(s),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return u.buffer}
function parseMD3(buf){
  const dv=new DataView(buf); const nsurf=dv.getInt32(84,true), ofsSurf=dv.getInt32(100,true); let o=ofsSurf; const out=[];
  for(let s=0;s<nsurf;s++){
    let sh='';{const oSh=dv.getInt32(o+92,true);for(let k=0;k<64;k++){const c=dv.getUint8(o+oSh+k);if(!c)break;sh+=String.fromCharCode(c)}}
    const nv=dv.getInt32(o+80,true), nt=dv.getInt32(o+84,true), oT=dv.getInt32(o+88,true), oST=dv.getInt32(o+96,true), oX=dv.getInt32(o+100,true), oE=dv.getInt32(o+104,true);
    const pos=new Float32Array(nv*3), nor=new Float32Array(nv*3), uv=new Float32Array(nv*2), idx=new Uint32Array(nt*3);
    for(let i=0;i<nv;i++){const p=o+oX+i*8;
      // Q3 x,y,z (z up) -> three x,z,-y (y up)
      const x=dv.getInt16(p,true)/64,y=dv.getInt16(p+2,true)/64,z=dv.getInt16(p+4,true)/64, n=dv.getInt16(p+6,true);
      const lat=((n>>8)&255)*2*Math.PI/255, lng=(n&255)*2*Math.PI/255;
      const nx=Math.cos(lat)*Math.sin(lng), ny=Math.sin(lat)*Math.sin(lng), nz=Math.cos(lng);
      pos.set([x,z,-y],i*3); nor.set([nx,nz,-ny],i*3);
      uv[i*2]=dv.getFloat32(o+oST+i*8,true); uv[i*2+1]=dv.getFloat32(o+oST+i*8+4,true);}
    for(let i=0;i<nt;i++){const p=o+oT+i*12; idx[i*3]=dv.getInt32(p,true); idx[i*3+1]=dv.getInt32(p+4,true); idx[i*3+2]=dv.getInt32(p+8,true);}
    out.push({pos,nor,uv,idx,nv,nt,sh}); o+=oE;}
  return out;
}
const cv=document.getElementById('c');
const R=new THREE.WebGLRenderer({canvas:cv,antialias:true,preserveDrawingBuffer:true}); R.setPixelRatio(Math.min(2,devicePixelRatio));
R.outputColorSpace=THREE.SRGBColorSpace; R.shadowMap.enabled=true; R.shadowMap.type=THREE.PCFSoftShadowMap;
const S=new THREE.Scene(); S.background=new THREE.Color(getComputedStyle(document.documentElement).getPropertyValue('--bg').trim()||'#f3efe6');
const cam=new THREE.PerspectiveCamera(40,1,1,5000);
S.add(new THREE.HemisphereLight(0xdfeaff,0x8a6f55,0.9));
const sun=new THREE.DirectionalLight(0xfff1dc,2.2); sun.position.set(-260,420,220); sun.castShadow=true;
sun.shadow.mapSize.set(2048,2048); Object.assign(sun.shadow.camera,{left:-260,right:260,top:260,bottom:-260,near:10,far:1200}); sun.shadow.bias=-0.0008; S.add(sun);
const L=new THREE.TextureLoader(), texCache={};
function texFor(sh){const k=sh.split('/').pop(); const u=TEX[k]||TEX['*']; if(!u)return null; if(!texCache[u]){const t=L.load(u); t.colorSpace=THREE.SRGBColorSpace; t.flipY=false; t.anisotropy=8; t.wrapS=t.wrapT=THREE.RepeatWrapping; texCache[u]=t} return texCache[u]}
const surfs=parseMD3(b64(MD3)); let tv=0,tt=0, box=new THREE.Box3();
for(const s of surfs){const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.BufferAttribute(s.pos,3)); g.setAttribute('normal',new THREE.BufferAttribute(s.nor,3)); g.setAttribute('uv',new THREE.BufferAttribute(s.uv,2));
  // Quake winding is clockwise; flip to three's counter-clockwise front faces
  const ix=s.idx.slice(); for(let i=0;i<ix.length;i+=3){const t=ix[i+1];ix[i+1]=ix[i+2];ix[i+2]=t}
  g.setIndex(new THREE.BufferAttribute(ix,1));
  const m=new THREE.Mesh(g,new THREE.MeshStandardMaterial({map:texFor(s.sh),roughness:/chrome|red|brass|black/.test(s.sh)?0.38:0.95,metalness:0})); m.castShadow=true; m.receiveShadow=true; S.add(m);
  g.computeBoundingBox(); box.union(g.boundingBox); tv+=s.nv; tt+=s.nt;}
if(GROUND){const gt=L.load(GROUND); gt.colorSpace=THREE.SRGBColorSpace; gt.wrapS=gt.wrapT=THREE.RepeatWrapping; gt.repeat.set(3,3);
  const gm=new THREE.Mesh(new THREE.PlaneGeometry(900,900),new THREE.MeshStandardMaterial({map:gt,roughness:1})); gm.rotation.x=-Math.PI/2; gm.receiveShadow=true; S.add(gm);}
const size=box.getSize(new THREE.Vector3()), ctr=box.getCenter(new THREE.Vector3());
document.getElementById('info').textContent=`${tv} verts · ${tt} tris · ${size.x.toFixed(0)} × ${size.z.toFixed(0)} × ${size.y.toFixed(0)} units`;
let yaw=0.75,pitch=0.42,dist=Math.max(size.x,size.z)*1.9,auto=true;
function place(){cam.position.set(ctr.x+dist*Math.cos(pitch)*Math.sin(yaw),ctr.y+dist*Math.sin(pitch),ctr.z+dist*Math.cos(pitch)*Math.cos(yaw)); cam.lookAt(ctr)}
function size2(){const w=cv.clientWidth,h=cv.clientHeight; R.setSize(w,h,false); cam.aspect=w/h; cam.updateProjectionMatrix()}
addEventListener('resize',size2); size2();
let drag=null,pts=new Map(),pinch0=0;
cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId);pts.set(e.pointerId,[e.clientX,e.clientY]);auto=false;drag=[e.clientX,e.clientY];
  if(pts.size===2){const [a,b]=[...pts.values()];pinch0=Math.hypot(a[0]-b[0],a[1]-b[1])}});
cv.addEventListener('pointermove',e=>{if(!pts.has(e.pointerId))return;pts.set(e.pointerId,[e.clientX,e.clientY]);
  if(pts.size===2){const [a,b]=[...pts.values()];const d=Math.hypot(a[0]-b[0],a[1]-b[1]);if(pinch0){dist*=pinch0/d;pinch0=d}return}
  yaw-=(e.clientX-drag[0])*0.008;pitch=Math.max(0.05,Math.min(1.45,pitch+(e.clientY-drag[1])*0.006));drag=[e.clientX,e.clientY]});
const up=e=>{pts.delete(e.pointerId);pinch0=0};cv.addEventListener('pointerup',up);cv.addEventListener('pointercancel',up);
cv.addEventListener('wheel',e=>{e.preventDefault();dist*=Math.exp(e.deltaY*0.001)},{passive:false});
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
window.__setView=(y,p,d)=>{auto=false;yaw=y;pitch=p;if(d)dist=d;place();R.render(S,cam)};
(function loop(){if(auto&&!reduce)yaw+=0.004;place();R.render(S,cam);requestAnimationFrame(loop)})();
</script>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md3'); ap.add_argument('tex'); ap.add_argument('out')
    ap.add_argument('--three'); ap.add_argument('--threeurl'); ap.add_argument('--title', default='MD3 model')
    ap.add_argument('--sub', default=''); ap.add_argument('--ground')
    a = ap.parse_args()
    def uri(p, mime):
        return f'data:{mime};base64,' + base64.b64encode(open(p, 'rb').read()).decode()
    mime = lambda p: 'image/png' if p.lower().endswith('.png') else 'image/jpeg'
    import json
    def texmap(t):
        if os.path.isdir(t):
            return json.dumps({os.path.splitext(f)[0]: uri(os.path.join(t, f), mime(f)) for f in sorted(os.listdir(t))
                               if f.lower().endswith(('.jpg', '.jpeg', '.png'))})
        return json.dumps({'*': uri(t, mime(t))})
    three = (f'<script src="{a.threeurl}"></script>' if a.threeurl else '<script>' + open(a.three).read() + '</script>')
    html = (PAGE.replace('__TITLE__', a.title).replace('__SUB__', a.sub).replace('__THREE__', three)
            .replace('__MD3__', base64.b64encode(open(a.md3, 'rb').read()).decode())
            .replace('__TEX__', texmap(a.tex)).replace('__GROUND__', uri(a.ground, mime(a.ground)) if a.ground else ''))
    open(a.out, 'w').write(html)
    print(a.out, round(len(html) / 1e6, 2), 'MB')


if __name__ == '__main__':
    main()
