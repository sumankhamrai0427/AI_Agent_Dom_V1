document.addEventListener("DOMContentLoaded", () => {
    const taskForm = document.getElementById("taskForm");
    const deedFileInput = document.getElementById("deed_file");
    const fileLabel = document.getElementById("fileLabel");
    
    const consoleTaskId = document.getElementById("consoleTaskId");
    const consoleStep = document.getElementById("consoleStep");
    const statusBadge = document.getElementById("statusBadge");
    const logTerminal = document.getElementById("logTerminal");
    
    const liveViewImg = document.getElementById("liveViewImg");
    const livePlaceholder = document.getElementById("livePlaceholder");
    
    const captchaModal = document.getElementById("captchaModal");
    const captchaImageSrc = document.getElementById("captchaImageSrc");
    const btnSolveCaptcha = document.getElementById("btnSolveCaptcha");
    
    const resultsSection = document.getElementById("resultsSection");
    const gisIframe = document.getElementById("gisIframe");
    const downloadHtml = document.getElementById("downloadHtml");
    const downloadExcel = document.getElementById("downloadExcel");
    const downloadGeoJson = document.getElementById("downloadGeoJson");

    let currentTaskId = null;
    let pollIntervalId = null;
    let loggedTimestamps = new Set();

    // 1. File Upload styling update
    deedFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            fileLabel.textContent = `Deed Selected: ${e.target.files[0].name}`;
            fileLabel.style.color = "var(--secondary)";
        } else {
            fileLabel.textContent = "Drag & drop or click to browse";
            fileLabel.style.color = "inherit";
        }
    });

    // 2. Submit Task Form
    taskForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        // Reset console state
        logTerminal.innerHTML = "";
        loggedTimestamps.clear();
        addTerminalLine("Aetheris", "Initializing request payload...", "info");
        
        const formData = new FormData(taskForm);
        
        // Append a user-friendly objective based on selected state
        const state = formData.get("state");
        const objective = `Deed Audit: Run autonomous ownership verification audit for uploaded deed in state: ${state}.`;
        formData.append("objective", objective);

        try {
            const response = await fetch("/api/tasks", {
                method: "POST",
                body: formData
            });
            const data = await response.json();
            
            if (data.success) {
                currentTaskId = data.task_id;
                consoleTaskId.textContent = `Task ID: #${currentTaskId}`;
                addTerminalLine("Supervisor", `Task created successfully. ID: #${currentTaskId}`, "success");
                
                // Hide results section if visible from previous run
                resultsSection.style.display = "none";
                
                // Start polling status
                startPolling(currentTaskId);
            } else {
                addTerminalLine("SystemError", `Failed to initiate task: ${data.error}`, "error");
            }
        } catch (error) {
            addTerminalLine("SystemError", `API connection failed: ${error.message}`, "error");
        }
    });

    // 3. Status Polling Loop
    function startPolling(taskId) {
        if (pollIntervalId) clearInterval(pollIntervalId);
        
        pollIntervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/tasks/${taskId}`);
                const data = await response.json();
                
                if (data.success) {
                    const task = data.task;
                    updateUIStatus(task);
                    processLogs(task.logs);
                    
                    if (task.status === "COMPLETED") {
                        clearInterval(pollIntervalId);
                        addTerminalLine("Supervisor", "Workflow finalized successfully! Output files ready.", "success");
                        
                        // Log validation results to terminal console
                        if (task.verification) {
                            if (!task.verification.is_valid) {
                                addTerminalLine("ValidationAgent", "WARNING: Mismatch/discrepancies detected between Deed and Portal!", "error");
                                if (task.verification.conflicts && Array.isArray(task.verification.conflicts)) {
                                    task.verification.conflicts.forEach(conflict => {
                                        addTerminalLine("ValidationAgent", `  - Discrepancy: ${conflict}`, "warning");
                                    });
                                }
                            } else {
                                addTerminalLine("ValidationAgent", "SUCCESS: All records matched successfully with the government database!", "success");
                            }
                        }
                        
                        displayResults(task);
                    } else if (task.status === "FAILED") {
                        clearInterval(pollIntervalId);
                        addTerminalLine("Supervisor", `Workflow terminated with error: ${task.error_message}`, "error");
                    }
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 2000);
    }

    // 4. Update Header and Badges
    function updateUIStatus(task) {
        consoleStep.textContent = `Current Step: ${task.current_step || 'Processing'}`;
        
        statusBadge.textContent = task.status;
        statusBadge.className = "status-badge"; // Reset classes
        
        if (task.status === "PENDING") statusBadge.classList.add("badge-pending");
        else if (task.status === "RUNNING") statusBadge.classList.add("badge-running");
        else if (task.status === "COMPLETED") statusBadge.classList.add("badge-completed");
        else if (task.status === "FAILED") statusBadge.classList.add("badge-failed");
        else if (task.status === "PAUSED_CAPTCHA") {
            statusBadge.classList.add("badge-captcha");
            showCaptchaModal(task.logs);
        }

        // If task has extracted document, render the deed preview
        const deedPreviewCard = document.getElementById("deedPreviewCard");
        const deedPreviewContent = document.getElementById("deedPreviewContent");
        
        if (task.extracted_document && deedPreviewCard && deedPreviewContent) {
            deedPreviewCard.style.display = "block";
            const doc = task.extracted_document;
            deedPreviewContent.innerHTML = `
                <div><strong>Owner:</strong> <span style="color:var(--secondary)">${doc.owner_name || 'N/A'}</span></div>
                <div><strong>Father:</strong> <span style="color:var(--text)">${doc.father_name || 'N/A'}</span></div>
                <div><strong>State / Dist:</strong> <span style="color:var(--text)">${task.metadata.state || 'N/A'} / ${doc.district || 'N/A'}</span></div>
                <div><strong>Village:</strong> <span style="color:var(--text)">${doc.village || 'N/A'}</span></div>
                <div><strong>Khata / Plot:</strong> <span style="color:var(--secondary)">${doc.khata || 'N/A'}</span></div>
                <div><strong>Khasra:</strong> <span style="color:var(--text)">${doc.khasra || 'N/A'}</span></div>
                <div><strong>Area:</strong> <span style="color:var(--text)">${doc.area || 'N/A'}</span></div>
                <div><strong>Ref No:</strong> <span style="color:var(--text)">${doc.reference_number || 'N/A'}</span></div>
            `;
        } else if (deedPreviewCard) {
            deedPreviewCard.style.display = "none";
        }
    }

    // 5. Render live logs and browser images
    function processLogs(logs) {
        if (!logs || logs.length === 0) return;
        
        let latestScreenshot = null;
        
        logs.forEach(log => {
            // Generate unique log signature based on time, agent, and result
            const logSignature = `${log.timestamp}_${log.agent_name}_${log.action}`;
            
            if (!loggedTimestamps.has(logSignature)) {
                loggedTimestamps.add(logSignature);
                
                const timeStr = log.timestamp.split(" ")[1];
                let lineType = "info";
                if (log.status === "FAILURE") lineType = "error";
                else if (log.status === "WARNING") lineType = "warning";
                
                const msg = log.result || log.error_message || `Executing: ${log.action}`;
                addTerminalLine(log.agent_name, msg, lineType, timeStr);
            }
            
            if (log.screenshot_url) {
                latestScreenshot = log.screenshot_url;
            }
        });
        
        // Update browser live view feed
        if (latestScreenshot) {
            liveViewImg.src = latestScreenshot;
            liveViewImg.style.display = "block";
            livePlaceholder.style.display = "none";
        }
    }

    // Add log text to terminal panel
    function addTerminalLine(agent, text, type, timeStr = null) {
        if (!timeStr) {
            const now = new Date();
            timeStr = now.toTimeString().split(' ')[0];
        }
        
        const line = document.createElement("div");
        line.className = "terminal-line";
        
        let colorClass = "";
        if (type === "error") colorClass = "terminal-error";
        
        line.innerHTML = `
            <span class="terminal-time">[${timeStr}]</span>
            <span class="terminal-agent">[${agent}]</span>
            <span class="${colorClass}">${text}</span>
        `;
        
        logTerminal.appendChild(line);
        logTerminal.scrollTop = logTerminal.scrollHeight;
    }

    // 6. CAPTCHA Modals
    function showCaptchaModal(logs) {
        // Find latest screenshot in logs to display in modal
        let captchaImgUrl = "/static/captcha_placeholder.png"; // Fallback placeholder
        let isLoginPause = false;
        
        for (let i = logs.length - 1; i >= 0; i--) {
            if (logs[i].screenshot_url) {
                captchaImgUrl = logs[i].screenshot_url;
            }
            if (logs[i].step_name === "Manual Login Required") {
                isLoginPause = true;
            }
        }
        
        const titleEl = document.getElementById("captchaModalTitle");
        const descEl = document.getElementById("captchaModalDesc");
        
        if (isLoginPause) {
            if (titleEl) titleEl.textContent = "Action Required: Manual Login";
            if (descEl) descEl.textContent = "Please use the physical browser window to log in manually (enter Username, Password, and OTP). Once you are successfully logged in and on the landing search page, click the button below to resume the AI agent.";
        } else {
            if (titleEl) titleEl.textContent = "CAPTCHA Challenge Detected";
            if (descEl) descEl.textContent = "The autonomous browser agent is currently paused. Please solve the captcha in the image below, then click continue.";
        }
        
        captchaImageSrc.src = captchaImgUrl;
        captchaModal.classList.add("active");
    }

    btnSolveCaptcha.addEventListener("click", async () => {
        if (!currentTaskId) return;
        
        addTerminalLine("User", "CAPTCHA solved confirmation sent to system.", "info");
        captchaModal.classList.remove("active");
        
        try {
            const response = await fetch(`/api/tasks/${currentTaskId}/solve-captcha`, {
                method: "POST"
            });
            const data = await response.json();
            if (!data.success) {
                addTerminalLine("SystemError", `Failed to send CAPTCHA resume: ${data.error}`, "error");
            }
        } catch (error) {
            addTerminalLine("SystemError", `Network error sending CAPTCHA resume: ${error.message}`, "error");
        }
    });

    // 7. Results Dashboard
    function displayResults(task) {
        resultsSection.style.display = "block";
        
        // Load GIS Interactive map
        if (task.gis_data && task.gis_data.map_html_url) {
            gisIframe.src = task.gis_data.map_html_url;
        }
        
        // Configure report links
        if (task.metadata.html_report) {
            downloadHtml.href = `/api/storage/reports/${task.metadata.html_report.split(/[/\\]/).pop()}`;
        }
        if (task.metadata.excel_report) {
            downloadExcel.href = `/api/storage/reports/${task.metadata.excel_report.split(/[/\\]/).pop()}`;
        }
        downloadGeoJson.href = `/api/storage/reports/plot_${task.id}_geojson.json`;
    }
});
