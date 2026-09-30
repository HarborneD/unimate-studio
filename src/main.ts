import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import './style.css';

type Rig = { id: string; name: string; joints: number; parents: number[]; rest: number[][]; description: string };
type Request = { prompt: string; rig: string; seed: number; guidance: number; quality: string };
type Job = { id: string; status: string; request: Request; message: string; progress: number; seconds?: number; frames?: number };
type Motion = { fps: number; frames: number; parents: number[]; positions: number[][][]; request: Request; seconds: number; provenance: {device:string; solver:string} };
type Health = { status: string; message: string; device: string | null; rigs: Rig[] };

const paths: Record<string, string> = {
  logo: '<path d="M4 6v8a8 8 0 0 0 16 0V6M12 3v9"/>',
  spark: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/>',
  github: '<path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.9a3.4 3.4 0 0 0-.9-2.7c3-.4 6.2-1.5 6.2-7A5.4 5.4 0 0 0 19.8 5a5 5 0 0 0-.1-3.5s-1.2-.4-3.8 1.4a13 13 0 0 0-7 0C6.3 1.1 5.1 1.5 5.1 1.5A5 5 0 0 0 5 5a5.4 5.4 0 0 0-1.5 3.7c0 5.5 3.2 6.6 6.2 7a3.4 3.4 0 0 0-.9 2.7V22"/>',
  human: '<circle cx="12" cy="4" r="2"/><path d="M12 6v8M5 10l7-2 7 2M12 14l-4 7m4-7 4 7"/>',
  quadruped: '<path d="M4 10h12l3-5 3 5-3 3h-3M4 10l-2-4m2 4v10m12-10v10M7 12v8m6-8v8"/>',
  avian: '<path d="M12 8v10m0-10L2 4l4 9 6-1 6 1 4-9-10 4Zm0 10-3 3m3-3 3 3"/><circle cx="12" cy="5" r="2"/>',
  cube: '<path d="m12 2 9 5v10l-9 5-9-5V7l9-5Zm0 20V12m9-5-9 5-9-5m4.5-7.5 9 5"/>',
  reset: '<path d="M3 11a9 9 0 1 1 2 7M3 4v7h7"/>',
  grid: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18m6-18v18"/>',
  expand: '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/>',
  play: '<path d="m8 4 12 8-12 8V4Z" fill="currentColor" stroke="none"/>',
  pause: '<path d="M8 5v14M16 5v14" stroke-width="3"/>',
  back: '<path d="M5 5v14m14-14L7 12l12 7V5Z"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  orbit: '<ellipse cx="12" cy="12" rx="10" ry="5" transform="rotate(-30 12 12)"/><circle cx="12" cy="12" r="2"/>',
  mouse: '<rect x="6" y="2" width="12" height="20" rx="6"/><path d="M12 2v7"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-11v1"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
};
function icon(name: string) { return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.human}</svg>`; }

document.querySelector<HTMLDivElement>('#app')!.innerHTML = `
<header><div class="brand"><span class="logo">${icon('logo')}</span><span>UniMate <em>Studio</em></span><span class="badge">OPEN SOURCE</span></div><div class="header-right"><span class="host-label"><span id="status-dot" class="status-dot"></span> <span id="host-status">Connecting to model</span></span><button class="icon" id="about" title="About & credits" aria-label="About and credits">${icon('info')}</button><a href="https://github.com/HarborneD/unimate-studio" target="_blank" rel="noopener">${icon('github')} Source code</a></div></header>
<div class="intro"><div><div class="eyebrow">THE ANIMATION WORKBENCH</div><h1>A few words. A new motion.</h1><p>Describe an action. Bring a skeleton to life.</p></div><div class="note">${icon('cube')} One model. Different skeletons.</div></div>
<main class="workspace">
 <aside class="sidebar">
  <section><div class="section-top"><h2>Choose your skeleton</h2><span class="step">01</span></div><div class="rigs" id="rigs"><span class="loading-notice">Preparing available rigs...</span></div><div class="rig-detail" id="rig-detail"><span></span> Skeleton conditioning</div></section>
  <section><div class="section-top"><h2>Describe the motion</h2><span class="step">02</span></div><div class="prompt-box"><textarea id="prompt" maxlength="400" aria-label="Motion description" spellcheck="false">An object walks forward at a relaxed, steady pace.</textarea><div class="prompt-foot"><span>ENGLISH MOTION DESCRIPTION</span><span id="char-count">49 / 400</span></div></div><div class="examples" id="examples"></div></section>
  <section><div class="section-top"><h2>Make it your own</h2><span class="step">03</span></div><div class="field-row"><div class="field"><label for="seed">Seed</label><input id="seed" type="number" min="0" max="2147483647" value="42" step="1"></div><div class="field"><label for="quality">Quality</label><select id="quality"><option value="preview">Preview · 30 steps</option><option value="standard">Standard · adaptive</option></select></div></div><div><div class="guidance-head"><label for="guidance">Prompt guidance</label><output id="guidance-value">3.0</output></div><input type="range" id="guidance" min="1.1" max="8" value="3" step="0.1"><div class="range-caption"><span>More freedom</span><span>Follow the prompt</span></div></div></section>
  <div><button class="generate" id="generate" disabled>${icon('spark')} <span>Generate animation</span></button><div class="generate-sub">60 frames <span>·</span> 2 seconds <span>·</span> UniMate v2</div><div id="loading-notice" class="loading-notice">Starting inference host...</div></div>
  <div class="sidebar-bottom">Powered by <a href="https://github.com/Friedrich-M/UniMate" target="_blank" rel="noopener">UniMate</a>, an open-source model for animating diverse skeletons.</div>
 </aside>
 <section class="viewport-area" aria-label="Animation viewer">
  <div class="viewport-head"><div class="viewport-label">${icon('cube')} <span>Motion preview</span> <span class="badge" id="motion-badge">REST POSE</span></div><div class="viewport-actions"><button id="toggle-grid" class="active" title="Toggle ground grid" aria-label="Toggle ground grid" aria-pressed="true">${icon('grid')}</button><button id="reset-camera" title="Reset camera" aria-label="Reset camera">${icon('reset')}</button><button id="fullscreen" title="Fullscreen viewer" aria-label="Fullscreen viewer">${icon('expand')}</button></div></div>
  <div class="stage" id="stage"><div class="stage-topleft" id="stage-info">PREPARING RIG<br>REST POSE / SKELETON VIEW</div><div class="stage-topright">PERSPECTIVE<br>Y UP</div><div class="empty-label" id="empty-label">Your next motion starts with a prompt.</div><div class="stage-help"><span>${icon('orbit')} Drag to orbit</span><span>${icon('mouse')} Scroll or pinch to zoom</span></div><div class="orientation">Y<br> &nbsp; X — Z</div><div class="generating" id="generating" hidden><div class="spinner"></div><strong id="progress-label">Generating motion</strong><small id="elapsed">0s elapsed</small><div class="progress"><div id="progress-bar"></div></div></div></div>
  <div class="playback"><div class="playback-top"><div class="playback-buttons"><button class="transport" id="restart" title="First frame" aria-label="First frame">${icon('back')}</button><button class="play-btn" id="play" title="Play or pause (Space)" aria-label="Play animation" disabled>${icon('play')}</button><span class="time" id="time">0.00 / 2.00 s</span><select class="speed" id="speed" aria-label="Playback speed"><option value="0.5">0.5x</option><option value="1" selected>1x</option><option value="2">2x</option></select><button class="transport active" id="loop" title="Loop playback" aria-label="Loop playback" aria-pressed="true">${icon('reset')}</button></div><div class="export-wrap"><button class="outline" id="export" disabled>${icon('download')} Export ${icon('chevron')}</button><div class="export-menu" id="export-menu" hidden><a id="bvh-link">BVH animation <small>.bvh</small></a><a id="json-link">Motion + provenance <small>.json</small></a><a id="npy-link">UniMate features <small>.npy</small></a></div></div></div><div class="timeline"><input type="range" id="scrub" min="0" max="59" step="1" value="0" aria-label="Animation frame" disabled><div class="ticks"><span>0</span><span>15</span><span>30</span><span>45</span><span>60 frames</span></div></div></div>
 </section>
