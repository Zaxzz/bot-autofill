# bot.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os, time, random, traceback

# ================== KONFIG ==================
EMAIL = os.getenv("RUBIN_EMAIL")  # ambil dari GitHub Secrets
PASSWORD = os.getenv("RUBIN_PASS")  # ambil dari GitHub Secrets
LOGIN_URL = "https://rubin.id/login.html"
WINDOW_SIZE = (390, 844)  # tampilan mobile
if not EMAIL or not PASSWORD:
    raise SystemExit("Set RUBIN_EMAIL & RUBIN_PASS di GitHub Secrets dulu ya.")

# ============================================

def jitter(min_ms=200, max_ms=600):
    time.sleep(random.uniform(min_ms/1000, max_ms/1000))

def safe_click(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)

def click_checkbox_if_needed(driver, wait, xpath, desired=True, timeout=10):
    el = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    except Exception:
        pass
    checked = el.is_selected()
    if desired and not checked:
        safe_click(driver, el)
    elif (not desired) and checked:
        safe_click(driver, el)
    return el

def ensure_panel_open(driver, wait, panel_id, header_text):
    header_xpath = f"//h6[.//span[normalize-space()='{header_text}']]"
    header = wait.until(EC.presence_of_element_located((By.XPATH, header_xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", header)
    collapse = driver.find_element(By.ID, panel_id)
    if "show" not in collapse.get_attribute("class"):
        anchor = header.find_element(By.XPATH, "./ancestor::a")
        safe_click(driver, anchor)
        WebDriverWait(driver, 10).until(lambda d: "show" in collapse.get_attribute("class"))
    return collapse

def toggle_random_two_on_one_off(driver, wait, base_xpath):
    names = ["awal_waktu", "dimasjid", "berjamaah"]
    off_name = random.choice(names)
    for name in names:
        desired = (name != off_name)
        xpath = f"{base_xpath}//input[starts-with(@id,'{name}-')]"
        click_checkbox_if_needed(driver, wait, xpath, desired=desired)
        jitter(250, 700)
    print(f"🎲 Pola toggle: OFF={off_name}, ON={[n for n in names if n != off_name]}")

def process_sholat_panel(driver, wait, panel_id, header_text):
    panel_el = ensure_panel_open(driver, wait, panel_id=panel_id, header_text=header_text)
    base_xpath = f"//*[@id='{panel_id}']"
    # Berhalangan → OFF
    try:
        bh = panel_el.find_element(By.XPATH, ".//input[starts-with(@id,'berhalangan-')]")
        if bh.is_selected():
            click_checkbox_if_needed(driver, wait, f"{base_xpath}//input[starts-with(@id,'berhalangan-')]", desired=False)
            jitter()
    except Exception:
        pass
    # Dilakukan → ON
    click_checkbox_if_needed(driver, wait, f"{base_xpath}//input[starts-with(@id,'dilakukan-')]", desired=True)
    jitter(600, 1000)
    # Random 2 ON, 1 OFF
    toggle_random_two_on_one_off(driver, wait, base_xpath)
    print(f"✅ {header_text}: selesai")

def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--window-size={WINDOW_SIZE[0]},{WINDOW_SIZE[1]}")
    options.add_argument("--lang=id-ID")
    # (runner sering set ini)
    chrome_path = os.getenv("CHROME_PATH") or os.getenv("GOOGLE_CHROME_SHIM")
    if chrome_path:
        options.binary_location = chrome_path

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 25)

    try:
        # Login
        driver.get(LOGIN_URL)
        email_box = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[contains(@placeholder,'Email') or contains(@placeholder,'No hp')]")
        ))
        pass_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
        email_box.clear(); email_box.send_keys(EMAIL)
        pass_box.clear();  pass_box.send_keys(PASSWORD)
        login_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space()='Login' or contains(.,'Login')]")
        ))
        safe_click(driver, login_btn)

        # Buka kartu "Sudah Sholat ?"
        target_card = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//h6[contains(normalize-space(),'Sudah Sholat')]")
        ))
        driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", target_card)
        time.sleep(0.5)
        parent_div = target_card.find_element(By.XPATH, "./ancestor::div[@class='col pl-0']")
        safe_click(driver, parent_div)
        print("✅ Masuk halaman input sholat")

        # Urutan panel yang diproses
        targets = [
            ("collapse-Subuh",   "Sholat Wajib Subuh"),
            ("collapse-Dzuhur",  "Sholat Wajib Dzuhur"),
            ("collapse-Ashar",   "Sholat Wajib Ashar"),
            ("collapse-Maghrib", "Sholat Wajib Maghrib"),
            ("collapse-Isya",    "Sholat Wajib Isya"),
        ]

        for pid, title in targets:
            try:
                process_sholat_panel(driver, wait, panel_id=pid, header_text=title)
                jitter(500, 900)
            except Exception as e:
                print(f"⚠️ {title}: gagal diproses ({e}). Lanjut yang lain...")

        print("🎉 Semua panel dicoba diproses.")

    except Exception as e:
        print("❌ ERROR:", e)
        traceback.print_exc()
        ts = int(time.time())
        try:
            driver.save_screenshot(f"fail_{ts}.png")
            print(f"📸 Screenshot disimpan: fail_{ts}.png")
        except Exception:
            pass
        raise
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
