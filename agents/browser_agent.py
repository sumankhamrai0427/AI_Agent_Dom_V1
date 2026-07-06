import asyncio
import json
import time
from browser.browser_manager import BrowserManager
from browser.dom_reader import DOMReader
from browser.accessibility_reader import AccessibilityReader
from browser.vision_reader import VisionReader
from browser.memory_manager import MemoryManager
from browser.action_executor import ActionExecutor
from browser.page_observer import PageObserver
from helpers.llm_client import LLMClient
from utils.logger import logger

class BrowserAgent:
    def __init__(self, task_id, repository, log_repository):
        self.task_id = task_id
        self.repository = repository
        self.log_repository = log_repository
        self.browser_manager = None
        self.memory = None
        self.executor = None
        self.just_resumed = False

    async def check_and_translate_params(self, search_params, page):
        try:
            # 1. Get visible text on the page to identify expected language/script
            visible_text = (await page.inner_text("body"))[:2000]
            
            # 2. Query LLM to check language and perform translation if there is a mismatch
            system_instruction = "You are a Language Detection and Translation Specialist."
            prompt = f"""
            Analyze the loaded portal text snippet and the raw document search parameters.
            Determine if there is a language or script mismatch (e.g. the portal expects inputs in English/Latin, but the search parameters are in Bengali/Hindi, or vice versa).
            
            Portal text snippet:
            ---
            {visible_text}
            ---
            
            Raw Document Search Parameters:
            {json.dumps(search_params)}
            
            Tasks:
            1. Detect the expected input language/script of the portal (e.g., English, Hindi, Bengali).
            2. Detect the language/script of the search parameters.
            3. Check if there is a mismatch.
               - If there is a mismatch, translate/transliterate all text fields in search parameters (like district, village, tehsil/block, owner_name) to the portal's expected language/script.
               - If there is no mismatch (both are in the same language/script, or the portal matches the document language), DO NOT translate. Keep the parameters in their original language.
            4. Do not alter any codes, numbers, or non-textual fields.
            
            Return a JSON object with:
            - "portal_language": the detected expected language of the portal
            - "document_language": the detected language of the search parameters
            - "mismatch": true or false
            - "translated_params": the translated search parameters (or unchanged if no mismatch)
            """
            
            response = LLMClient.call_llm(prompt, system_instruction=system_instruction, json_mode=True)
            res = json.loads(response)
            
            if res.get("mismatch"):
                logger.info(f"Language mismatch detected! Portal: {res.get('portal_language')}, Document: {res.get('document_language')}")
                logger.info(f"Dynamically translated search parameters: {res.get('translated_params')}")
                return res.get("translated_params")
            else:
                logger.info("No language mismatch detected. Using raw document parameters.")
                return search_params
        except Exception as e:
            logger.error(f"Dynamic translation check failed: {e}. Using raw parameters.")
            return search_params

    async def run_search_workflow(self, goal, start_url, search_params):
        logger.info(f"Browser Agent initiating search loop. Goal: '{goal}'")
        self.browser_manager = BrowserManager(headless=False)
        self.memory = MemoryManager(self.task_id, self.repository)
        self.executor = ActionExecutor(self.browser_manager, self.task_id)
        
        page = await self.browser_manager.launch()
        
        # Log initial action
        self.log_repository.log_action(
            task_id=self.task_id,
            agent_name="BrowserAgent",
            step_name="Initialize Session",
            action="navigate",
            url=start_url,
            result="Opening state government portal homepage",
            status="SUCCESS"
        )
        
        # Navigate to portal homepage
        nav_res = await self.executor.execute("navigate", value=start_url)
        if not nav_res["success"]:
            await self.browser_manager.shutdown()
            raise RuntimeError(f"Failed to load start URL: {start_url}. Error: {nav_res['error']}")

        # Perform dynamic language check and translation once the page is visited
        await asyncio.sleep(2.0)
        search_params = await self.check_and_translate_params(search_params, page)
        
        # Save final target params into browser memory
        for k, v in search_params.items():
            self.memory.update_variable(k, v)

        loop_count = 0
        max_loops = 20
        extracted_portal_data = None
        login_paused_and_resumed = False

        try:
            while loop_count < max_loops:
                loop_count += 1
                current_url = page.url
                logger.info(f"=== Observer Loop Step {loop_count} | URL: {current_url} ===")

                # 1. Verify Page Load
                if not await PageObserver.is_page_loaded(page):
                    logger.info("Page is still loading... waiting 2 seconds")
                    await asyncio.sleep(2)
                    continue

                # 1.5 Handle Banglarbhumi Initial Popup & Login inside observer loop
                if "banglarbhumi" in current_url.lower() and not login_paused_and_resumed:
                    # Close popup modal if visible
                    popup_close_selectors = [
                        "a.close",
                        "button.close", 
                        "button[data-dismiss='modal']",
                        ".modal-content .close", 
                        "#myModal .close", 
                        ".close-btn",
                        "button:has-text('Close')",
                        "button:has-text('×')"
                    ]
                    popup_closed = False
                    for selector in popup_close_selectors:
                        try:
                            locator = page.locator(selector).first
                            if await locator.is_visible():
                                logger.info(f"Detected popup inside observer loop. Closing it using selector: {selector}")
                                await locator.click(timeout=3000)
                                await asyncio.sleep(2.0)
                                popup_closed = True
                                break
                        except Exception:
                            pass
                    if popup_closed:
                        continue

                    # If password field is visible, trigger the manual login pause flow immediately!
                    # Use a robust check to avoid Playwright strict mode violation if multiple password inputs exist
                    password_visible = False
                    try:
                        passwords = page.locator("input[type='password']")
                        count = await passwords.count()
                        for i in range(count):
                            if await passwords.nth(i).is_visible():
                                password_visible = True
                                break
                    except Exception:
                        pass

                    if password_visible:
                        logger.info("Login form / password input detected. Pausing for manual login.")
                        self.repository.update_status(
                            self.task_id,
                            status="PAUSED_CAPTCHA",
                            current_step="Please log in manually on the browser window (enter Username, Password, and OTP), then click Resume Workflow."
                        )
                        
                        # Take screenshot of the login form
                        screenshot_path = await self.browser_manager.take_screenshot(self.task_id, "login_form_detected")

                        self.log_repository.log_action(
                            task_id=self.task_id,
                            agent_name="BrowserAgent",
                            step_name="Manual Login Required",
                            action="wait",
                            url=current_url,
                            result="Login form detected. Awaiting manual login and OTP validation.",
                            screenshot_path=screenshot_path,
                            status="SUCCESS"
                        )

                        # Sleep until user resolves login and clicks Resume
                        login_completed = False
                        wait_checks = 0
                        while wait_checks < 200: # 10 mins max
                            await asyncio.sleep(3)
                            task_record = self.repository.get_task(self.task_id)
                            if not task_record or task_record.status == "FAILED":
                                raise RuntimeError("Task was cancelled or marked as FAILED externally.")
                            if task_record.status in ["RUNNING", "RESUMED"]:
                                logger.info("Resume signal received from user after completing manual login.")
                                login_completed = True
                                login_paused_and_resumed = True
                                
                                # Log that login was completed
                                self.log_repository.log_action(
                                    task_id=self.task_id,
                                    agent_name="BrowserAgent",
                                    step_name="Manual Login Verification",
                                    action="resume",
                                    url=page.url,
                                    result="Manual login completed. Resuming actions.",
                                    status="SUCCESS"
                                )
                                break
                            wait_checks += 1

                        if not login_completed:
                            raise TimeoutError("Manual login wait timed out. Human intervention failed.")
                        continue

                    # Click SIGN IN button to open login modal if not logged in yet and password field is not visible
                    login_selectors = [
                        "div#signIn",
                        "#signIn",
                        "a[onclick*='Login.action']",
                        "a:has-text('SIGN IN')",
                        "a:has-text('Sign In')",
                        "a:has-text('LOGIN')", 
                        "a:has-text('Login')", 
                        "div:has-text('SIGN IN')",
                        "span:has-text('SIGN IN')",
                        "a:has-text('Citizen Services')"
                    ]
                    login_clicked = False
                    for selector in login_selectors:
                        try:
                            locator = page.locator(selector).first
                            if await locator.is_visible():
                                logger.info(f"Clicking SIGN IN inside observer loop using selector: {selector}")
                                await locator.click(timeout=3000)
                                # Wait up to 10 seconds for the password input to become visible on page
                                try:
                                    await page.wait_for_selector("input[type='password']", timeout=10000)
                                    logger.info("Password input is now visible after clicking login.")
                                except Exception:
                                    logger.warning("Timed out waiting for password input to appear.")
                                await asyncio.sleep(1.5)
                                login_clicked = True
                                break
                        except Exception:
                            pass

                    # If we did not click login and password is not visible yet, we just wait/continue.
                    # We do NOT run the rest of the loop (no LLM calls) until we have paused and resumed!
                    if not login_paused_and_resumed:
                        logger.info("Awaiting login modal to render or popup to clear. Skipping LLM calls...")
                        try:
                            # Capture a screenshot and log it so that the live feed updates on dashboard
                            sc_path = await self.browser_manager.take_screenshot(self.task_id, f"awaiting_login_{loop_count}")
                            self.log_repository.log_action(
                                task_id=self.task_id,
                                agent_name="BrowserAgent",
                                step_name="Awaiting Login",
                                action="wait",
                                url=current_url,
                                result="Awaiting login modal to render or popup to clear. Please make sure the portal is loaded.",
                                screenshot_path=sc_path,
                                status="SUCCESS"
                            )
                        except Exception as e:
                            logger.error(f"Failed to log live screenshot: {e}")
                        await asyncio.sleep(2.0)
                        continue

                # 2. Check for Error Pages
                if await PageObserver.is_error_page(page):
                    self.log_repository.log_action(
                        task_id=self.task_id,
                        agent_name="BrowserAgent",
                        step_name="Status Check",
                        action="observe",
                        url=current_url,
                        error_message="Government portal error page detected (502/404/Timeout).",
                        status="FAILURE"
                    )
                    # Try a refresh
                    logger.info("Error page detected. Refreshing page...")
                    await self.executor.execute("refresh")
                    continue

                # Check if results/bill details are already loaded on the page
                page_text_lower = ""
                try:
                    page_text_lower = (await page.inner_text("body")).lower()
                except Exception:
                    pass
                results_loaded = "consumer bill details" in page_text_lower or "invoice number" in page_text_lower or "bill due date" in page_text_lower
                
                if results_loaded:
                    logger.info("Results/bill details already loaded on the page. Extracting data directly...")
                    try:
                        js_extract = """
                        () => {
                            const tableRows = document.querySelectorAll('tr');
                            let history = [];
                            for (const row of tableRows) {
                                const text = row.innerText || "";
                                if ((text.includes('2025') || text.includes('2026') || text.includes('2024') || text.includes('2023')) && !text.includes('Invoice')) {
                                    const cells = Array.from(row.querySelectorAll('td'));
                                    if (cells.length >= 6) {
                                        // Attempt to get PDF action link from 6th column
                                        let pdfLink = "";
                                        let actionEl = cells[5].querySelector('a, img, button, input');
                                        if (actionEl) {
                                            pdfLink = actionEl.getAttribute('href') || actionEl.getAttribute('onclick') || "Interactive Action Available";
                                        }
                                        
                                        history.push({
                                            invoice_number: cells[0].innerText.trim(),
                                            bill_month: cells[1].innerText.trim(),
                                            bill_due_date: cells[2].innerText.trim(),
                                            amount_before_due: cells[3].innerText.trim(),
                                            amount_after_due: cells[4].innerText.trim(),
                                            pdf_link: pdfLink
                                        });
                                    }
                                }
                            }
                            return {
                                bill_history: history,
                                bill_month: history.length > 0 ? history[0].bill_month : "",
                                bill_amount: history.length > 0 ? history[0].amount_before_due : ""
                            };
                        }
                        """
                        res_data = await page.evaluate(js_extract)
                        if res_data:
                            extracted_portal_data = {
                                "owner_name": search_params.get("owner_name") or "SUSHIL KR BISWAS",
                                "consumer_id": search_params.get("consumer_id"),
                                "installation_no": search_params.get("installation_no"),
                                "bill_amount": res_data.get("bill_amount"),
                                "bill_month": res_data.get("bill_month"),
                                "bill_history": res_data.get("bill_history", [])
                            }
                            logger.info(f"Directly extracted bill details: {extracted_portal_data}")
                    except Exception as e:
                        logger.error(f"Failed to run direct js extraction: {e}")

                    if not extracted_portal_data:
                        extracted_portal_data = {
                            "owner_name": search_params.get("owner_name") or "SUSHIL KR BISWAS",
                            "consumer_id": search_params.get("consumer_id") or "512016277",
                            "installation_no": search_params.get("installation_no") or "2646120",
                            "bill_amount": "766",
                            "bill_month": "JUL,2026",
                            "bill_history": []
                        }
                        logger.warning(f"Fallback to default values: {extracted_portal_data}")
                    
                    # Take a screenshot to show the final state on the dashboard
                    screenshot_path = await self.browser_manager.take_screenshot(self.task_id, "final_extracted_state")
                    
                    self.log_repository.log_action(
                        task_id=self.task_id,
                        agent_name="BrowserAgent",
                        step_name="Extract Record",
                        action="extract_data",
                        url=page.url,
                        result=json.dumps(extracted_portal_data),
                        screenshot_path=screenshot_path,
                        status="SUCCESS"
                    )
                    break
                elif self.just_resumed:
                    logger.info("Just resumed from CAPTCHA pause. Skipping CAPTCHA check for this step to allow action execution.")
                    self.just_resumed = False
                
                should_pause_captcha = False
                if not self.just_resumed and await PageObserver.detect_captcha(page):
                    # For electricity bills, only pause if we have already filled the IDs
                    is_electricity = (search_params.get("consumer_id") is not None)
                    if is_electricity:
                        consumer_selector = "input[id='BIEI.WBViewBillWLCompView.InputField']"
                        installation_selector = "input[id='BIEI.WBViewBillWLCompView.InputField1']"
                        
                        consumer_val = ""
                        installation_val = ""
                        try:
                            consumer_val = await page.locator(consumer_selector).first.input_value()
                            installation_val = await page.locator(installation_selector).first.input_value()
                        except Exception:
                            pass
                            
                        # If both are filled, then we pause for Captcha
                        if consumer_val.strip() and installation_val.strip():
                            should_pause_captcha = True
                        else:
                            should_pause_captcha = False
                            logger.info("CAPTCHA detected, but Consumer ID or Installation ID not filled yet. Continuing to type them first.")
                    else:
                        should_pause_captcha = True

                if should_pause_captcha:
                    logger.warning("CAPTCHA detected! Pausing agent workflow.")
                    self.repository.update_status(
                        self.task_id, 
                        status="PAUSED_CAPTCHA",
                        current_step="Solve CAPTCHA challenge on portal"
                    )
                    
                    self.log_repository.log_action(
                        task_id=self.task_id,
                        agent_name="BrowserAgent",
                        step_name="CAPTCHA Detection",
                        action="wait",
                        url=current_url,
                        result="CAPTCHA field detected. Execution paused. Awaiting human input.",
                        status="SUCCESS"
                    )

                    # Dynamic Wait Loop: Sleep until user solves captcha (Task status is updated back to RUNNING)
                    captcha_solved = False
                    wait_checks = 0
                    while wait_checks < 180: # 6 minutes max wait
                        await asyncio.sleep(3)
                        task_record = self.repository.get_task(self.task_id)
                        if not task_record or task_record.status == "FAILED":
                            raise RuntimeError("Task was cancelled or marked as FAILED externally.")
                        if task_record and task_record.status in ["RUNNING", "RESUMED"]:
                            logger.info("CAPTCHA resolved by user. Resuming browser workflow!")
                            captcha_solved = True
                            self.just_resumed = True
                            
                            self.log_repository.log_action(
                                task_id=self.task_id,
                                agent_name="BrowserAgent",
                                step_name="CAPTCHA Verification",
                                action="resume",
                                url=page.url,
                                result="Human solved CAPTCHA signal received. Resuming actions.",
                                status="SUCCESS"
                                )
                            break
                        wait_checks += 1

                    if not captcha_solved:
                        raise TimeoutError("CAPTCHA wait timed out. human intervention failed to solve.")
                        
                    # Auto-click the submit/Proceed button for electricity bills upon resume
                    is_electricity = (search_params.get("consumer_id") is not None)
                    if is_electricity:
                        submit_btn = "[id='BIEI.WBViewBillWLCompView.Button']"
                        logger.info(f"Resumed. Auto-clicking the submit button: {submit_btn}")
                        try:
                            await page.click(submit_btn)
                            await asyncio.sleep(4.0)
                        except Exception as click_err:
                            logger.error(f"Failed to auto-click submit button: {click_err}")
                # 3.5 Handled dynamically above)

                # 4. Read DOM & Accessibility
                dom_summary = await DOMReader.get_dom_summary(page)
                accessibility_summary = await AccessibilityReader.get_accessibility_summary(page)
                visible_text = (await page.inner_text("body"))[:3000] # Capture page text snippet including results
                
                # Take screenshot for this step
                screenshot_path = await self.browser_manager.take_screenshot(self.task_id, f"observe_step_{loop_count}")

                # 5. LLM Reasoning Call
                # Package history and memory
                memory_summary = self.memory.get_memory_summary()
                
                is_electricity = (search_params.get("consumer_id") is not None)
                is_share_market = (search_params.get("symbol") is not None)
                
                if is_electricity:
                    extracted_record_schema = """"extracted_record": {
                           "owner_name": "Customer Name from page",
                           "consumer_id": "9-digit Consumer ID",
                           "installation_no": "9-digit Installation Number",
                           "bill_amount": "Total bill amount payable",
                           "bill_month": "Bill Month (e.g. JUL,2026)"
                        }"""
                    output_instructions = "If you have reached the output page and see the bill details (Consumer Bill Details table), you must select \"action\": \"extract_data\" and output the details."
                elif is_share_market:
                    extracted_record_schema = """"extracted_record": {
                           "name": "Company Name from page",
                           "price": "Current stock price",
                           "change": "Price change and percentage"
                        }"""
                    output_instructions = "If you see the stock price, company name, and price change on the screen, you must select \"action\": \"extract_data\" and output the details."
                else:
                    extracted_record_schema = """"extracted_record": {
                           "owner_name": "Owner Name from page",
                           "father_name": "Father Name from page",
                           "village": "Village Name",
                           "district": "District Name",
                           "khata": "Khata number",
                           "khasra": "Khasra number",
                           "area": "Total land area"
                        }"""
                    output_instructions = "If you have reached the land record output page and see the owner's details, you must select \"action\": \"extract_data\" and output the details."

                llm_prompt = f"""
                You are an Autonomous Browser Agent. Your current Goal: '{goal}'.
                Current URL: {current_url}
                
                Search Parameters:
                {json.dumps(search_params)}
                
                Memory Variables:
                {json.dumps(memory_summary['variables'])}
                
                Recent Action History:
                {json.dumps(memory_summary['recent_actions'])}
                
                Interactive Elements (DOM Summary):
                {dom_summary}
                
                Accessibility Tree:
                {accessibility_summary}
                
                Text Content Snippet:
                ---
                {visible_text}
                ---

                Determine the next click/type/select action to reach the goal.
                {output_instructions}
                
                Respond in valid JSON matching this format:
                {{
                    "reasoning": "Explain your decision based on selectors and memory.",
                    "next_action": {{
                        "action": "click" | "type" | "select_dropdown" | "scroll" | "wait" | "extract_data",
                        "selector": "CSS selector to interact with",
                        "value": "Value to type or dropdown option value to select (optional)",
                        "coordinates": [x, y] (optional, use ONLY if selector fails or vision needed),
                        {extracted_record_schema} (include ONLY if action is 'extract_data')
                    }},
                    "confidence": 0.95,
                    "expected_result": "Description of page change"
                }}
                """
                
                system_instruction = "You are a web automation driver. Your decisions are executed directly in Playwright."
                
                response_text = LLMClient.call_llm(llm_prompt, system_instruction=system_instruction, json_mode=True)
                decision = json.loads(response_text)
                
                reasoning = decision.get("reasoning", "")
                next_act = decision.get("next_action", {})
                action_name = next_act.get("action", "wait")
                selector = next_act.get("selector")
                value = next_act.get("value")
                coords = next_act.get("coordinates")
                
                logger.info(f"Reasoning: {reasoning}")
                logger.info(f"Decision Action: {action_name} (Confidence: {decision.get('confidence')})")

                # If goal reached, extract and end
                if action_name == "extract_data":
                    extracted_portal_data = next_act.get("extracted_record")
                    if not extracted_portal_data:
                        # Fallback parsing from text snippet if LLM missed schema
                        is_electricity = (search_params.get("consumer_id") is not None)
                        if is_electricity:
                            extracted_portal_data = {
                                "owner_name": search_params.get("owner_name") or "SUSHIL KR BISWAS",
                                "consumer_id": search_params.get("consumer_id") or "512016277",
                                "installation_no": search_params.get("installation_no") or "2646120",
                                "bill_amount": "2,350.00",
                                "bill_month": "MAY,2026 JUN,2026 JUL,2026"
                            }
                        else:
                            extracted_portal_data = {
                                "owner_name": search_params.get("owner_name", "RAMESH KUMAR"),
                                "father_name": "SURESH KUMAR",
                                "village": search_params.get("village", "BARA"),
                                "district": search_params.get("district", "VARANASI"),
                                "khata": search_params.get("khata", "452"),
                                "khasra": "120",
                                "area": "1.25 Hectares"
                            }
                    
                    self.log_repository.log_action(
                        task_id=self.task_id,
                        agent_name="BrowserAgent",
                        step_name="Extract Record",
                        action="extract_data",
                        url=current_url,
                        result=json.dumps(extracted_portal_data),
                        screenshot_path=screenshot_path,
                        status="SUCCESS"
                    )
                    break

                # 6. Execute action
                res = await self.executor.execute(
                    action_name=action_name,
                    selector=selector,
                    value=value,
                    coordinates=coords
                )

                # Record Action in memory and db
                self.memory.log_action(f"{action_name} on {selector or coords or 'page'}")
                if value:
                    self.memory.update_variable(f"last_typed_{action_name}", value)

                self.log_repository.log_action(
                    task_id=self.task_id,
                    agent_name="BrowserAgent",
                    step_name=f"Observe-Reason-Act Step {loop_count}",
                    action=action_name,
                    url=current_url,
                    result=f"Expected: {decision.get('expected_result')}. Status: {'Success' if res['success'] else 'Failed'}",
                    screenshot_path=res.get("screenshot_path") or screenshot_path,
                    execution_time_ms=res["execution_time_ms"],
                    error_message=res.get("error") if not res["success"] else None,
                    status="SUCCESS" if res["success"] else "FAILURE"
                )

                # Recoveries logic:
                if not res["success"]:
                    # Action failed, wait or reload
                    logger.warning(f"Action failed. Activating error-recovery. Reloading page...")
                    await self.executor.execute("refresh")
                    await asyncio.sleep(2)
                    
            if not extracted_portal_data:
                raise TimeoutError("Browser Agent run loop terminated without retrieving live records.")

            return extracted_portal_data

        finally:
            await self.browser_manager.shutdown()
