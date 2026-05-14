"""
scraper.py — Legacy standalone debug runner
Use this to quickly test the scraper output in isolation without running main.py.
For production, run:  python main.py
"""

from windows_scraper import scrape_active_window
import json
import time

print("Nudge Scraper — Debug Mode")
print("Scraping every 10 seconds. Switch to the window you want to inspect.\n")

while True:
    print("\nWaiting 10 seconds... (Switch to the window you want to scrape!)")
    time.sleep(10)

    result = scrape_active_window()
    if result:
        print(f"\n{'='*60}")
        print(f"App:    {result['app_name']}")
        print(f"Title:  {result['window_title']}")
        print(f"Time:   {result['timestamp']}")
        print(f"Elements ({len(result['text_elements'])}):")
        for el in result['text_elements'][:30]:  # show first 30
            print(f"  · {el}")
        if len(result['text_elements']) > 30:
            print(f"  ... and {len(result['text_elements']) - 30} more")
        print(f"{'='*60}")

        # Also write JSON for inspection
        with open("scraping_results.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("[OK] Written to scraping_results.json")
    else:
        print("[WARN] Scrape returned None")