// Camera view and capture. Captured photos are sent to the local backend,
// which saves them to data/raw/ and runs Hand Landmarker on them.

import { createFeedback } from "./feedback/feedback.js";
import { saveCapture } from "./api.js";
import { addPhoto, isViewerOpen, loadThumbnail } from "./thumbnail.js";

// Saved photos match what the camera sees; only the on-screen preview is mirrored.
const MIRROR_SAVED = false;

const stage = document.getElementById("stage");
const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const flash = document.getElementById("flash");
const statusText = document.getElementById("status");
const shutter = document.getElementById("shutter");

const feedback = createFeedback(document.getElementById("feedback"));

async function startCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    showStatus("This browser does not support camera access.");
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    shutter.disabled = false;
  } catch (err) {
    showStatus(
      err.name === "NotAllowedError"
        ? "Camera access was blocked. Allow it in your browser settings and reload."
        : `Could not start the camera: ${err.message}`
    );
  }
}

// Match the stage to the camera's shape so the preview has no black bars
video.addEventListener("resize", () => {
  if (video.videoWidth) stage.style.setProperty("--ar", `${video.videoWidth} / ${video.videoHeight}`);
});

function showStatus(message) {
  statusText.textContent = message;
  statusText.hidden = false;
}

async function capture() {
  if (!video.videoWidth) return;

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.save();
  if (MIRROR_SAVED) {
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
  }
  ctx.drawImage(video, 0, 0);
  ctx.restore();
  flashScreen();

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  try {
    const { name, annotation } = await saveCapture(blob);
    addPhoto(name, annotation);
  } catch (err) {
    console.error(err);
    feedback.text.setLines(["Could not save the photo. Is backend/server.py running?"]);
  }
}

function flashScreen() {
  flash.classList.add("on");
  requestAnimationFrame(() => requestAnimationFrame(() => flash.classList.remove("on")));
}

// Sample text until the backend provides real feedback
feedback.text.setLines(["Show your hand to the camera"]);

shutter.addEventListener("click", capture);

document.addEventListener("keydown", (e) => {
  if (isViewerOpen()) return;
  if (e.code === "Space" && !shutter.disabled) {
    e.preventDefault();
    capture();
  }
});

startCamera();
loadThumbnail();
