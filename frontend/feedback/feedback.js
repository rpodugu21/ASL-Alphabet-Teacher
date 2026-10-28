// Feedback panel: progress bar across the top, text underneath.

import { createProgressBar } from "./progress-bar.js";
import { createFeedbackText } from "./feedback-text.js";

export function createFeedback(container) {
  const progress = createProgressBar();
  const text = createFeedbackText();
  container.append(progress.el, text.el);
  return { progress, text };
}
