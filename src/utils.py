import multiprocessing
import re
import urllib.parse
from typing import Dict, List, Optional, Tuple

import requests
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def decode_html(html: str) -> str:
    """
    Decode HTML entities.

    Args:
        html: HTML content.

    Returns:
        Decoded HTML content.
    """
    return urllib.parse.unquote(html)


def get_html_selenium(url: str) -> str:
    """
    Get HTML content of a webpage using Selenium.

    Args:
        url: URL of the webpage.

    Returns:
        HTML content of the webpage.
    """
    # Setup Selenium
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")

    service = webdriver.FirefoxService(
        executable_path="/home/uziel/miniforge3/envs/citelinks/bin/geckodriver"
    )
    driver = webdriver.Firefox(
        service=service,
        options=options,
    )

    # Get HTML content
    driver.get(url)
    html_content = driver.page_source

    # Close Selenium
    driver.quit()

    return html_content


def get_doi_from_html(html: str) -> Optional[str]:
    """
    Extracts DOI from HTML content.

    Args:
        html: HTML content of a webpage.
    """
    doi_match = re.search(
        r"(https:)?//doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9%]+)",
        decode_html(html),
        re.IGNORECASE,
    )
    return doi_match.group(0).replace("%2F", "/") if doi_match else None


def get_doi_from_scribbr(url: str) -> Optional[str]:
    """
    Extracts DOI from a URL using the Scribbr citation generator.

    Args:
        url: URL of the publication.

    Returns:
        DOI of the publication.
    """
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")

    service = webdriver.FirefoxService(
        executable_path="/home/uziel/miniforge3/envs/citelinks/bin/geckodriver"
    )
    driver = webdriver.Firefox(
        service=service,
        options=options,
    )

    # Navigate to the citation generator page
    driver.get("https://www.scribbr.com/citation/generator/")

    # Find the input field and submit the URL
    input_field = driver.find_element(
        By.CSS_SELECTOR,
        "input.bg-transparent.text-sm.outline-none.placeholder\\:text-navy-blue-11",
    )
    input_field.send_keys(url)
    input_field.send_keys(Keys.RETURN)

    # Wait for the DOI element to be present in the DOM
    wait = WebDriverWait(driver, 5)  # wait up to 5 seconds
    try:
        doi_element = wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".inline-flex.items-center.space-x-2.truncate.rounded-full"
                    ".px-4.py-2.text-sm.font-semibold.bg-blue-3.hover\\:bg-blue-4",
                )
            )
        )
    except selenium.common.exceptions.TimeoutException:
        driver.quit()
        return None

    doi = doi_element.get_attribute("href")

    # Close the driver
    driver.quit()

    return doi


def extract_doi_from_url(url: str) -> Optional[str]:
    """
    Extracts DOI from HTML content of a webpage.

    Args:
        url: URL of the webpage.
    """
    # 1. Try requests approach
    doi_match = get_doi_from_html(requests.get(url).text)

    # 2. Try Selenium approach
    if not doi_match:
        doi_match = get_doi_from_html(get_html_selenium(url))

    # 3. Try Scribbr approach
    if not doi_match:
        doi_match = get_doi_from_scribbr(url)

    return doi_match


def get_bibtex_citation(doi: str) -> Optional[str]:
    """
    Get BibTeX citation from DOI.

    Args:
        doi: DOI of the article.

    Returns:
        BibTeX citation of the article.
    """
    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url)
    data = response.json()

    # Extract relevant fields
    title = data["message"]["title"][0]
    year = data["message"]["created"]["date-parts"][0][0]
    author = data["message"]["author"][0]["family"]
    journal = data["message"]["container-title"][0]

    # Generate citation key
    title_words = re.findall(r"\b\w+\b", title)
    keyword = title_words[0].lower() if title_words else "article"
    citation_key = f"{author}{year}{keyword}"

    # Construct BibTeX citation
    bibtex_citation = f"@article{{{citation_key},\n title = {{{title}}},\n author = {{{author}}},\n year = {year},\n journal = {{{journal}}}\n}}"

    return bibtex_citation


def process_paragraph(
    paragraph: str, bibtex_citations: Dict[str, str], paragraphs: List[str]
) -> None:
    """
    Process a batch of sentences.

    Args:
        paragraph: Paragraph of a text.
        bibtex_citations: Dictionary to store BibTeX citations.
        sentences: List of sentences to be modified.
    """
    # Regular expression to match URLs
    url_regex = (
        r"http[s]?://"  # http or https
        r"(?:[a-zA-Z]|[0-9]|"  # alphanumeric characters
        r"[$-_@.&+]|"  # special characters
        r"[!*\\(\\),]|"  # special characters
        r"(?:%[0-9a-fA-F][0-9a-fA-F]))+"  # percent encoding
    )

    # Store original sentence
    original_paragraph = paragraph

    # Find all URLs in the sentence
    urls = re.findall(url_regex, paragraph)

    for url in urls:
        # Extract DOI from URL
        doi = extract_doi_from_url(url)

        if doi:
            # Generate BibTeX citation
            bibtex_citation = get_bibtex_citation(doi)

            # Extract citation key from BibTeX citation
            citation_key = bibtex_citation.split(",")[0].split("{")[1]

            # Add BibTeX citation to list
            bibtex_citations[citation_key] = bibtex_citation

            # Replace URL with citation key
            paragraph = paragraph.replace(url, citation_key + url[-2:])

    # Replace original sentence with modified sentence in the shared list
    paragraphs[paragraphs.index(original_paragraph)] = paragraph


def replace_links_with_bibtex(text: str) -> Tuple[str, str, List[str]]:
    """
    Replace URLs in text with BibTeX citations.

    Args:
        text: Input text.
        batch_size: Number of sentences to process in each batch.

    Returns:
        Tuple containing original text, modified text, and list of BibTeX citations.
    """
    # 0. Setup
    manager = multiprocessing.Manager()
    bibtex_citations = manager.dict(dict())

    # 1. Split text into paragraphs
    paragraphs = manager.list(text.split("\n"))

    # 2. Process each paragraph
    for paragraph in paragraphs:
        # 2.1. Create new process
        process = multiprocessing.Process(
            target=process_paragraph, args=(paragraph, bibtex_citations, paragraphs)
        )
        process.start()
        process.join()

    # 3. Join modified paragraphs back together
    modified_text = "\n".join(paragraphs)

    return text, modified_text, bibtex_citations
