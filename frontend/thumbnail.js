// Bottom-right thumbnail and full-screen viewer.
// Photos are loaded from data/raw/ through the backend and drawn with their
// Hand Landmarker annotation on top.

import { getAnnotation, imageUrl, listCaptures } from "./api.js";

// Pairs of landmark indices joined by a line (wrist = 0, fingertips = 4, 8, 12, 16, 20)
const HAND_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [5, 9], [9, 10], [10, 11], [11, 12],
  [9, 13], [13, 14], [14, 15], [15, 16],
  [13, 17], [17, 18], [18, 19], [19, 20],
  [0, 17],
];

const thumb = document.getElementById("thumb");
const thumbImg = document.getElementById("thumb-img");
const viewer = document.getElementById("viewer");
const viewerCanvas = document.getElementById("viewer-canvas");
const viewerPrev = document.getElementById("viewer-prev");
const viewerNext = document.getElementById("viewer-next");
const viewerCount = document.getElementById("viewer-count");

const names = []; // oldest first
const annotations = new Map(); // name -> annotation
let index = 0;
let latest = null; // name of the most recent photo taken

export async function loadThumbnail() {
  try {
    names.push(...(await listCaptures()));
  } catch (err) {
    console.error(err);
  }
  latest = names.at(-1) ?? null;
  updateThumb();
}

export function addPhoto(name, annotation) {
  names.push(name);
  annotations.set(name, annotation);
  latest = name;
  updateThumb();
}

export function getLatestPhoto() {
  return latest;
}

export function isViewerOpen() {
  return !viewer.hidden;
}

function updateThumb() {
  if (!latest) return;
  thumbImg.src = imageUrl(latest);
  thumb.disabled = false;
}

// Opens at the first photo; the right arrow moves to newer ones
function openViewer() {
  if (!names.length) return;
  index = 0;
  viewer.hidden = false;
  showPhoto();
}

function closeViewer() {
  viewer.hidden = true;
}

function step(delta) {
  const next = index + delta;
  if (next < 0 || next >= names.length) return;
  index = next;
  showPhoto();
}

async function showPhoto() {
  const shown = index;
  const name = names[index];
  viewerPrev.disabled = index === 0;
  viewerNext.disabled = index === names.length - 1;
  viewerCount.textContent = `${index + 1} / ${names.length}  ·  ${name}`;

  const [img, annotation] = await Promise.all([loadImage(imageUrl(name)), annotationFor(name)]);
  if (shown !== index) return; // moved to another photo while loading
  draw(img, annotation);
}

function loadImage(src) {
  const img = new Image();
  img.src = src;
  return img.decode().then(() => img);
}

async function annotationFor(name) {
  if (!annotations.has(name)) annotations.set(name, await getAnnotation(name));
  return annotations.get(name);
}

function draw(img, annotation) {
  const w = (viewerCanvas.width = img.naturalWidth);
  const h = (viewerCanvas.height = img.naturalHeight);
  const ctx = viewerCanvas.getContext("2d");
  ctx.drawImage(img, 0, 0);
  if (!annotation) return;

  const lineWidth = Math.max(2, w / 400);
  ctx.lineWidth = lineWidth;
  ctx.lineCap = "round";

  for (const hand of annotation.hands) {
    const points = hand.landmarks.map((p) => [p.x * w, p.y * h]);

    ctx.strokeStyle = "#4ade80";
    ctx.beginPath();
    for (const [a, b] of HAND_CONNECTIONS) {
      ctx.moveTo(...points[a]);
      ctx.lineTo(...points[b]);
    }
    ctx.stroke();

    ctx.fillStyle = "#f87171";
    for (const [x, y] of points) {
      ctx.beginPath();
      ctx.arc(x, y, lineWidth * 1.8, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

thumb.addEventListener("click", openViewer);
document.getElementById("viewer-close").addEventListener("click", closeViewer);
viewerPrev.addEventListener("click", () => step(-1));
viewerNext.addEventListener("click", () => step(1));
viewer.addEventListener("click", (e) => {
  if (e.target === viewer) closeViewer();
});

document.addEventListener("keydown", (e) => {
  if (viewer.hidden) return;
  if (e.key === "Escape") closeViewer();
  else if (e.key === "ArrowLeft") step(-1);
  else if (e.key === "ArrowRight") step(1);
});
