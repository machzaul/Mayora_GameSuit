// copy-mediapipe.mjs
import { mkdir, copyFile, readdir } from 'node:fs/promises';
import { join } from 'node:path';

const sourceHands = 'node_modules/@mediapipe/hands';
const sourceCamera = 'node_modules/@mediapipe/camera_utils';
const destDir = 'assets/mediapipe';

const filesToCopy = [
  { src: join(sourceHands, 'hands.js'), dest: join(destDir, 'hands.js') },
  { src: join(sourceHands, 'hands_solution_simd_wasm_bin.wasm'), dest: join(destDir, 'hands_solution_simd_wasm_bin.wasm') },
  { src: join(sourceHands, 'hands_solution_simd_wasm_bin.data'), dest: join(destDir, 'hands_solution_simd_wasm_bin.data') },
  { src: join(sourceHands, 'hands_solution_simd_wasm_bin.js'), dest: join(destDir, 'hands_solution_simd_wasm_bin.js') }
];

async function findCameraUtils() {
  const files = await readdir(sourceCamera);
  const jsFiles = files.filter(f => f.endsWith('.js'));
  
  if (jsFiles.length === 0) {
    throw new Error('camera_utils.js tidak ditemukan di node_modules/@mediapipe/camera_utils/');
  }
  
  return join(sourceCamera, jsFiles[0]);
}

async function copyFiles() {
  console.log('📦 Menyalin file MediaPipe ke assets/mediapipe...\n');
  
  // Buat folder tujuan
  await mkdir(destDir, { recursive: true });
  
  // Salin file hands
  for (const { src, dest } of filesToCopy) {
    await copyFile(src, dest);
    console.log(`✅ ${dest.replace('assets/mediapipe/', '')}`);
  }
  
  // Cari dan salin camera_utils.js
  const cameraUtilsPath = await findCameraUtils();
  const cameraUtilsDest = join(destDir, 'camera_utils.js');
  await copyFile(cameraUtilsPath, cameraUtilsDest);
  console.log(`✅ camera_utils.js`);
  
  console.log('\n✨ Semua file MediaPipe berhasil disalin!');
}

copyFiles().catch(err => {
  console.error('\n❌ Gagal menyalin file:');
  console.error(err.message);
  process.exit(1);
});