const elements = {
  recipients: document.querySelector("#recipients"),
  subject: document.querySelector("#subject"),
  body: document.querySelector("#body"),
  resume: document.querySelector("#resume"),
  confirmation: document.querySelector("#confirmation"),
  validateButton: document.querySelector("#validateButton"),
  sendButton: document.querySelector("#sendButton"),
  cancelButton: document.querySelector("#cancelButton"),
  validationResult: document.querySelector("#validationResult"),
  formError: document.querySelector("#formError"),
  modeBanner: document.querySelector("#modeBanner"),
  limitBadge: document.querySelector("#limitBadge"),
  resumeHelp: document.querySelector("#resumeHelp"),
  progressPanel: document.querySelector("#progressPanel"),
  jobStatus: document.querySelector("#jobStatus"),
  progressPercent: document.querySelector("#progressPercent"),
  progressBar: document.querySelector("#progressBar"),
  processedCount: document.querySelector("#processedCount"),
  sentCount: document.querySelector("#sentCount"),
  sentLabel: document.querySelector("#sentLabel"),
  failedCount: document.querySelector("#failedCount"),
  totalCount: document.querySelector("#totalCount"),
  duplicateInfo: document.querySelector("#duplicateInfo"),
  failureList: document.querySelector("#failureList"),
  failureItems: document.querySelector("#failureItems"),
};

let config = null;
let currentJobId = null;
let eventSource = null;

function show(element, visible = true) {
  element.classList.toggle("hidden", !visible);
}

function displayError(message) {
  elements.formError.textContent =
    typeof message === "string" ? message : JSON.stringify(message);
  show(elements.formError);
}

function clearError() {
  elements.formError.textContent = "";
  show(elements.formError, false);
}

async function responseError(response) {
  try {
    const payload = await response.json();
    const detail = payload.detail;
    if (detail && typeof detail === "object" && detail.message) {
      const invalid = detail.invalid?.length
        ? ` Invalid: ${detail.invalid.join(", ")}`
        : "";
      return `${detail.message}${invalid}`;
    }
    return typeof detail === "string" ? detail : JSON.stringify(detail || payload);
  } catch {
    return `Request failed with status ${response.status}.`;
  }
}

async function loadConfig() {
  const response = await fetch("/api/config");
  if (!response.ok) {
    throw new Error(await responseError(response));
  }

  config = await response.json();
  elements.subject.value = config.default_subject;
  elements.body.value = config.default_body;
  elements.limitBadge.textContent = `Maximum ${config.max_recipients} unique recipients`;
  elements.resumeHelp.textContent =
    `PDF only; maximum ${config.max_resume_size_mb} MB.`;

  if (config.dry_run) {
    elements.modeBanner.textContent =
      "DRY-RUN MODE: messages are built and counted, but no SMTP connection is made. " +
      "Set SMTP_DRY_RUN=false in .env to send real emails.";
    show(elements.modeBanner);
    elements.sentLabel.textContent = "Simulated";
  } else if (!config.smtp_configured) {
    elements.modeBanner.textContent =
      "SMTP is not configured. Update .env and restart the application.";
    show(elements.modeBanner);
    elements.sendButton.disabled = true;
  }
}

async function validateRecipients() {
  clearError();
  show(elements.validationResult, false);

  const recipients = elements.recipients.value.trim();
  if (!recipients) {
    displayError("Paste at least one recruiter email address.");
    return null;
  }

  elements.validateButton.disabled = true;
  try {
    const response = await fetch("/api/recipients/validate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({recipients}),
    });

    if (!response.ok) {
      throw new Error(await responseError(response));
    }

    const result = await response.json();
    const parts = [
      `${result.valid.length} valid unique address(es)`,
      `${result.duplicate_count} duplicate(s) removed`,
      `${result.invalid.length} invalid address(es)`,
    ];

    if (!result.within_limit) {
      parts.push(`batch exceeds the limit of ${result.max_recipients}`);
    }

    elements.validationResult.textContent = parts.join(" • ");
    show(elements.validationResult);
    return result;
  } catch (error) {
    displayError(error.message);
    return null;
  } finally {
    elements.validateButton.disabled = false;
  }
}

