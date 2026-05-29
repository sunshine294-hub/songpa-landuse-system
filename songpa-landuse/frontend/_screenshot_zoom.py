# -*- coding: utf-8 -*-
"""Zoom in screenshot to see parcel coloring"""
from playwright.sync_api import sync_playwright
import os

SCREENSHOT_DIR = r"c:\Users\gangg\antigravity\prom\songpa-landuse\frontend"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    
    page.goto("http://localhost:5173", timeout=30000)
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    
    # Zoom in by scrolling on map area
    map_el = page.locator(".maplibregl-canvas")
    box = map_el.bounding_box()
    if box:
        cx = box["x"] + box["width"] / 2
        cy = box["y"] + box["height"] / 2
        # Move mouse to center of map then scroll
        page.mouse.move(cx, cy)
        for _ in range(8):
            page.mouse.wheel(0, -300)
            page.wait_for_timeout(300)
        
        page.wait_for_timeout(4000)  # Wait for tiles and data to load
    
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "screenshot_zoomed.png"), full_page=False)
    print("Zoomed screenshot saved")
    
    # Also test zone color mode
    zone_btn = page.locator("aside").first.locator("button:has-text('용도지역')")
    if zone_btn.count() > 0:
        zone_btn.click()
        page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "screenshot_zone.png"), full_page=False)
        print("Zone mode screenshot saved")
    
    browser.close()