</main>
<div class="toast" id="toast" role="alert" hidden><span id="toast-text"></span><button id="dismiss-error" aria-label="Dismiss error">${icon('close')}</button></div>
<section class="takes"><div class="takes-top"><h2>Your takes <span id="take-count">00</span></h2><p>Generated on this host · choose a take to revisit it</p></div><div class="take-list" id="take-list"><div class="takes-empty">A little direction goes a long way. Generate your first take above.</div></div></section>
<footer class="footer"><span>UniMate Studio <span style="opacity:.5">/</span> An open-source animation experiment</span><span>Built with <a href="https://github.com/Friedrich-M/UniMate" target="_blank" rel="noopener">UniMate</a> <span style="opacity:.5">·</span> <a href="#" id="credits-link">MIT license & credits</a></span></footer>
<dialog class="credits" id="credits"><button class="icon" id="close-credits" aria-label="Close credits">${icon('close')}</button><div class="eyebrow">OPEN RESEARCH, OPEN TOOLS</div><h2>Motion for every kind of skeleton.</h2><p>This workbench runs the released <a href="https://huggingface.co/Linzhan/UniMate" target="_blank" rel="noopener">UniMate v2 model</a> with EMA weights. Prompt text is encoded with FLAN-T5; the model generates 60 frames at 30 fps. The viewer shows forward kinematics from the predicted rotations.</p><ul><li>UniMate: Linzhan Mou, Jiahui Lei, Zhiyang Dou, Chenyue Cai, Chaoyue Song, Adam Finkelstein and Szymon Rusinkiewicz. Code and checkpoints: MIT.</li><li>Three.js: MIT. Motion library: MIT. FLAN-T5: Apache 2.0.</li><li>Humanoid conditioning: Mixamo / Adobe source data, downloaded locally. Other rigs, when available, are original primitive demonstration skeletons.</li><li>UniMate Studio source: MIT.</li></ul><p>Model outputs are experimental: prompts may not be followed perfectly and clips can have foot sliding. Looped playback repeats the clip; it does not generate a seamless loop. BVH uses a canonical rig and does not retarget to a character mesh.</p><small>Inference runs on the connected Python host. Source animation packs are not bundled with this open-source tool. <a href="https://linzhanmou.com/unimate/" target="_blank" rel="noopener">Read the research</a>.</small></dialog>`;

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id)! as T;
const prompt = $<HTMLTextAreaElement>('prompt');
let rigs: Rig[] = [], selectedRig = 'mixamo', motion: Motion | null = null, activeJob = '', jobs: Job[] = [];
let playing = false, looping = true, frame = 0, busy = false, healthReady = false;
const examples: Record<string, [string,string][]> = {
  mixamo: [['Walk','An object walks forward at a relaxed, steady pace.'],['Dance','An object dances energetically, moving its arms and legs.'],['Jump','An object jumps in place with both arms raised.'],['Wave','An object stands still and waves its right hand.']],
  quadruped: [['Walk','An object walks forward on four legs.'],['Run','An object runs forward at a fast pace.'],['Sit','An object sits down on its hind legs.']],
  avian: [['Flap','An object flaps its wings rhythmically.'],['Hop','An object hops forward with its wings spread.'],['Fly','An object flies forward, flapping both wings.']],
};

function error(message: string) { $('toast-text').textContent = message; $('toast').hidden = false; }
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data as T;
}
function counter() { $('char-count').textContent = `${prompt.value.length} / 400`; }
prompt.addEventListener('input', counter); counter();
$('dismiss-error').onclick = () => $('toast').hidden = true;
$<HTMLInputElement>('guidance').oninput = () => $('guidance-value').textContent = Number($<HTMLInputElement>('guidance').value).toFixed(1);
function updateGenerate() { $<HTMLButtonElement>('generate').disabled = busy || !healthReady; }

const stage = $('stage');
const scene = new THREE.Scene();
scene.background = new THREE.Color('#eaede3');
scene.fog = new THREE.Fog('#eaede3', 10, 24);
const camera = new THREE.PerspectiveCamera(34, 1, 0.01, 80);
const renderer = new THREE.WebGLRenderer({antialias:true,alpha:false});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.4;
stage.prepend(renderer.domElement);
const controls = new OrbitControls(camera,renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.minDistance = 1.2; controls.maxDistance = 13;
controls.maxPolarAngle = Math.PI/2 - 0.03;
scene.add(new THREE.HemisphereLight('#ffffff','#879775',2.7));
const sun = new THREE.DirectionalLight('#fffcf2',4);
sun.position.set(3,7,4); sun.castShadow=true;
sun.shadow.mapSize.set(1024,1024); sun.shadow.camera.left=-5;sun.shadow.camera.right=5;sun.shadow.camera.top=5;sun.shadow.camera.bottom=-5;sun.shadow.bias=-0.0003;
scene.add(sun);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(200,200), new THREE.MeshStandardMaterial({color:'#e9eddf',roughness:1}));
floor.rotation.x=-Math.PI/2;floor.position.y=-0.012;floor.receiveShadow=true;scene.add(floor);
const grid = new THREE.GridHelper(200,400,'#cdd6c0','#d6deca');
(grid.material as THREE.Material).transparent=true;(grid.material as THREE.Material).opacity=.55;scene.add(grid);
const group = new THREE.Group();scene.add(group);
const boneMaterial = new THREE.MeshStandardMaterial({color:'#718a54',roughness:.5,metalness:.08});
const jointMaterial = new THREE.MeshStandardMaterial({color:'#b3c991',roughness:.48});
const rootMaterial = new THREE.MeshStandardMaterial({color:'#505e40',roughness:.7});
const boneGeometry = new THREE.CylinderGeometry(0.022,0.027,1,8);
const jointGeometry = new THREE.SphereGeometry(0.035,12,8);
let bones: THREE.Mesh[] = [], joints: THREE.Mesh[] = [], parents: number[] = [], rest: number[][] = [];
const up = new THREE.Vector3(0,1,0), a = new THREE.Vector3(), b = new THREE.Vector3(), direction = new THREE.Vector3();
function setSkeleton(p: number[], positions: number[][]) {
  group.clear(); parents=p;rest=positions;
  bones=[];joints=[];
  for(let i=0;i<p.length;i++) {
    const sphere=new THREE.Mesh(jointGeometry,i===0?rootMaterial:jointMaterial);sphere.castShadow=true;group.add(sphere);joints.push(sphere);
    const bone=new THREE.Mesh(boneGeometry,boneMaterial);bone.castShadow=true;group.add(bone);bones.push(bone);
  }
  drawPose(positions); resetCamera(positions);
}
function drawPose(positions: number[][]) {
  positions.forEach((pos,i)=>{
    if(!joints[i]) return;
    a.fromArray(pos);joints[i].position.copy(a);
    const parent=parents[i];
    if(parent<0||parent===i){bones[i].visible=false;return;}
    bones[i].visible=true;b.fromArray(positions[parent]);
    direction.copy(a).sub(b);const length=direction.length();
    bones[i].position.copy(a).add(b).multiplyScalar(.5);
    bones[i].scale.set(1,length,1);bones[i].quaternion.setFromUnitVectors(up,direction.normalize());
  });
}
function resetCamera(positions = motion?.positions[0] || rest) {
  if(!positions.length)return;
  const box=new THREE.Box3().setFromPoints(positions.map(p=>new THREE.Vector3(...p as [number,number,number])));
  const center=box.getCenter(new THREE.Vector3()), size=box.getSize(new THREE.Vector3());
  const extent=Math.max(size.y,size.x,size.z,1.5);
  controls.target.set(center.x,center.y,center.z);
  camera.position.set(center.x+extent*1.9,center.y+extent*1.05,center.z+extent*2.8);
  controls.update();
}
new ResizeObserver(()=>{ const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix(); }).observe(stage);
$('toggle-grid').onclick=()=>{grid.visible=!grid.visible;$('toggle-grid').classList.toggle('active',grid.visible);$('toggle-grid').setAttribute('aria-pressed',String(grid.visible));};
$('reset-camera').onclick=()=>resetCamera();
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('stage').requestFullscreen();}catch{error('Fullscreen is unavailable in this browser.');}};
// Show an authored neutral skeleton while the real host prepares its rigs.
// It is labelled REST POSE; generated animation always comes from the API.
setSkeleton([-1,0,1,2,3,3,5,6,3,8,9,0,11,12,0,14,15],[[0,.93,0],[0,1.1,0],[0,1.25,0],[0,1.4,0],[0,1.63,0],[-.16,1.4,0],[-.42,1.3,0],[-.63,1.2,0],[.16,1.4,0],[.42,1.3,0],[.63,1.2,0],[-.11,.85,0],[-.11,.43,0],[-.11,.06,.1],[.11,.85,0],[.11,.43,0],[.11,.06,.1]]);

function pickRig(id: string) {
  selectedRig=id;
  const rig=rigs.find(r=>r.id===id)!;
  document.querySelectorAll<HTMLButtonElement>('.rig-card').forEach(el=>{el.classList.toggle('active',el.dataset.rig===id);el.setAttribute('aria-pressed',String(el.dataset.rig===id));});
  $('rig-detail').innerHTML='<span></span>'; $('rig-detail').append(document.createTextNode(`${rig.joints} joints · ${rig.description}`));
  $('examples').replaceChildren();
  (examples[id] || examples.mixamo).forEach(([label,text])=>{const btn=document.createElement('button');btn.className='example';btn.textContent=label;btn.onclick=()=>{prompt.value=text;counter();};$('examples').append(btn);});
  if(!motion || motion.request.rig!==id){motion=null;activeJob='';playing=false;frame=0;setSkeleton(rig.parents,rig.rest.map(p=>p.slice(0,3)));$('empty-label').hidden=false;$('motion-badge').textContent='REST POSE';setPlaybackEnabled(false);updatePlay();}
  $('stage-info').innerHTML='';$('stage-info').append(document.createTextNode(rig.name.toUpperCase()),document.createElement('br'),document.createTextNode(`${rig.joints} JOINTS / SKELETON VIEW`));
}
function drawRigs() {
  $('rigs').replaceChildren();
  rigs.forEach(r=>{const btn=document.createElement('button');btn.className='rig-card';btn.dataset.rig=r.id;btn.innerHTML=icon(r.id==='mixamo'?'human':r.id);const label=document.createElement('span');label.textContent=r.name;btn.append(label);btn.onclick=()=>pickRig(r.id);$('rigs').append(btn);});
  pickRig(rigs.some(r=>r.id===selectedRig)?selectedRig:rigs[0].id);
}
function setPlaybackEnabled(value:boolean) { ['play','scrub','export'].forEach(id=>($<HTMLButtonElement>(id).disabled=!value)); }
function updatePlay() {$('play').innerHTML=icon(playing?'pause':'play');$('play').setAttribute('aria-label',playing?'Pause animation':'Play animation');}
$('play').onclick=()=>{if(!motion)return;playing=!playing;updatePlay();};
$('restart').onclick=()=>{frame=0;if(motion)drawPose(motion.positions[0]);};
$('loop').onclick=()=>{looping=!looping;$('loop').classList.toggle('active',looping);$('loop').setAttribute('aria-pressed',String(looping));};
$<HTMLInputElement>('scrub').oninput=()=>{playing=false;frame=Number($<HTMLInputElement>('scrub').value);if(motion)drawPose(motion.positions[Math.floor(frame)]);updatePlay();};
window.addEventListener('keydown',(event)=>{if(event.code==='Space'&&!['INPUT','TEXTAREA','SELECT','BUTTON'].includes((event.target as HTMLElement).tagName)&&!$('credits').hasAttribute('open')){event.preventDefault();$('play').click();}});
let previous=performance.now();
function animate(now:number){requestAnimationFrame(animate);const dt=Math.min((now-previous)/1000,.1);previous=now;
  if(motion){if(playing){frame+=dt*motion.fps*Number($<HTMLSelectElement>('speed').value);if(frame>=motion.frames){if(looping)frame%=motion.frames;else{frame=motion.frames-1;playing=false;updatePlay();}}}
    drawPose(motion.positions[Math.min(motion.frames-1,Math.floor(frame))]);
    $<HTMLInputElement>('scrub').value=String(Math.floor(frame));
    $('time').textContent=`${(frame/motion.fps).toFixed(2)} / ${(motion.frames/motion.fps).toFixed(2)} s`;
  }
  controls.update();renderer.render(scene,camera);
}requestAnimationFrame(animate);

async function openTake(job:Job) {
  try {
    const data=await api<Motion>(`/api/jobs/${job.id}/motion.json`);
    pickRig(job.request.rig);motion=data;activeJob=job.id;frame=0;playing=true;
    setSkeleton(data.parents,data.positions[0]);setPlaybackEnabled(true);updatePlay();
    $('empty-label').hidden=true;$('motion-badge').textContent='GENERATED';
    prompt.value=job.request.prompt;$<HTMLInputElement>('seed').value=String(job.request.seed);$<HTMLInputElement>('guidance').value=String(job.request.guidance);$('guidance-value').textContent=job.request.guidance.toFixed(1);$<HTMLSelectElement>('quality').value=job.request.quality;counter();
    ['bvh','json','npy'].forEach(ext=>{const link=$<HTMLAnchorElement>(`${ext}-link`);link.href=`/api/jobs/${job.id}/motion.${ext}`;link.download=`unimate-${job.id.slice(0,8)}.${ext}`;});
    renderTakes();
  }catch(exc){error((exc as Error).message);}
}
function renderTakes() {
  const completed=jobs.filter(j=>j.status==='complete');$('take-count').textContent=String(completed.length).padStart(2,'0');
  if(!completed.length)return;
  $('take-list').replaceChildren();
  completed.forEach(job=>{const btn=document.createElement('button');btn.className='take'+(activeJob===job.id?' active':'');
    const symbol=document.createElement('span');symbol.className='take-symbol';symbol.innerHTML=icon(job.request.rig==='mixamo'?'human':job.request.rig);btn.append(symbol);
    const copy=document.createElement('div');copy.className='take-copy';const title=document.createElement('div');title.className='take-title';title.textContent=job.request.prompt.replace(/^An object /i,'');
    const meta=document.createElement('div');meta.className='take-meta';meta.textContent=`${rigs.find(r=>r.id===job.request.rig)?.name || job.request.rig} · 2s · seed ${job.request.seed}`;
    copy.append(title,meta);btn.append(copy);btn.title=job.request.prompt;btn.onclick=()=>openTake(job);$('take-list').append(btn);});
}
$('export').onclick=()=>{$('export-menu').hidden=!$('export-menu').hidden;};
document.addEventListener('click',event=>{if(!(event.target as Element).closest('.export-wrap'))$('export-menu').hidden=true;});
$('about').onclick=()=> $<HTMLDialogElement>('credits').showModal();
$('credits-link').onclick=(e)=>{e.preventDefault();$<HTMLDialogElement>('credits').showModal();};
$('close-credits').onclick=()=> $<HTMLDialogElement>('credits').close();
function delay(ms:number){return new Promise(resolve=>setTimeout(resolve,ms));}
$('generate').onclick=async()=>{
  if(busy)return;
  const request: Request={prompt:prompt.value,rig:selectedRig,seed:Number($<HTMLInputElement>('seed').value),guidance:Number($<HTMLInputElement>('guidance').value),quality:$<HTMLSelectElement>('quality').value};
  if(!Number.isInteger(request.seed)||request.seed<0||request.seed>2147483647){error('Enter a whole-number seed from 0 to 2147483647.');return;}
  if(request.prompt.trim().length<3){error('Describe the motion before generating.');return;}
  busy=true;playing=false;updatePlay();updateGenerate();$('toast').hidden=true;$('generating').hidden=false;$('progress-label').textContent='Preparing generation';$('elapsed').textContent='0s elapsed';$('progress-bar').style.width='0';
  const start=performance.now();const timer=setInterval(()=>$('elapsed').textContent=`${Math.floor((performance.now()-start)/1000)}s elapsed`,1000);
  try{
    let job=await api<Job>('/api/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});
    while(job.status==='queued'||job.status==='running'){
      $('progress-label').textContent=job.message;$('progress-bar').style.width=`${job.progress*100}%`;
      await delay(1000);job=await api<Job>(`/api/jobs/${job.id}`);
    }
    if(job.status!=='complete')throw new Error(job.message);
    jobs=await api<Job[]>('/api/jobs');await openTake(job);
  }catch(exc){error((exc as Error).message);}
  finally{clearInterval(timer);busy=false;updateGenerate();$('generating').hidden=true;}
};
async function connect() {
  let drawn=false;
  while(true){
    try{
      const health=await api<Health>('/api/health');healthReady=health.status==='ready';updateGenerate();
      $('status-dot').classList.toggle('ready',healthReady);
      $('host-status').textContent=healthReady?'Model connected':'Model '+health.status;
      $('loading-notice').textContent=health.message;$('loading-notice').hidden=healthReady;
      if(healthReady&&!drawn){rigs=health.rigs;drawRigs();jobs=await api<Job[]>('/api/jobs');renderTakes();const latest=jobs.find(j=>j.status==='complete'&&j.request.rig===selectedRig);if(latest)await openTake(latest);drawn=true;}
      if(health.status==='error'){$('loading-notice').textContent='Model setup needs attention. See the host log. '+health.message;}
    }catch{$('host-status').textContent='Host unavailable';healthReady=false;updateGenerate();$('loading-notice').hidden=false;$('loading-notice').textContent='Cannot reach the inference host. Start server.py and reload.';}
    await delay(drawn?15000:2500);
  }
}void connect();
