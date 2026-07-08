document.addEventListener("DOMContentLoaded", () => {
    const chatHistory = document.getElementById("chatHistory");

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
    let selectedAgent = null;

    function addChatMessage(sender, text, isHtml = false) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-message ${sender === 'bot' ? 'bot' : 'user'}`;

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";

        if (isHtml) {
            bubble.innerHTML = text;
        } else {
            bubble.textContent = text;
        }

        msgDiv.appendChild(bubble);
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function showInitialOptions() {
        const optionsHtml = `
            How can I help you?
            <div class="chat-options">
                <button class="chat-option-btn" data-agent="Land Agent">1. Land Related</button>
                <button class="chat-option-btn" data-agent="Electricity Bill Agent">2. Electricity Bill Related</button>
                <button class="chat-option-btn" data-agent="Share Market Agent">3. Share Market Related</button>
                <button class="chat-option-btn" data-agent="Kolkata Municipal Corporation">4. KMC Related</button>
                <button class="chat-option-btn" data-agent="Redbus Travel Agent">5. Redbus Travel Agent</button>
            </div>
        `;
        addChatMessage('bot', optionsHtml, true);

        // Add listeners to new buttons
        const buttons = chatHistory.querySelectorAll(".chat-option-btn");
        buttons.forEach(btn => {
            btn.addEventListener("click", () => handleAgentSelection(btn.getAttribute("data-agent")));
        });
    }

    function handleAgentSelection(agentName) {
        selectedAgent = agentName;
        addChatMessage('user', agentName);

        setTimeout(() => {
            // Share Market Agent: ask for symbol, no file upload needed
            if (agentName === "Share Market Agent") {
                const inputHtml = `
                    Please enter a stock/index symbol for market analysis.
                    <div style="margin-top: 12px; display: flex; flex-direction: column; gap: 10px;">
                        <input id="stockSymbolInput" type="text" placeholder="e.g. RELIANCE, NIFTY50, TCS, INFOSYS"
                            style="width:100%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15);
                            color:#FFF; padding:12px 16px; border-radius:10px; font-family:inherit; font-size:15px; outline:none;
                            transition:all 0.3s ease;" />
                        <button id="submitSymbolBtn"
                            style="background:linear-gradient(135deg,#6366F1 0%,#4F46E5 100%); color:#FFF; border:none;
                            padding:12px; border-radius:10px; font-size:15px; font-weight:700; cursor:pointer;
                            box-shadow:0 4px 15px rgba(99,102,241,0.4); transition:all 0.3s ease;">
                            🔍 Analyse Market
                        </button>
                    </div>
                `;
                addChatMessage('bot', inputHtml, true);
                setTimeout(() => {
                    const btn = document.getElementById("submitSymbolBtn");
                    const inp = document.getElementById("stockSymbolInput");
                    if (btn && inp) {
                        btn.addEventListener("click", () => {
                            const symbol = inp.value.trim().toUpperCase() || "NIFTY50";
                            submitShareMarketTask(symbol);
                        });
                        inp.addEventListener("keydown", (e) => {
                            if (e.key === "Enter") {
                                const symbol = inp.value.trim().toUpperCase() || "NIFTY50";
                                submitShareMarketTask(symbol);
                            }
                        });
                    }
                }, 100);
                return;
            }

            // Kolkata Municipal Corporation: ask for Assessment Number
            if (agentName === "Kolkata Municipal Corporation") {
                const inputHtml = `
                    Please enter the KMC Assessment Number or Ward Number.
                    <div style="margin-top:12px; display:flex; flex-direction:column; gap:10px;">
                        <input id="kmcAssessInput" type="text" placeholder="e.g. WARD-15 / 123456"
                            style="width:100%; background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15);
                            color:#FFF; padding:12px 16px; border-radius:10px; font-family:inherit; font-size:15px; outline:none;" />
                        <button id="submitKmcBtn"
                            style="background:linear-gradient(135deg,#10B981 0%,#059669 100%); color:#FFF; border:none;
                            padding:12px; border-radius:10px; font-size:15px; font-weight:700; cursor:pointer;
                            box-shadow:0 4px 15px rgba(16,185,129,0.4); transition:all 0.3s ease;">
                            🏛️ Search KMC Records
                        </button>
                    </div>
                `;
                addChatMessage('bot', inputHtml, true);
                setTimeout(() => {
                    const btn = document.getElementById("submitKmcBtn");
                    const inp = document.getElementById("kmcAssessInput");
                    if (btn && inp) {
                        btn.addEventListener("click", () => {
                            const assessNo = inp.value.trim() || "N/A";
                            submitKmcTask(assessNo);
                        });
                    }
                }, 100);
                return;
            }

            // Land / Electricity: standard file upload
            const uploadHtml = `
                Please upload the relevant document for the ${agentName}.
                <div class="chat-file-upload">
                    <svg style="width:24px;height:24px;fill:var(--secondary);margin-bottom:8px;" viewBox="0 0 24 24">
                        <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z" />
                    </svg>
                    <p id="chatFileLabel" style="font-size:13px;font-weight:500;color:var(--text-main);">Click or drag file here to upload</p>
                    <input type="file" id="chatDeedFile" name="deed_file" accept=".pdf,.png,.jpg,.jpeg">
                </div>
            `;
            addChatMessage('bot', uploadHtml, true);

            const fileInput = document.getElementById("chatDeedFile");
            const fileLabel = document.getElementById("chatFileLabel");

            fileInput.addEventListener("change", (e) => {
                if (e.target.files.length > 0) {
                    const file = e.target.files[0];
                    fileLabel.textContent = `Selected: ${file.name}`;
                    submitTask(file);
                }
            });
        }, 500);
    }

    // Submit Share Market task (no file needed)
    async function submitShareMarketTask(symbol) {
        addChatMessage('user', `Analysing: ${symbol}`);
        addChatMessage('bot', `Starting Share Market Agent for ${symbol}...`);
        document.getElementById("liveAgentConsole").style.display = "block";
        logTerminal.innerHTML = "";
        loggedTimestamps.clear();
        addTerminalLine("Aetheris", `Initializing Share Market Agent for symbol: ${symbol}`, "info");

        const formData = new FormData();
        formData.append("objective", `Agent Task: share market stock equity analysis for ${symbol}`);
        formData.append("symbol", symbol);

        try {
            const response = await fetch("/api/tasks", { method: "POST", body: formData });
            const data = await response.json();
            if (data.success) {
                currentTaskId = data.task_id;
                consoleTaskId.textContent = `Task ID: #${currentTaskId}`;
                addTerminalLine("Supervisor", `Task created successfully. ID: #${currentTaskId}`, "success");
                resultsSection.style.display = "none";
                await loadTaskHistory();
                fetchTaskState(currentTaskId);
            } else {
                addTerminalLine("SystemError", `Failed to initiate task: ${data.error}`, "error");
            }
        } catch (error) {
            addTerminalLine("SystemError", `API connection failed: ${error.message}`, "error");
        }
    }

    // Submit KMC task
    async function submitKmcTask(assessNo) {
        addChatMessage('user', `KMC Assessment: ${assessNo}`);
        addChatMessage('bot', `Starting Kolkata Municipal Corporation Agent...`);
        document.getElementById("liveAgentConsole").style.display = "block";
        logTerminal.innerHTML = "";
        loggedTimestamps.clear();
        addTerminalLine("Aetheris", `Initializing KMC Agent for assessment: ${assessNo}`, "info");

        const formData = new FormData();
        formData.append("objective", `Agent Task: kolkata municipal corporation kmc property search ${assessNo}`);
        formData.append("assessment_no", assessNo);

        try {
            const response = await fetch("/api/tasks", { method: "POST", body: formData });
            const data = await response.json();
            if (data.success) {
                currentTaskId = data.task_id;
                consoleTaskId.textContent = `Task ID: #${currentTaskId}`;
                addTerminalLine("Supervisor", `Task created successfully. ID: #${currentTaskId}`, "success");
                resultsSection.style.display = "none";
                await loadTaskHistory();
                fetchTaskState(currentTaskId);
            } else {
                addTerminalLine("SystemError", `Failed to initiate task: ${data.error}`, "error");
            }
        } catch (error) {
            addTerminalLine("SystemError", `API connection failed: ${error.message}`, "error");
        }
    }

    async function submitTask(file) {
        addChatMessage('user', `Uploaded: ${file.name}`);
        addChatMessage('bot', `Starting ${selectedAgent} task...`);

        // Show Live Agent Console
        document.getElementById("liveAgentConsole").style.display = "block";

        // Reset console state
        logTerminal.innerHTML = "";
        loggedTimestamps.clear();
        addTerminalLine("Aetheris", `Initializing ${selectedAgent} request payload...`, "info");

        const formData = new FormData();
        formData.append("deed_file", file);
        formData.append("objective", `Agent Task: ${selectedAgent}`);

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
                addChatMessage('bot', `Failed to start task: ${data.error}`);
            }
        } catch (error) {
            addTerminalLine("SystemError", `API connection failed: ${error.message}`, "error");
            addChatMessage('bot', `API connection failed: ${error.message}`);
        }
    }

    // Initialize chatbot
    showInitialOptions();

    // Initialize Socket.IO connection
    const socket = io();

    socket.on("log_added", (log) => {
        if (currentTaskId && log.task_id === currentTaskId) {
            // Use stable key: agent+action+result (same as processLogs) to prevent duplicates
            const resultSnippet = (log.result || log.error_message || log.action || "").slice(0, 60);
            const logSignature = `${log.agent_name}_${log.action}_${resultSnippet}`;
            if (!loggedTimestamps.has(logSignature)) {
                loggedTimestamps.add(logSignature);

                let lineType = "info";
                if (log.status === "FAILURE") lineType = "error";
                else if (log.status === "WARNING") lineType = "warning";
                else if (log.status === "SUCCESS") lineType = "success";

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
            let htmlContent = `
                <div><strong>${doc.utility_type === 'TRAVEL' ? 'Passenger Name' : 'Owner Name'}:</strong> <span style="color:var(--secondary)">${doc.passenger_name || doc.owner_name || 'N/A'}</span></div>
                ${doc.utility_type !== 'TRAVEL' ? `<div><strong>Father/Spouse:</strong> <span style="color:#FFF">${doc.father_name || 'N/A'}</span></div>` : ''}
                <div><strong>Utility Type:</strong> <span style="color:#FFF;text-transform:uppercase">${doc.utility_type || 'LAND'}</span></div>
                ${doc.utility_type !== 'TRAVEL' ? `<div><strong>Village Name:</strong> <span style="color:#FFF">${doc.village || 'N/A'}</span></div>` : ''}
            `;

            if (doc.utility_type === 'ELECTRICITY') {
                htmlContent += `
                <div><strong>Consumer ID:</strong> <span style="color:var(--secondary)">${doc.consumer_id || 'N/A'}</span></div>
                <div><strong>Installation ID:</strong> <span style="color:#FFF">${doc.installation_no || 'N/A'}</span></div>
                <div><strong>Bill Amount:</strong> <span style="color:#FFF">${doc.bill_amount || 'N/A'}</span></div>
                `;
            } else if (doc.utility_type === 'SHARE_MARKET') {
                htmlContent += `
                <div><strong>Symbol:</strong> <span style="color:var(--secondary)">${doc.symbol || 'N/A'}</span></div>
                `;
            } else if (doc.utility_type === 'TRAVEL') {
                htmlContent += `
                <div><strong>Source:</strong> <span style="color:var(--secondary)">${doc.source || 'N/A'}</span></div>
                <div><strong>Destination:</strong> <span style="color:#FFF">${doc.destination || 'N/A'}</span></div>
                <div><strong>Date of Travel:</strong> <span style="color:#FFF">${doc.travel_date || 'N/A'}</span></div>
                `;
            } else {
                htmlContent += `
                <div><strong>Khata Number:</strong> <span style="color:var(--secondary)">${doc.khata || 'N/A'}</span></div>
                <div><strong>Khasra/Plot:</strong> <span style="color:#FFF">${doc.khasra || doc.survey_no || 'N/A'}</span></div>
                <div><strong>Area:</strong> <span style="color:#FFF">${doc.area || 'N/A'}</span></div>
                `;
            }

            deedPreviewContent.innerHTML = htmlContent;
        } else if (deedPreviewCard) {
            deedPreviewCard.style.display = "none";
        }
    }

    // 5. Render live logs and browser images
    function processLogs(logs) {
        if (!logs || logs.length === 0) return;

        let latestScreenshot = null;

        logs.forEach(log => {
            // Use stable key matching the socket.io handler (no timestamp)
            const resultSnippet = (log.result || log.error_message || log.action || "").slice(0, 60);
            const logSignature = `${log.agent_name}_${log.action}_${resultSnippet}`;

            if (!loggedTimestamps.has(logSignature)) {
                loggedTimestamps.add(logSignature);

                const timeParts = log.timestamp.split(" ");
                const timeStr = timeParts.length > 1 ? timeParts[1] : timeParts[0];
                let lineType = "info";
                if (log.status === "FAILURE") lineType = "error";
                else if (log.status === "WARNING") lineType = "warning";
                else if (log.status === "SUCCESS") lineType = "success";

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

        // GIS map removed per user request

        // Configure report links
        const viewHtml = document.getElementById('viewHtml');
        if (task.metadata.html_report) {
            const filename = task.metadata.html_report.split(/[/\\]/).pop();
            if (viewHtml) {
                viewHtml.href = `/api/storage/reports/${filename}`;
                viewHtml.style.pointerEvents = "auto";
                viewHtml.style.opacity = "1";
            }
            if (downloadHtml) {
                downloadHtml.href = `/api/storage/download/reports/${filename}`;
                downloadHtml.style.pointerEvents = "auto";
                downloadHtml.style.opacity = "1";
            }
        } else {
            if (viewHtml) {
                viewHtml.href = "#";
                viewHtml.style.pointerEvents = "none";
                viewHtml.style.opacity = "0.5";
            }
            if (downloadHtml) {
                downloadHtml.href = "#";
                downloadHtml.style.pointerEvents = "none";
                downloadHtml.style.opacity = "0.5";
            }
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

        const geojsonCard = document.getElementById("geojsonCard");
        const isNonLand = task.document && (task.document.utility_type === 'ELECTRICITY' || task.document.utility_type === 'SHARE_MARKET' || task.document.utility_type === 'TRAVEL');

        if (geojsonCard) {
            geojsonCard.style.display = isNonLand ? 'none' : 'flex';
        }

        if (task.gis_data && !isNonLand) {
            downloadGeoJson.href = `/api/storage/reports/plot_${task.id}_geojson.json`;
            downloadGeoJson.style.pointerEvents = "auto";
            downloadGeoJson.style.opacity = "1";
        } else {
            downloadGeoJson.href = "#";
            downloadGeoJson.style.pointerEvents = "none";
            downloadGeoJson.style.opacity = "0.5";
        }

        // Handle AI Insights section
        const insightsSectionWrapper = document.getElementById("insightsSectionWrapper");
        const aiSectionTitle = document.getElementById("aiSectionTitle");
        const aiConsumptionTitle = document.getElementById("aiConsumptionTitle");
        const billingTrendTitle = document.getElementById("billingTrendTitle");
        const billGraphContainer = document.getElementById("billGraphContainer");

        if (task.metadata && task.metadata.ai_analysis && !task.metadata.ai_analysis.insufficient_data) {
            if (insightsSectionWrapper) insightsSectionWrapper.style.display = "block";

            // Adjust titles for Share Market
            const isShareMarket = task.document && task.document.utility_type === "SHARE_MARKET";
            const isTravel = task.document && task.document.utility_type === "TRAVEL";
            if (isShareMarket) {
                if (aiSectionTitle) aiSectionTitle.innerHTML = `<svg style="width:20px;height:20px;fill:var(--accent)" viewBox="0 0 24 24"><path d="M16 11.78L20.24 4.45L21.97 5.45L16.74 14.5L10.23 10.75L5.46 19H22V21H2V3H4V17.54L11.27 7.5L16 11.78Z"/></svg> Share Market Analysis & Real-time Trends`;
                if (aiConsumptionTitle) aiConsumptionTitle.innerText = "Market Analysis";
                if (billingTrendTitle) billingTrendTitle.innerText = "Market Trend Graph";
            } else if (isTravel) {
                if (aiSectionTitle) aiSectionTitle.innerHTML = `<svg style="width:20px;height:20px;fill:var(--accent)" viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg> Travel Assistant Analysis`;
                if (aiConsumptionTitle) aiConsumptionTitle.innerText = "Best Travel Options";
                if (billingTrendTitle) billingTrendTitle.innerText = "Price Comparison";
            } else {
                if (aiSectionTitle) aiSectionTitle.innerHTML = `<svg style="width:20px;height:20px;fill:var(--accent)" viewBox="0 0 24 24"><path d="M15,21H9V20H15V21M19,8H17.73C17.38,5.68 15.39,4 13,4C12.33,4 11.68,4.13 11.08,4.37C10.58,3.5 9.61,3 8.5,3C6.7,3 5.25,4.34 5.04,6.08C3.28,6.58 2,8.19 2,10A4,4 0 0,0 6,14H7.17C7.6,16.29 9.6,18 12,18C14.4,18 16.4,16.29 16.83,14H19A4,4 0 0,0 23,10A4,4 0 0,0 19,8M12,16A2,2 0 1,1 14,14A2,2 0 0,1 12,16Z" /></svg> Audit Results & Geographic Information Systems`;
                if (aiConsumptionTitle) aiConsumptionTitle.innerText = "AI Consumption Analysis";
                if (billingTrendTitle) billingTrendTitle.innerText = "Billing Trend Graph";
            }

            const aiData = task.metadata.ai_analysis;

            // Set Summary Text
            const aiSummaryText = document.getElementById("aiSummaryText");
            if (aiSummaryText) {
                if (isTravel) {
                    aiSummaryText.innerHTML = `
                        <p style="margin-top: 0;"><b>Summary:</b> ${aiData.summary || "No summary available."}</p>
                        <p style="margin-bottom: 0;"><b>Recommendation:</b> ${aiData.recommendation || "No recommendations available."}</p>
                    `;
                } else {
                    aiSummaryText.innerHTML = `
                        <p style="margin-top: 0;"><b>Summary:</b> ${aiData.summary || "No summary available."}</p>
                        <p style="margin-bottom: 0;"><b>Recommendation for Next Month:</b> ${aiData.recommendation || "No recommendations available."}</p>
                    `;
                }
            }

            // Render Graph
            const labels = aiData.chart_labels ? [...aiData.chart_labels].reverse() : [];
            const data = aiData.chart_data ? [...aiData.chart_data].reverse() : [];

            if (labels.length === 0 || data.length === 0) {
                if (billGraphContainer) billGraphContainer.style.display = "none";
                if (billingTrendTitle) billingTrendTitle.style.display = "none";
            } else {
                if (billGraphContainer) billGraphContainer.style.display = "block";
                if (billingTrendTitle) billingTrendTitle.style.display = "block";
            }

            const ctx = document.getElementById('billGraph').getContext('2d');
            if (window.billChart) {
                window.billChart.destroy();
            }
            window.billChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Bill Amount (₹)',
                        data: data,
                        backgroundColor: 'rgba(56, 189, 248, 0.5)',
                        borderColor: 'rgba(56, 189, 248, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: '#94a3b8' },
                            grid: { color: 'rgba(255,255,255,0.1)' }
                        },
                        x: {
                            ticks: { color: '#94a3b8' },
                            grid: { color: 'rgba(255,255,255,0.1)' }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#f8fafc' } }
                    }
                }
            });

        } else {
            if (insightsSectionWrapper) insightsSectionWrapper.style.display = "none";
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
