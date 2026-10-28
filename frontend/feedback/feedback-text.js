// Text area under the progress bar. Grows downward with the number of lines.

export function createFeedbackText() {
  const el = document.createElement("ul");
  el.className = "feedback-text";

  // lines: strings, most important first
  function setLines(lines) {
    el.replaceChildren(
      ...lines.map((line) => {
        const li = document.createElement("li");
        li.textContent = line;
        return li;
      })
    );
  }

  return { el, setLines };
}
