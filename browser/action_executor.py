import asyncio
import time
import os
from utils.logger import logger

class ActionExecutor:
    def __init__(self, browser_manager, task_id=None):
        self.browser_manager = browser_manager
        self.task_id = task_id

    async def _draw_cursor(self, page, x, y):
        """Draws a visual cursor (red dot) at the specified coordinates on the page."""
        js_draw = f"""
        () => {{
            const oldCursor = document.getElementById('agent-visual-cursor');
            if (oldCursor) oldCursor.remove();

            const cursor = document.createElement('div');
            cursor.id = 'agent-visual-cursor';
            cursor.style.position = 'fixed';
            cursor.style.left = '{x - 10}px';
            cursor.style.top = '{y - 10}px';
            cursor.style.width = '20px';
            cursor.style.height = '20px';
            cursor.style.borderRadius = '50%';
            cursor.style.backgroundColor = 'rgba(255, 0, 0, 0.7)';
            cursor.style.border = '2px solid white';
            cursor.style.boxShadow = '0 0 10px rgba(0,0,0,0.5)';
            cursor.style.zIndex = '999999';
            cursor.style.pointerEvents = 'none';
            cursor.style.transition = 'transform 0.1s ease-out';
            
            document.body.appendChild(cursor);

            setTimeout(() => {{
                cursor.style.transform = 'scale(0.5)';
                cursor.style.backgroundColor = 'rgba(255, 0, 0, 0.9)';
            }}, 50);

            setTimeout(() => {{
                cursor.style.opacity = '0';
                setTimeout(() => cursor.remove(), 300);
            }}, 1500);
        }}
        """
        try:
            await page.evaluate(js_draw)
        except Exception as e:
            logger.debug(f"Failed to draw visual cursor: {e}")

    async def execute(self, action_name, selector=None, value=None, coordinates=None, timeout_ms=5000):
        """Executes an action and returns (success, error_message, screenshot_path, time_ms)."""
        start_time = time.time()
        success = False
        error_msg = ""
        screenshot_path = None
        
        # Normalize selector with dots in ID to bypass CSS syntax limitations (e.g. #BIEI.WBViewBillWLCompView.InputField -> [id='BIEI.WBViewBillWLCompView.InputField'])
        if selector and "#" in selector and "." in selector.split("#", 1)[1]:
            tag, id_part = selector.split("#", 1)
            selector = f"{tag}[id='{id_part}']" if tag else f"[id='{id_part}']"
            logger.info(f"Normalized selector with dots in ID to: '{selector}'")
            
        page = await self.browser_manager.get_page()
        action_name = action_name.lower()
        
        logger.info(f"Executing Action: '{action_name}' | Selector: '{selector}' | Value: '{value}' | Coords: {coordinates}")

        try:
            if action_name == "navigate":
                if not value:
                    raise ValueError("Navigation URL value is required.")
                await page.goto(value, wait_until="domcontentloaded", timeout=60000)
                success = True
                
            elif action_name == "click":
                if coordinates:
                    await self._draw_cursor(page, coordinates[0], coordinates[1])
                    # Click by vision coordinates
                    await page.mouse.click(coordinates[0], coordinates[1])
                elif selector:
                    await page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
                    try:
                        box = await page.locator(selector).first.bounding_box()
                        if box:
                            await self._draw_cursor(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    except Exception:
                        pass
                    await page.click(selector)
                else:
                    raise ValueError("Click action requires either selector or coordinates.")
                success = True
                
            elif action_name == "double_click":
                if selector:
                    await page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
                    try:
                        box = await page.locator(selector).first.bounding_box()
                        if box:
                            await self._draw_cursor(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    except Exception:
                        pass
                    await page.dblclick(selector)
                elif coordinates:
                    await self._draw_cursor(page, coordinates[0], coordinates[1])
                    await page.mouse.dblclick(coordinates[0], coordinates[1])
                else:
                    raise ValueError("Double click requires selector or coordinates.")
                success = True
                
            elif action_name == "type":
                if not selector:
                    raise ValueError("Type action requires a selector.")
                await page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
                try:
                    box = await page.locator(selector).first.bounding_box()
                    if box:
                        await self._draw_cursor(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                except Exception:
                    pass
                # Focus and fill using Playwright fill API
                await page.focus(selector)
                await page.locator(selector).fill(str(value))
                # Trigger dynamic framework change/input notifications
                await page.locator(selector).evaluate("el => el.dispatchEvent(new Event('input', { bubbles: true }))")
                success = True
                
            elif action_name == "select_dropdown":
                if not selector:
                    raise ValueError("Select action requires a selector.")
                await page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
                try:
                    box = await page.locator(selector).first.bounding_box()
                    if box:
                        await self._draw_cursor(page, box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                except Exception:
                    pass
                
                # Check tag name
                tag_name = ""
                try:
                    tag_name = await page.locator(selector).first.evaluate("el => el.tagName.toLowerCase()")
                except Exception:
                    pass
                
                if tag_name == "select":
                    # Try selecting by label (visible text) first, as models usually output labels (e.g. "HOOGLY", "Patna")
                    try:
                        await page.select_option(selector, label=str(value))
                    except Exception as e1:
                        # Fallback to selecting by value attribute
                        try:
                            await page.select_option(selector, value=str(value))
                        except Exception as e2:
                             # Fallback to case-insensitive option matching using evaluate
                             js_select = f"""
                             (sel, val) => {{
                                 const selectEl = document.querySelector(sel);
                                 if (!selectEl) return false;
                                 const options = Array.from(selectEl.options);
                                 const searchVal = val.toUpperCase().trim();
                                 const match = options.find(opt => {{
                                     const optText = opt.text.trim().toUpperCase();
                                     const optVal = opt.value.trim().toUpperCase();
                                     return optText === searchVal || 
                                            optVal === searchVal ||
                                            (searchVal.length >= 2 && (optText.includes(searchVal) || optVal.includes(searchVal)));
                                 }});
                                 if (match) {{
                                     selectEl.value = match.value;
                                     selectEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                     return true;
                                 }}
                                 return false;
                             }}
                             """
                             res = await page.evaluate(js_select, [selector, str(value)])
                             if not res:
                                 raise RuntimeError(f"Could not select option '{value}' by label or value. Error: {e1} | {e2}")
                else:
                    # Non-native select dropdown (e.g., Angular <mat-select> or custom combobox)
                    logger.info(f"Custom dropdown detected (<{tag_name}>). Simulating click and option selection.")
                    # Click the dropdown selector to open the options overlay
                    await page.click(selector)
                    await asyncio.sleep(0.8) # Wait for overlay animation to complete
                    
                    # Try to locate the option with matching text
                    option_selectors = [
                        f"mat-option:has-text('{value}')",
                        f"[role='option']:has-text('{value}')",
                        f"mat-option:has-text('{str(value).upper()}')",
                        f"[role='option']:has-text('{str(value).upper()}')",
                        f"li:has-text('{value}')",
                        f"div:has-text('{value}')"
                    ]
                    
                    option_clicked = False
                    for opt_sel in option_selectors:
                        try:
                            opt_locator = page.locator(opt_sel).first
                            # Wait up to 1 second for each possible selector to be visible
                            if await opt_locator.is_visible():
                                await opt_locator.click(timeout=1500)
                                option_clicked = True
                                break
                        except Exception:
                            pass
                    
                    if not option_clicked:
                        try:
                            # Read all visible options from the overlay
                            option_elements = await page.locator("mat-option, [role='option'], li, option").all()
                            available_options = []
                            option_map = []
                            for opt in option_elements:
                                text = await opt.inner_text()
                                text = text.strip()
                                if text:
                                    available_options.append(text)
                                    option_map.append((text, opt))
                                    
                            if available_options:
                                # Try programmatic matching first (exact, substring, or numerical code match)
                                matched_opt_pair = None
                                val_str = str(value).strip().upper()
                                
                                for text, opt in option_map:
                                    opt_upper = text.upper()
                                    # 1. Exact match
                                    if opt_upper == val_str:
                                        matched_opt_pair = (text, opt)
                                        break
                                    # 2. Code match: check if the search value is a number (e.g., "191") and is present in the option text
                                    if val_str.isdigit() and len(val_str) >= 2:
                                        import re
                                        if re.search(r'\b' + re.escape(val_str) + r'\b', opt_upper) or val_str in opt_upper:
                                            matched_opt_pair = (text, opt)
                                            break
                                    # 3. Simple containment match
                                    if val_str in opt_upper or opt_upper in val_str:
                                        matched_opt_pair = (text, opt)
                                
                                if matched_opt_pair:
                                    logger.info(f"Programmatic match found for '{value}': '{matched_opt_pair[0]}'")
                                    await matched_opt_pair[1].click(timeout=1500)
                                    option_clicked = True
                                else:
                                    # Fallback to LLM fuzzy matching
                                    logger.info(f"Fuzzy LLM matching option '{value}' against: {available_options}")
                                    sys_instruction = (
                                        "You are a translation and matching specialist. Your job is to select the option "
                                        "from the given list of options that corresponds to the target English location/name. "
                                        "Respond ONLY with the exact text of the matched option from the list. "
                                        "If no options match, return 'None'."
                                    )
                                    prompt = f"Target English Name: '{value}'\nAvailable Options List: {available_options}"
                                    
                                    from helpers.llm_client import LLMClient
                                    match_res = LLMClient.call_llm(prompt, system_instruction=sys_instruction).strip()
                                    match_res = match_res.replace('"', '').replace("'", "").strip()
                                    logger.info(f"LLM determined fuzzy match for '{value}': '{match_res}'")
                                    
                                    if match_res and match_res.lower() != 'none':
                                        for opt_text, opt in option_map:
                                            if match_res.upper() in opt_text.upper() or opt_text.upper() in match_res.upper():
                                                await opt.click(timeout=1500)
                                                option_clicked = True
                                                break
                        except Exception as ex:
                            logger.warning(f"Fuzzy LLM dropdown option matching failed: {ex}")

                    if not option_clicked:
                        # Try case-insensitive text match on any matching element in body
                        try:
                            js_click_option = f"""
                            (val) => {{
                                const items = Array.from(document.querySelectorAll('mat-option, [role="option"], li, span'));
                                const match = items.find(el => el.innerText.trim().toUpperCase() === val.toUpperCase());
                                if (match) {{
                                    match.click();
                                    return true;
                                }}
                                return false;
                            }}
                            """
                            res = await page.evaluate(js_click_option, str(value))
                            if not res:
                                raise RuntimeError(f"Could not click custom option '{value}' inside dropdown overlay.")
                        except Exception as e:
                            raise RuntimeError(f"Custom option click failed: {e}")
                success = True
                
            elif action_name == "scroll":
                if value == "down":
                    await page.evaluate("window.scrollBy(0, 400);")
                elif value == "up":
                    await page.evaluate("window.scrollBy(0, -400);")
                elif selector:
                    # Specific selector scroll
                    await page.locator(selector).scroll_into_view_if_needed()
                else:
                    # Default fallback
                    await page.evaluate("window.scrollBy(0, 400);")
                success = True
                
            elif action_name == "upload_file":
                if not selector or not value or not os.path.exists(value):
                    raise ValueError("Upload file requires selector and a valid file path.")
                async with page.expect_file_chooser() as fc_info:
                    await page.click(selector)
                file_chooser = await fc_info.value
                await file_chooser.set_files(value)
                success = True
                
            elif action_name == "download_file":
                if not selector:
                    raise ValueError("Download file requires target click selector.")
                async with page.expect_download(timeout=timeout_ms * 3) as download_info:
                    await page.click(selector)
                download = await download_info.value
                # Save file to storage reports
                download_dir = "storage/reports"
                os.makedirs(download_dir, exist_ok=True)
                download_path = os.path.join(download_dir, download.suggested_filename)
                await download.save_as(download_path)
                # Set value return to save the filepath
                value = download_path
                success = True
                
            elif action_name == "back":
                await page.go_back()
                success = True
                
            elif action_name == "refresh":
                await page.reload()
                success = True
                
            elif action_name == "wait":
                wait_sec = float(value) if value and str(value).replace('.','',1).isdigit() else 2.0
                await asyncio.sleep(wait_sec)
                success = True
                
            elif action_name == "hover":
                if selector:
                    await page.hover(selector)
                elif coordinates:
                    await page.mouse.move(coordinates[0], coordinates[1])
                success = True
                
            elif action_name == "keyboard_shortcut":
                if not value:
                    raise ValueError("Keyboard shortcut value (e.g. Enter, Control+A) is required.")
                if selector:
                    await page.focus(selector)
                await page.keyboard.press(value)
                success = True
                
            else:
                raise ValueError(f"Unsupported action: '{action_name}'")

            # Pause briefly to allow state transitions
            await asyncio.sleep(0.5)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Action '{action_name}' execution failed: {error_msg}")

        # Capture post-action screenshot
        execution_time = int((time.time() - start_time) * 1000)
        screenshot_path = await self.browser_manager.take_screenshot(
            self.task_id or 999, f"action_{action_name}"
        )

        return {
            "success": success,
            "error": error_msg,
            "screenshot_path": screenshot_path,
            "execution_time_ms": execution_time,
            "downloaded_path": value if action_name == "download_file" and success else None
        }
