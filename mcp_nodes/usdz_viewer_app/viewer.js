console.log('[USDZ Viewer] script loaded');
(function () {
  console.log('[USDZ Viewer] IIFE start');
  function qs(name) {
    const p = new URLSearchParams(window.location.search);
    return p.get(name) || "";
  }
  function appendLog(msg) {
    try {
      const pre = document.getElementById("log");
      if (pre) {
        const line = `[${new Date().toISOString()}] ${msg}`;
        pre.textContent += (pre.textContent ? "\n" : "") + line;
      }
      // Mirror to console
      // eslint-disable-next-line no-console
      console.log(msg);
    } catch (_) {}
  }
  async function probe(url) {
    appendLog(`Probing URL: ${url}`);
    const sameOrigin = new URL(url, window.location.href).origin === window.location.origin;
    appendLog(`Same origin: ${sameOrigin}`);
    appendLog(`User-Agent: ${navigator.userAgent}`);
    try {
      const resp = await fetch(url, { method: "GET", mode: "cors" });
      appendLog(`Fetch response: type=${resp.type} ok=${resp.ok} status=${resp.status}`);
      if (resp.type === "opaque") {
        appendLog("Opaque response (likely CORS not enabled) - headers not readable.");
      } else {
        appendLog(`Content-Type: ${resp.headers.get("content-type")}`);
        appendLog(`Content-Length: ${resp.headers.get("content-length")}`);
      }
    } catch (e) {
      appendLog(`Fetch error: ${e && e.message ? e.message : String(e)}`);
    }
  }
  const src = qs("src");
  const title = qs("title") || "USDZ Viewer";
  const srcUrlObj = src ? new URL(src, window.location.href) : null;
  const srcPathLower = srcUrlObj ? srcUrlObj.pathname.toLowerCase() : "";

  document.getElementById("title").textContent = title;
  const srcLabel = document.getElementById("srcLabel");
  srcLabel.textContent = src;

  // Diagnostics controls
  const reprobe = document.getElementById("reprobe");
  const copyDiag = document.getElementById("copyDiag");
  if (reprobe) {
    reprobe.addEventListener("click", function () { probe(src); });
  }
  if (copyDiag) {
    copyDiag.addEventListener("click", async function () {
      try {
        const text = document.getElementById("log").textContent || "";
        await navigator.clipboard.writeText(text);
        appendLog("Diagnostics copied to clipboard");
      } catch (e) { appendLog("Copy failed: " + (e && e.message ? e.message : String(e))); }
    });
  }
  // Auto-probe on load
  if (src) { probe(src); }

  // Three.js preview for USDZ (via USDZLoader)
  (async function () {
    try {
      if (!src) return;
      const isUSDZ = srcPathLower.endsWith('.usdz');

      appendLog('Initializing three.js viewer...');
      const modules = await Promise.all([
import('three'),
import('three/addons/controls/OrbitControls.js'),
import('tinyusdz/TinyUSDZLoader.js'),
import('tinyusdz/TinyUSDZLoaderUtils.js'),
      ]);
      const THREE = modules[0];
      const OrbitControls = modules[1].OrbitControls;
      const TinyUSDZLoader = modules[2].TinyUSDZLoader;
      const TinyUSDZLoaderUtils = modules[3].TinyUSDZLoaderUtils;

      const mount = document.getElementById('threeMount');
      const rect = mount.getBoundingClientRect();

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.setPixelRatio(window.devicePixelRatio);
      renderer.setSize(rect.width, rect.height);
      mount.appendChild(renderer.domElement);

      const scene = new THREE.Scene();
      scene.background = null;
      scene.up.set(0, 0, 1);
      const camera = new THREE.PerspectiveCamera(50, rect.width / rect.height, 0.01, 1000);
      camera.up.set(0, 0, 1);
      camera.position.set(2.5, 1.5, 3.5);

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;

      scene.add(new THREE.AmbientLight(0xffffff, 0.6));
      const dir = new THREE.DirectionalLight(0xffffff, 0.8);
      dir.position.set(2, 4, 2);
      scene.add(dir);

      const grid = new THREE.GridHelper(10, 10, 0x3f3f46, 0x27272a);
      grid.material.opacity = 0.25; grid.material.transparent = true;
      grid.rotateX(Math.PI / 2);
      scene.add(grid);

      if (!isUSDZ) {
        appendLog('Unsupported extension for in-canvas preview.');
        return;
      }

      const loader = new TinyUSDZLoader();
      try {
        await loader.init({ useZstdCompressedWasm: false });
      } catch (e) {
        appendLog('TinyUSDZ init error: ' + (e && e.message ? e.message : String(e)));
        return;
      }

      try {
        const usd_scene = await loader.loadAsync(src);
        const usdRootNode = usd_scene.getDefaultRootNode();
        const defaultMtl = TinyUSDZLoaderUtils.createDefaultMaterial();
        const options = { overrideMaterial: false, envMap: null, envMapIntensity: 1.0 };
        const threeNode = TinyUSDZLoaderUtils.buildThreeNode(usdRootNode, defaultMtl, usd_scene, options);
        scene.add(threeNode);
        const box = new THREE.Box3().setFromObject(threeNode);
        const size = box.getSize(new THREE.Vector3()).length() || 1;
        const center = box.getCenter(new THREE.Vector3());
        controls.target.copy(center);
        const dist = size * 1.25;
        camera.position.copy(center).add(new THREE.Vector3(dist, dist * 0.5, dist));
        camera.near = size / 100; camera.far = size * 100; camera.updateProjectionMatrix();
        const overlay = document.getElementById('overlay'); if (overlay) overlay.remove();
        appendLog('USDZ loaded successfully.');
      } catch (e) {
        appendLog('TinyUSDZ load error: ' + (e && e.message ? e.message : String(e)));
      }

      function onResize() {
        const r = mount.getBoundingClientRect();
        camera.aspect = r.width / r.height;
        camera.updateProjectionMatrix();
        renderer.setSize(r.width, r.height);
      }
      window.addEventListener('resize', onResize);

      (function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
      })();
    } catch (e) {
      appendLog('Viewer init error: ' + (e && e.message ? e.message : String(e)));
    }
  })();

  window.addEventListener('error', (e) => {
    appendLog('Window error: ' + (e.error && e.error.message ? e.error.message : e.message));
  });
  window.addEventListener('unhandledrejection', (e) => {
    appendLog('Unhandled rejection: ' + (e.reason && e.reason.message ? e.reason.message : String(e.reason)));
  });
})();


