// ─── Part 3: Three.js 3D Doro — isolated module, graceful failure ─────────────
import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';

const canvas  = document.getElementById('doro-canvas');
const wrapper = document.getElementById('doro-canvas-wrapper');

function getSize() {
  const w = wrapper.offsetWidth  || 300;
  const h = wrapper.offsetHeight || 300;
  return Math.min(w, h);          // always square — prevents stretching
}

const sz = getSize();
const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(sz, sz);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.LinearToneMapping;
renderer.toneMappingExposure = 1.2;

const scene  = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 2000);

// Lights — lower ambient to preserve depth, key + fill + rim for 3D look
scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const key = new THREE.DirectionalLight(0xffffff, 1.8);
key.position.set(2, 3, 4);
scene.add(key);
const fill = new THREE.DirectionalLight(0xffe0f0, 0.6);
fill.position.set(-3, 1, 2);
scene.add(fill);
const rim = new THREE.DirectionalLight(0xaaccff, 0.7);
rim.position.set(0, 2, -4);
scene.add(rim);

// ─── Orientation group ────────────────────────────────────────────────────────
// doro.fbx: mesh-only, exported from Blender with Apply Transform, -Z Forward,
// Y Up.  FBXLoader handles the coordinate conversion automatically — no manual
// rotation needed.
const doroOrient = new THREE.Group();
scene.add(doroOrient);

// ─── Animation system ────────────────────────────────────────────────────────

let doroModel   = null;
let baseY       = 0;
let isSleeping  = false;
let currentAnim = null;
let animAmp     = 12;
const clock     = new THREE.Clock();

const ANIMS = {
  idle: (m, t) => {
    if (!isSleeping) m.position.y = baseY + Math.sin(t * 1.6) * animAmp * 0.1;
    return false;
  },
  feed: (m, t) => {
    const p = t / 0.9;
    m.position.y = baseY + animAmp * (p < 0.4
      ? p / 0.4
      : 1 - ((p - 0.4) / 0.6) ** 2);
    return t > 0.9;
  },
  play: (m, t) => {
    const p = Math.min(t / 1.2, 1);
    m.position.y = baseY + Math.sin(p * Math.PI) * animAmp * 1.4;
    m.rotation.y = p * Math.PI * 2;
    return t > 1.2;
  },
  pet_cat: (m, t) => {
    m.rotation.z = Math.sin(t * 9) * 0.13 * Math.max(0, 1 - t);
    return t > 1.0;
  },
  wash: (m, t) => {
    m.position.x = Math.sin(t * 22) * animAmp * 0.4 * Math.max(0, 1 - t / 0.8);
    return t > 0.8;
  },
  sleep: (m, t) => {
    m.rotation.z = Math.min(t / 0.6, 1) * 0.42;
    isSleeping = true;
    return t > 0.6;
  },
  wake: (m, t) => {
    m.rotation.z = Math.max(0, 0.42 * (1 - t / 0.4));
    if (t > 0.4) isSleeping = false;
    return t > 0.4;
  },
  treat: (m, t) => {
    m.position.y = baseY + Math.abs(Math.sin(t * 13)) * animAmp * 0.8 * Math.max(0, 1 - t);
    const pulse = 1 + Math.sin(t * 15) * 0.07 * Math.max(0, 1 - t);
    m.scale.setScalar((m.userData.baseScale || 1) * pulse);
    return t > 1.0;
  },
  status: (m, t) => {
    m.rotation.y += 0.022;
    return t > 2.8;
  },
  rename: (m, t) => {
    const pulse = 1 + Math.sin(t * 11) * 0.09 * Math.max(0, 1 - t / 0.8);
    m.scale.setScalar((m.userData.baseScale || 1) * pulse);
    return t > 0.8;
  },
};

function resetModel(m) {
  m.position.set(0, baseY, 0);
  m.rotation.set(0, 0, 0);
  m.scale.setScalar(m.userData.baseScale || 1);
}

window.doroPlayAnimation = function(name) {
  if (!doroModel) return;
  if (name !== 'wake') isSleeping = false;
  resetModel(doroModel);
  currentAnim = { name, startTime: clock.getElapsedTime() };
};

