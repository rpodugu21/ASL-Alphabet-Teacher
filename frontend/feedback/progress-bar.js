// Progress bar: a label with a bar underneath. Spans the top of the feedback panel.

export function createProgressBar(label = "Match") {
  const el = document.createElement("div");
  el.className = "progress";
  el.innerHTML = `
    <span class="progress-label"></span>
    <div class="progress-track"><div class="progress-fill"></div></div>
  `;
  el.querySelector(".progress-label").textContent = label;
  const fill = el.querySelector(".progress-fill");

  let value = 0;

  // value: 0–100
  function setValue(next) {
    value = Math.max(0, Math.min(100, next));
    fill.style.width = `${value}%`;
    el.dataset.level = value >= 80 ? "good" : value >= 50 ? "ok" : "bad";
  }

  setValue(0);
  return { el, setValue, getValue: () => value };
}
