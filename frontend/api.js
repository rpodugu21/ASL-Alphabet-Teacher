// All calls to the local backend (backend/server.py).

// Saves a PNG to data/raw/ and runs Hand Landmarker on it.
// Returns { name, annotation }.
export async function saveCapture(blob) {
  const res = await fetch("/api/capture", {
    method: "POST",
    headers: { "Content-Type": "image/png" },
    body: blob,
  });
  if (!res.ok) throw new Error(`Saving the photo failed (${res.status})`);
  return res.json();
}

// Names of saved photos, oldest first.
export async function listCaptures() {
  const res = await fetch("/api/captures");
  if (!res.ok) throw new Error(`Listing photos failed (${res.status})`);
  return res.json();
}

export function imageUrl(name) {
  return `/api/captures/${name}.png`;
}

// Hand Landmarker output saved next to the photo, or null if missing.
export async function getAnnotation(name) {
  const res = await fetch(`/api/captures/${name}.json`);
  return res.ok ? res.json() : null;
}
