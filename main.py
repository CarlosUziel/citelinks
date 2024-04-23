import base64

import streamlit as st

from utils import replace_links_with_bibtex

# Improve the overall look and feel of the app
st.set_page_config(
    page_title="URL to Citation Converter",
    page_icon="📚",
)

# Streamlit code
st.title("URL to Citation Converter")

user_input = st.text_area("Enter your text here")

if st.button("Process URLs"):
    # Create a placeholder for the processing message
    processing_message = st.empty()
    # Display a message saying that the request is being processed
    processing_message.text("Processing your request...")

    original_text, modified_text, bibtex_citations = replace_links_with_bibtex(
        user_input
    )

    # Update the processing message to indicate that the processing is done
    processing_message.text("Processing done!")

    # Justify the output text
    st.write(
        "<div style='text-align: justify'>",
        modified_text,
        "</div>",
        unsafe_allow_html=True,
    )

    # Convert modified_text to a .txt file and create a download link
    b64_text = base64.b64encode(
        modified_text.encode()
    ).decode()  # some strings <-> bytes conversions necessary here
    href_text = f'<a href="data:file/txt;base64,{b64_text}" download="modified_text.txt">Download Modified Text</a>'

    # Convert bibtex_citations to a string with each citation separated by "\n"
    bibtex_string = "\n".join(bibtex_citations.values())
    b64_bib = base64.b64encode(
        bibtex_string.encode()
    ).decode()  # some strings <-> bytes conversions necessary here
    href_bib = f'<a href="data:file/txt;base64,{b64_bib}" download="bibtex_citations.bib">Download Citations BIB File</a>'

    # Center the download links using custom CSS
    st.markdown(
        f"""
        <style>
        .download-links {{
            display: flex;
            justify-content: center;
            gap: 10px;
        }}
        </style>
        <div class="download-links">
            {href_text}
            {href_bib}
        </div>
        """,
        unsafe_allow_html=True,
    )