function renderJob(job) {
  show(elements.progressPanel);
  elements.jobStatus.textContent =
    `${job.status.toUpperCase()}${job.dry_run ? " · DRY RUN" : ""}`;
  elements.progressPercent.textContent = `${job.progress_percent}%`;
  elements.progressBar.style.width = `${job.progress_percent}%`;
  elements.processedCount.textContent = job.processed;
  elements.sentCount.textContent = job.sent;
  elements.failedCount.textContent = job.failed;
  elements.totalCount.textContent = job.total;
  elements.duplicateInfo.textContent =
    `${job.duplicate_count} duplicate address(es) removed before sending.`;

  elements.failureItems.innerHTML = "";
  if (job.failures.length) {
    for (const failure of job.failures) {
      const item = document.createElement("li");
      item.textContent = `${failure.email}: ${failure.error}`;
      elements.failureItems.appendChild(item);
    }
    show(elements.failureList);
  } else {
    show(elements.failureList, false);
  }

  const terminal = ["completed", "cancelled", "failed"].includes(job.status);
  elements.sendButton.disabled = !terminal;
  show(elements.cancelButton, !terminal);

  if (terminal && eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function watchJob(jobId) {
  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource(`/api/jobs/${jobId}/events`);
  eventSource.onmessage = (event) => {
    renderJob(JSON.parse(event.data));
  };
  eventSource.onerror = async () => {
    eventSource?.close();
    eventSource = null;

    try {
      const response = await fetch(`/api/jobs/${jobId}`);
      if (response.ok) {
        renderJob(await response.json());
      } else {
        displayError(await responseError(response));
      }
    } catch (error) {
      displayError(`Progress connection closed: ${error.message}`);
    }
  };
}

async function startJob() {
  clearError();

  const validation = await validateRecipients();
  if (!validation) return;
  if (validation.invalid.length) {
    displayError(`Correct invalid addresses: ${validation.invalid.join(", ")}`);
    return;
  }
  if (!validation.within_limit) {
    displayError(`Reduce the batch to ${validation.max_recipients} unique addresses.`);
    return;
  }
  if (!elements.resume.files.length) {
    displayError("Select your résumé PDF.");
    return;
  }
  if (!elements.confirmation.checked) {
    displayError("Confirm that you are authorized to contact these recipients.");
    return;
  }

  const formData = new FormData();
  formData.append("recipients", elements.recipients.value);
  formData.append("subject", elements.subject.value);
  formData.append("body", elements.body.value);
  formData.append("confirmation", "true");
  formData.append("resume", elements.resume.files[0]);

  elements.sendButton.disabled = true;

  try {
    const response = await fetch("/api/jobs", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await responseError(response));
    }

    const job = await response.json();
    currentJobId = job.id;
    renderJob(job);
    watchJob(job.id);
    elements.progressPanel.scrollIntoView({behavior: "smooth", block: "start"});
  } catch (error) {
    displayError(error.message);
    elements.sendButton.disabled = false;
  }
}

async function cancelJob() {
  if (!currentJobId) return;

  elements.cancelButton.disabled = true;
  try {
    const response = await fetch(`/api/jobs/${currentJobId}/cancel`, {
      method: "POST",
    });
    if (!response.ok) {
      throw new Error(await responseError(response));
    }
    renderJob(await response.json());
  } catch (error) {
    displayError(error.message);
  } finally {
    elements.cancelButton.disabled = false;
  }
}

elements.validateButton.addEventListener("click", validateRecipients);
elements.sendButton.addEventListener("click", startJob);
elements.cancelButton.addEventListener("click", cancelJob);

loadConfig().catch((error) => displayError(error.message));
