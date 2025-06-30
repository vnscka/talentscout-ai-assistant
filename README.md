# TalentScout AI Hiring Assistant

## ✅ Project Overview

TalentScout AI Hiring Assistant is an intelligent chatbot designed to streamline the initial screening process for tech candidates. Built for "TalentScout," a fictional recruitment agency, this chatbot automates the collection of essential candidate information and generates relevant technical questions based on a candidate's declared tech stack. It leverages the power of Large Language Models (LLMs) to maintain a coherent conversation flow, making the preliminary screening process efficient and engaging.

## ⚙️ Installation Instructions

To set up and run the TalentScout AI Hiring Assistant locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone <Your_GitHub_Repo_Link_Here>
    cd talent-scout-chatbot
    ```
    (Replace `<Your_GitHub_Repo_Link_Here>` with your actual GitHub repository URL)

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```
    (You'll need to create a `requirements.txt` file if you don't have one. It should contain `streamlit`, `google-generativeai`, `python-dotenv` (if you use it for local env vars)).
    **Create `requirements.txt` content:**
    ```
    streamlit
    google-generativeai
    # python-dotenv # Only if you manage API key via .env file for local testing
    ```

4.  **Set up your Google Gemini API Key:**
    The application requires a Google Gemini API Key. You can set this up in two ways:
    * **Recommended for Streamlit Cloud deployment:** Create a `.streamlit/secrets.toml` file in your project root with the following content:
        ```toml
        google_gemini_api_key = "YOUR_GEMINI_API_KEY"
        ```
        Replace `"YOUR_GEMINI_API_KEY"` with your actual key.
    * **For local development (alternative):** Set it as an environment variable named `GOOGLE_API_KEY`.
        * On Windows: `set GOOGLE_API_KEY=YOUR_GEMINI_API_KEY`
        * On macOS/Linux: `export GOOGLE_API_KEY=YOUR_GEMINI_API_KEY`
        (It's best practice not to commit API keys directly to your repository).

## 🚀 How to Use

1.  **Run the Streamlit application:**
    ```bash
    streamlit run your_app_file_name.py
    ```
    (Replace `your_app_file_name.py` with the actual name of your Python script, e.g., `app.py` or `talent_scout_chatbot.py`).

2.  **Interact with the Chatbot:**
    * Upon launching, the chatbot will greet you and immediately prompt for essential candidate details (Full Name, Email, Phone, Years of Experience, Desired Position(s), Current Location, Tech Stack).
    * Provide the requested information in a clear format. The chatbot will attempt to parse these details. If any required information (Name, Email, Tech Stack) is missing or unparsable, it will re-prompt you.
    * Once sufficient information is collected, the chatbot will generate 3-5 technical questions based on your declared tech stack.
    * Answer the technical questions at your own pace.
    * When you are finished answering all questions, type a completion keyword like "done", "thank you", or "finished".
    * The chatbot will then provide a concise technical assessment based on your answers and gracefully conclude the conversation, informing you of the next steps.
    * To restart the chat session, click the "🔄 Reset Chat" button in the sidebar.

## 🧠 Prompt Design

Effective prompt engineering is central to this chatbot's functionality. The system uses a multi-stage prompting approach with Google Gemini 1.5 Flash:

1.  **Initial System Prompt:** Sets the persona ("TalentScout, an AI Hiring Assistant") and defines the primary goals (gather info, generate questions, maintain tone, graceful conclusion, non-deviation). This prompt is included in the `initial_history` of the `chat_session`.

    * **Example (excerpt):** "You are TalentScout... Your primary goal is to systematically gather essential candidate information... and then generate 3-5 relevant technical questions..."

2.  **Information Extraction Prompt:** Sent after the user's initial input, this prompt guides the LLM to extract structured data (JSON) from free-form text. It explicitly lists the required keys and instructs the LLM to use "N/A" for missing data, making parsing more reliable.

    * **Example:**
        ```
        Extract the following candidate information from the user's input. If a piece of information is not present, use "N/A".
        User input: "{user_input}"
        Return a valid JSON object with the following keys. Ensure all keys are present:
        {
            "Full Name": "...",
            "Email Address": "...",
            "Phone Number": "...",
            "Years of Experience": "...",
            "Desired Position(s)": "...",
            "Current Location": "...",
            "Tech Stack": "..."
        }
        ```

3.  **Technical Question Generation Prompt:** Triggered once candidate information is collected, this prompt asks the LLM to generate targeted questions based on the `Tech Stack` value.

    * **Example:** `"Generate 3–5 open-ended technical questions for a candidate skilled in: {tech_stack}. Format them as a numbered list."`

4.  **Technical Assessment Prompt:** Issued when the candidate signals completion of the technical questions. This prompt instructs the LLM to generate a concise, professional assessment based on the provided tech stack, questions, and the candidate's collected answers, focusing on specific criteria (technical depth, problem-solving, clarity) and explicitly disallowing hiring recommendations.

    * **Example (excerpt):** "You are evaluating a candidate's technical screening... Write a concise, professional 2–3 sentence assessment. Focus on: 1. Technical depth 2. Problem-solving 3. Clarity. No hiring recommendations."

These prompts are designed to be clear, concise, and provide sufficient context and constraints to guide the LLM toward desired, structured outputs for each phase of the screening.

## 🔐 Data Privacy Note

For this demonstration, candidate information is stored temporarily in Streamlit's `st.session_state`. This means the data resides only in the server's memory for the duration of the user's active session and is cleared upon session end or chat reset. No candidate data is persistently stored on disk or in a database in this demo version.

**Important for Production:** For a real-world application handling sensitive candidate information, robust data privacy measures compliant with regulations like GDPR would be essential. This would include:
* Secure, encrypted database storage (data at rest).
* Encrypted communication channels (data in transit, e.g., HTTPS).
* Strict access controls and authentication.
* Data retention policies and mechanisms for data deletion.
* Explicit user consent mechanisms.
* Regular security audits and compliance checks.

This project focuses on the LLM interaction and UI, demonstrating the *flow* of data gathering rather than its secure, long-term persistence.

## 📚 Tech Used

* **Programming Language:** Python
* **Frontend Interface:** Streamlit
* **Large Language Model (LLM):** Google Gemini 1.5 Flash (via `google-generativeai` library)

## 🧩 Challenges & Fixes

During development, several challenges were encountered and addressed:

1.  **Initial Chatbox Rendering:**
    * **Challenge:** Initially, an empty white `chat-box` div was visible at the start, making the UI appear cluttered even before any interaction.
    * **Fix:** The explicit `div` structure for the `.chat-box` was removed. Messages are now directly rendered using `st.markdown` with individual message styling, allowing the chat content to flow naturally without a predefined container. The first greeting is placed directly on the page, and subsequent messages appear inline.

2.  **Conversation Flow & Context Management:**
    * **Challenge:** Ensuring the chatbot consistently followed the multi-stage screening process (info gathering -> question generation -> answer collection -> assessment) without deviation or losing track of the current stage.
    * **Fix:** Comprehensive use of Streamlit's `st.session_state` was implemented to track the chatbot's state (`info_requested`, `info_collected`, `tech_questions_asked`, `conversation_ended`). Conditional logic based on these flags dictates the chatbot's next action and response, providing a structured and predictable flow.

3.  **Robust Information Parsing:**
    * **Challenge:** Extracting structured candidate details from free-form user input reliably and handling cases of incomplete or malformed input. Simple user responses like "okay" or "huh" could lead to parsing errors.
    * **Fix:** A specific "Information Extraction Prompt" was designed to guide the LLM to output details in a JSON format. The Python code includes `try-except` blocks for `json.JSONDecodeError` and logic to check for the presence and validity of critical fields (Name, Email, Tech Stack). If parsing fails or information is missing, the chatbot provides specific, actionable feedback to the user, re-prompting for the necessary details.
