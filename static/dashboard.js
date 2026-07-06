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
    let loggedTimestamps = new Set();

    // 1. File Upload styling update
    deedFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            fileLabel.textContent = `File Selected: ${e.target.files[0].name}`;
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
        const state = formData.get("state") || "Auto-detect";
        const objective = `Deed Audit: Run autonomous ownership verification audit for uploaded deed (State: ${state}).`;
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
                
                // Refresh task list sidebar
                await loadTaskHistory();
                
                // Load initial task state once
                fetchTaskState(currentTaskId);
            } else {
                addTerminalLine("SystemError", `Failed to initiate task: ${data.error}`, "error");
            }
        } catch (error) {
            addTerminalLine("SystemError", `API connection failed: ${error.message}`, "error");
        }
    });

    // Initialize Socket.IO connection
    const socket = io();

    socket.on("log_added", (log) => {
        if (currentTaskId && log.task_id === currentTaskId) {
            const logSignature = `${log.timestamp || new Date().toISOString()}_${log.agent_name}_${log.action}`;
            if (!loggedTimestamps.has(logSignature)) {
                loggedTimestamps.add(logSignature);
                
                let lineType = "info";
                if (log.status === "FAILURE") lineType = "error";
                else if (log.status === "WARNING") lineType = "warning";
                
                const msg = log.result || log.error_message || `Executing: ${log.action}`;
                addTerminalLine(log.agent_name, msg, lineType);
            }
            if (log.screenshot_url) {
                liveViewImg.src = log.screenshot_url;
                liveViewImg.style.display = "block";
                livePlaceholder.style.display = "none";
            }
            if (log.url) {
                document.getElementById("browserUrlText").textContent = log.url;
            }
        }
    });

    socket.on("task_updated", async (update) => {
        if (update.task_id) {
            // Reload history list status changes in background
            await loadTaskHistory();
            
            if (currentTaskId && update.task_id === currentTaskId) {
                fetchTaskState(currentTaskId);
            }
        }
    });

    // 3. Fetch Task State
    async function fetchTaskState(taskId) {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            const data = await response.json();
            
            if (data.success) {
                const task = data.task;
                updateUIStatus(task);
                processLogs(task.logs);
                
                if (task.status === "COMPLETED") {
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
                    addTerminalLine("Supervisor", `Workflow terminated with error: ${task.error_message}`, "error");
                }
            }
        } catch (err) {
            console.error("Fetch state error:", err);
        }
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

        // Update workflow pipeline progress bar and labels
        updatePipelineTracker(task);
        
        // Update mock browser address text URL
        updateBrowserUrl(task);

        // If task has extracted document, render the deed preview
        const deedPreviewCard = document.getElementById("deedPreviewCard");
        const deedPreviewContent = document.getElementById("deedPreviewContent");
        
        if (task.extracted_document && deedPreviewCard && deedPreviewContent) {
            deedPreviewCard.style.display = "block";
            const doc = task.extracted_document;
            deedPreviewContent.innerHTML = `
                <div><strong>Owner Name:</strong> <span style="color:var(--secondary)">${doc.owner_name || 'N/A'}</span></div>
                <div><strong>Father/Spouse:</strong> <span style="color:#FFF">${doc.father_name || 'N/A'}</span></div>
                <div><strong>Utility Type:</strong> <span style="color:#FFF;text-transform:uppercase">${doc.utility_type || 'N/A'}</span></div>
                <div><strong>Village Name:</strong> <span style="color:#FFF">${doc.village || 'N/A'}</span></div>
                <div><strong>Khata Number:</strong> <span style="color:var(--secondary)">${doc.khata || 'N/A'}</span></div>
                <div><strong>Khasra/Plot:</strong> <span style="color:#FFF">${doc.khasra || doc.survey_no || 'N/A'}</span></div>
                <div><strong>Area:</strong> <span style="color:#FFF">${doc.area || 'N/A'}</span></div>
                <div><strong>Consumer ID:</strong> <span style="color:var(--secondary)">${doc.consumer_id || 'N/A'}</span></div>
                <div><strong>Installation ID:</strong> <span style="color:#FFF">${doc.installation_no || 'N/A'}</span></div>
                <div><strong>Bill Amount:</strong> <span style="color:#FFF">${doc.bill_amount || 'N/A'}</span></div>
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
                
                const timeParts = log.timestamp.split(" ");
                const timeStr = timeParts.length > 1 ? timeParts[1] : timeParts[0];
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
        else if (type === "warning") colorClass = "terminal-warning";
        else if (type === "success") colorClass = "terminal-success";
        
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
        } else {
            gisIframe.src = "";
        }
        
        // Configure report links
        if (task.metadata.html_report) {
            downloadHtml.href = `/api/storage/reports/${task.metadata.html_report.split(/[/\\]/).pop()}`;
            downloadHtml.style.pointerEvents = "auto";
            downloadHtml.style.opacity = "1";
        } else {
            downloadHtml.href = "#";
            downloadHtml.style.pointerEvents = "none";
            downloadHtml.style.opacity = "0.5";
        }
        
        if (task.metadata.excel_report) {
            downloadExcel.href = `/api/storage/reports/${task.metadata.excel_report.split(/[/\\]/).pop()}`;
            downloadExcel.style.pointerEvents = "auto";
            downloadExcel.style.opacity = "1";
        } else {
            downloadExcel.href = "#";
            downloadExcel.style.pointerEvents = "none";
            downloadExcel.style.opacity = "0.5";
        }
        
        if (task.gis_data) {
            downloadGeoJson.href = `/api/storage/reports/plot_${task.id}_geojson.json`;
            downloadGeoJson.style.pointerEvents = "auto";
            downloadGeoJson.style.opacity = "1";
        } else {
            downloadGeoJson.href = "#";
            downloadGeoJson.style.pointerEvents = "none";
            downloadGeoJson.style.opacity = "0.5";
        }
    }

    // 8. Dynamic Sidebar Audit History Loader
    async function loadTaskHistory() {
        try {
            const response = await fetch("/api/tasks");
            const data = await response.json();
            if (data.success && Array.isArray(data.tasks)) {
                const historyList = document.getElementById("auditHistoryList");
                if (historyList) {
                    if (data.tasks.length === 0) {
                        historyList.innerHTML = `<p style="color: var(--text-muted); font-size: 13px; text-align: center; margin-top: 20px;">No audits found</p>`;
                        return;
                    }
                    
                    historyList.innerHTML = "";
                    // Sort descending by ID
                    const sortedTasks = data.tasks.sort((a, b) => b.id - a.id);
                    
                    sortedTasks.forEach(task => {
                        const item = document.createElement("div");
                        item.className = "history-item";
                        if (currentTaskId === task.id) {
                            item.classList.add("active");
                        }
                        
                        let badgeClass = "badge-pending";
                        if (task.status === "RUNNING") badgeClass = "badge-running";
                        else if (task.status === "COMPLETED") badgeClass = "badge-completed";
                        else if (task.status === "FAILED") badgeClass = "badge-failed";
                        else if (task.status === "PAUSED_CAPTCHA") badgeClass = "badge-captcha";
                        
                        const stateText = task.metadata && task.metadata.state ? task.metadata.state : "WB";
                        const desc = task.objective ? task.objective.replace("Deed Audit: Run autonomous ownership verification audit for uploaded deed in state: ", "") : "Autonomous Audit";
                        
                        item.innerHTML = `
                            <div class="history-details">
                                <div class="history-id">Audit Run #${task.id} <span style="font-size: 10px; color: var(--primary); margin-left: 5px; font-weight:700;">[${stateText}]</span></div>
                                <div class="history-desc" title="${task.objective}">${desc}</div>
                            </div>
                            <span class="status-badge ${badgeClass}" style="font-size: 9px; padding: 3px 8px; border-radius:4px;">${task.status}</span>
                        `;
                        
                        item.addEventListener("click", () => {
                            selectTask(task.id);
                        });
                        historyList.appendChild(item);
                    });
                }
            }
        } catch (err) {
            console.error("Failed to load task history:", err);
        }
    }

    // Select and load a task from history
    function selectTask(taskId) {
        currentTaskId = taskId;
        
        // Highlight active list item
        const items = document.querySelectorAll(".history-item");
        items.forEach(item => {
            const idEl = item.querySelector(".history-id");
            if (idEl && idEl.textContent.includes(`Audit Run #${taskId} `)) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
        
        consoleTaskId.textContent = `Task ID: #${taskId}`;
        logTerminal.innerHTML = "";
        loggedTimestamps.clear();
        
        // Reset browser frame and progress bar
        liveViewImg.style.display = "none";
        livePlaceholder.style.display = "block";
        document.getElementById("browserUrlText").textContent = "about:blank";
        resultsSection.style.display = "none";
        
        // Fetch specific task state
        fetchTaskState(taskId);
    }

    // Pipeline Tracker Logic
    function updatePipelineTracker(task) {
        const progressBar = document.getElementById("pipelineProgressBar");
        const progressText = document.getElementById("pipelineProgressText");
        
        const lblStepDoc = document.getElementById("lblStepDoc");
        const lblStepVal = document.getElementById("lblStepVal");
        const lblStepSearch = document.getElementById("lblStepSearch");
        const lblStepVerify = document.getElementById("lblStepVerify");
        const lblStepReport = document.getElementById("lblStepReport");
        
        const labels = [lblStepDoc, lblStepVal, lblStepSearch, lblStepVerify, lblStepReport];
        
        labels.forEach(lbl => {
            if (lbl) {
                lbl.classList.remove("active");
                lbl.classList.remove("completed");
            }
        });
        
        let percent = 0;
        let activeIdx = -1;
        
        if (task.status === "COMPLETED") {
            percent = 100;
            activeIdx = 5;
        } else if (task.status === "FAILED") {
            percent = 100;
            activeIdx = 5;
        } else {
            const step = (task.current_step || "").toLowerCase();
            
            if (step.includes("extract")) {
                percent = 15;
                activeIdx = 0;
            } else if (step.includes("validate") || step.includes("standard")) {
                percent = 35;
                activeIdx = 1;
            } else if (step.includes("search") || step.includes("portal") || step.includes("captcha") || step.includes("browser")) {
                percent = 60;
                activeIdx = 2;
            } else if (step.includes("verify") || step.includes("comparison") || step.includes("findings")) {
                percent = 80;
                activeIdx = 3;
            } else if (step.includes("report") || step.includes("gis") || step.includes("finalize")) {
                percent = 95;
                activeIdx = 4;
            } else {
                percent = 5;
                activeIdx = 0;
            }
        }
        
        if (progressBar) progressBar.style.width = `${percent}%`;
        if (progressText) progressText.textContent = `${percent}% Completed`;
        
        labels.forEach((lbl, idx) => {
            if (lbl) {
                if (idx < activeIdx) {
                    lbl.classList.add("completed");
                } else if (idx === activeIdx) {
                    lbl.classList.add("active");
                }
            }
        });
    }

    // Sync address bar
    function updateBrowserUrl(task) {
        const browserUrlText = document.getElementById("browserUrlText");
        if (!browserUrlText) return;
        
        let url = "about:blank";
        const state = (task.metadata && task.metadata.state ? task.metadata.state : "").toUpperCase();
        
        if (task.logs && task.logs.length > 0) {
            for (let i = 0; i < task.logs.length; i++) {
                const log = task.logs[i];
                if (log.url) {
                    url = log.url;
                    break;
                }
            }
        }
        
        if (url === "about:blank") {
            if (state === "WB") {
                url = "https://portal.wbsedcl.in/webdynpro/resources/wbsedcl/viewbillwl/WBViewBillWL";
            } else if (state === "UP") {
                url = "https://upbhunaksha.gov.in/";
            } else if (state === "BIHAR") {
                url = "https://biharbhumi.bihar.gov.in/";
            }
        }
        
        browserUrlText.textContent = url;
    }

    // Initialize Dashboard
    async function initDashboard() {
        await loadTaskHistory();
        
        // Auto-select the latest task if available
        const firstItem = document.querySelector(".history-item");
        if (firstItem) {
            firstItem.click();
        }
    }
    
    initDashboard();
});
