# -*- coding: utf-8 -*-
"""Screenshot the running frontend at localhost:5173"""
from playwright.sync_api import sync_playwright
import os

SCREENSHOT_DIR = r"c:\Users\gangg\antigravity\prom\songpa-landuse\frontend"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    # Capture console errors
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    
    page.goto("http://localhost:5173", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(3000)  # Extra wait for map tiles to load
    
    screenshot_path = os.path.join(SCREENSHOT_DIR, "screenshot_initial.png")
    page.screenshot(path=screenshot_path, full_page=False)
    print(f"Screenshot saved: {screenshot_path}")
    
    if errors:
        print(f"\nConsole errors ({len(errors)}):")
        for e in errors[:20]:
            print(f"  - {e}")
    else:
        print("No console errors!")
    
    # Check if map loaded
    map_el = page.locator(".maplibregl-canvas")
    print(f"Map canvas found: {map_el.count() > 0}")
    
    browser.close()
