import gradio as gr
from gtts import gTTS
import os

def scrape_x_article(url: str, headless: bool = False, chrome_profile: str = None):
    """
    Returns:
        title (str)
        full_text (str)
    """

    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    import time

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    if chrome_profile:
        options.add_argument(f"--user-data-dir={chrome_profile}")
        options.add_argument("--profile-directory=Default")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless")
    options.binary_location = "/usr/bin/chromium"
    

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        time.sleep(4)

        # -------- TITLE --------
        page_title = driver.title.replace(" / X", "").strip()

        # -------- SCROLL --------
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # -------- ARTICLE BLOCKS --------
        selectors = [
            "div.longform-unstyled-narrow",
            "div[data-block='true']",
            "div[class*='longform']",
        ]

        paragraphs = []
        for selector in selectors:
            paragraphs = driver.find_elements(By.CSS_SELECTOR, selector)
            if paragraphs:
                break

        if not paragraphs:
            spans = driver.find_elements(By.CSS_SELECTOR, 'span[data-text="true"]')
            full_text = " ".join(s.text for s in spans if s.text.strip())
            return page_title, full_text

        extracted = []
        for para in paragraphs:
            spans = para.find_elements(By.CSS_SELECTOR, 'span[data-text="true"]')
            text = "".join(s.text for s in spans).strip()
            if text:
                extracted.append(text)

        full_text = "\n\n".join(extracted)

        return page_title, full_text

    finally:
        driver.quit()


def scrape_tweet(url: str, headless: bool = False, chrome_profile: str = None):
    """
    Returns:
        title (str)
        tweet_text (str)
    """

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import time

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    if chrome_profile:
        options.add_argument(f"--user-data-dir={chrome_profile}")
        options.add_argument("--profile-directory=Default")

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--window-size=1280,720")  # smaller than 1920x1080
    options.add_argument("--single-process")  # critical for low-memory envs
    options.add_argument("--no-zygote")
    options.binary_location = "/usr/bin/chromium"

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)

        wait = WebDriverWait(driver, 20)

        # Wait for tweet container
        tweet_container = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@data-testid='tweetText']")
            )
        )

        # Small delay to ensure rendering
        time.sleep(2)

        # Extract spans
        spans = tweet_container.find_elements(By.XPATH, ".//span")
        tweet_text = " ".join(
            [span.text for span in spans if span.text.strip()]
        )

        # Title from page title
        page_title = driver.title.replace(" / X", "").strip()

        return page_title, tweet_text

    finally:
        driver.quit()

# ----------------------------
# SCRAPER WRAPPER
# ----------------------------
def scrape_content(mode, url):
    try:
        if mode == "Normal Tweet":
            title, text = scrape_tweet(url)
        else:
            title, text = scrape_x_article(url)

        
        return title, text

    except Exception as e:
        return "Error", str(e)


# ----------------------------
# TTS GENERATOR
# ----------------------------
def generate_audio(text):
    if not text.strip():
        return None

    tts = gTTS(text=text, lang="en")
    output_path = "output.mp3"
    tts.save(output_path)

    return output_path


# ----------------------------
# UI
# ----------------------------
with gr.Blocks() as app:
    gr.Markdown("# X Post → Speech")

    mode = gr.Radio(
        choices=["Normal Tweet", "Long Form Article"],
        label="Select Content Type",
        value="Normal Tweet"
    )

    url_input = gr.Textbox(label="Paste X URL")

    scrape_btn = gr.Button("Scrape Content")

    title_output = gr.Textbox(label="Title")
    text_output = gr.Textbox(label="Extracted Text", lines=15)

    scrape_btn.click(
        scrape_content,
        inputs=[mode, url_input],
        outputs=[title_output,text_output]
    )

    gr.Markdown("## Generate Audio")

    audio_btn = gr.Button("Generate Audio")
    audio_output = gr.Audio(label="Audio Output")

    audio_btn.click(
        generate_audio,
        inputs=text_output,
        outputs=audio_output
    )

app.launch(server_name="0.0.0.0", server_port=7860)