// ─── Render loop ─────────────────────────────────────────────────────────────

(function animate() {
  requestAnimationFrame(animate);
  if (doroModel) {
    if (currentAnim) {
      const t = clock.getElapsedTime() - currentAnim.startTime;
      const done = ANIMS[currentAnim.name]?.(doroModel, t);
      if (done) {
        currentAnim = null;
        resetModel(doroModel);
        if (isSleeping) doroModel.rotation.z = 0.42;
      }
    } else {
      ANIMS.idle(doroModel, clock.getElapsedTime());
    }
  }
  renderer.render(scene, camera);
})();

// ─── Load FBX ────────────────────────────────────────────────────────────────

const loader = new FBXLoader();
loader.load(
  '/static/models/doro.fbx',   // ← mesh-only, no skeleton, no UE4 bone rest-pose issue
  (obj) => {
    // Load ORM texture (R=AO, G=Roughness, B=Metallic), then upgrade materials
    const texLoader = new THREE.TextureLoader();
    const ormTex = texLoader.load('/static/models/CH_NPC_Dororog_ORM.png');
    ormTex.colorSpace = THREE.NoColorSpace;   // ORM is linear data, not sRGB

    obj.traverse(child => {
      if (!child.isMesh) return;
      const oldMats = Array.isArray(child.material) ? child.material : [child.material];
      const newMats = oldMats.map(mat => {
        const std = new THREE.MeshStandardMaterial({
          map: mat.map || null,            // albedo from FBX
          color: 0xffffff,
          roughnessMap: ormTex,            // G channel → roughness
          metalnessMap: ormTex,            // B channel → metalness
          aoMap: ormTex,                   // R channel → ambient occlusion
          aoMapIntensity: 1.0,
          roughness: 1.0,                  // let the map control it fully
          metalness: 1.0,                  // let the map control it fully
          vertexColors: false,
        });
        if (mat.normalMap) std.normalMap = mat.normalMap;
        mat.dispose();
        return std;
      });
      child.material = newMats.length === 1 ? newMats[0] : newMats;

      // aoMap needs UV2 — copy UV1 to UV2 if missing
      if (child.geometry && !child.geometry.attributes.uv2 && child.geometry.attributes.uv) {
        child.geometry.attributes.uv2 = child.geometry.attributes.uv;
      }
    });

    // Measure bounding box
    const box0 = new THREE.Box3().setFromObject(obj);
    const size = box0.getSize(new THREE.Vector3());
    console.log('[Doro] mesh-only size XYZ:', size.x.toFixed(1), size.y.toFixed(1), size.z.toFixed(1));

    // Scale to fit — smaller for better framing with padding
    const targetH = 40;
    const scale = targetH / Math.max(size.x, size.y, size.z);
    obj.scale.setScalar(scale);
    obj.userData.baseScale = scale;

    // Add to group FIRST so the rotation is applied, then compute the
    // world-space bounding box to correctly center the result at origin.
    doroOrient.add(obj);
    doroOrient.updateWorldMatrix(true, true);
    const worldBox = new THREE.Box3().setFromObject(doroOrient);
    const worldCenter = worldBox.getCenter(new THREE.Vector3());
    doroOrient.position.sub(worldCenter);   // shift the whole group to center at (0,0,0)
    baseY = 0;
    animAmp = targetH * 0.22;

    // Camera: face toward +Z, camera slightly above for a flattering angle
    const dist = targetH * 2.8;
    camera.position.set(0, targetH * 0.15, dist);
    camera.lookAt(0, 0, 0);

    doroModel = obj;
  },
  undefined,
  (err) => {
    console.warn('FBX load failed — showing fallback image.', err);
    canvas.style.display = 'none';
    const fb = document.getElementById('doro-fallback');
    if (fb) fb.style.display = 'block';
  }
);

// ─── Resize ──────────────────────────────────────────────────────────────────

window.addEventListener('resize', () => {
  const s = getSize();
  renderer.setSize(s, s);
});
