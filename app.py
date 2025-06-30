import streamlit as st
import google.generativeai as genai
import os
import json
import re
from google.api_core import exceptions # Imported but not explicitly used for error handling type in current version

# --- Page Configuration ---
st.set_page_config(
    page_title="TalentScout – AI Hiring Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Styling ---
st.markdown("""
<style>
body, html {
    font-family: 'Segoe UI', sans-serif;
    /* Removed explicit background-color to let Streamlit's theme control the main page background */
}

/* Ensure general text within Streamlit containers is visible */
div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"],
div[data-testid="stMarkdownContainer"] {
    color: var(--text-color); /* Use Streamlit's theme variable for text color */
}

/* Specific styling for custom message bubbles */
.message {
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.75rem;
    font-size: 15px;
    max-width: 85%;
    line-height: 1.6;
    word-wrap: break-word;
    margin-top: 0.5rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.user {
    background-color: #e7f1ff; /* Light blue for user messages */
    color: #1a1a1a; /* Dark text for user messages */
    align-self: flex-end;
    margin-left: auto;
    border: 1px solid #d0e0ff;
}
.assistant {
    background-color: #f9f9f9; /* Very light gray for assistant messages */
    color: #1a1a1a; /* Dark text for assistant messages */
    border: 1px solid #e0e0e0;
    align-self: flex-start;
    margin-right: auto;
}

/* Sidebar Titles and Descriptions */
.sidebar-title {
    font-size: 24px;
    font-weight: bold;
    color: var(--text-color); /* Use Streamlit's theme variable */
    margin-bottom: 0.5rem;
}
.sidebar-desc {
    font-size: 14px;
    color: var(--text-color); /* Use Streamlit's theme variable */
    margin-bottom: 1.5rem;
}

/* Textarea for user input */
textarea {
    border: 1px solid var(--border-color) !important; /* Use Streamlit's theme variable */
    border-radius: 8px !important;
    padding: 0.75rem !important;
    font-size: 15px !important;
    background-color: var(--secondary-background-color) !important; /* Ensure it contrasts */
    color: var(--text-color) !important; /* Ensure text is visible */
}

/* Main Streamlit Button */
.st-emotion-cache-1c7y2vl.eczjsme11 { /* This is the "Send" button */
    background-color: #2e72d2;
    color: white; /* Ensure text is white */
    padding: 0.6rem 1.5rem;
    border-radius: 6px;
    font-size: 14px;
    cursor: pointer;
    border: none;
}
.st-emotion-cache-1c7y2vl.eczjsme11:hover {
    background-color: #1a56a4;
    color: white; /* Ensure text remains white on hover */
}

/* General Streamlit Button */
div.stButton > button {
    background-color: var(--secondary-background-color); /* Use Streamlit's theme variable */
    color: var(--text-color); /* Use Streamlit's theme variable */
    border: 1px solid var(--border-color); /* Use Streamlit's theme variable */
    border-radius: 6px;
    padding: 0.4rem 1.2rem;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
}
div.stButton > button:hover {
    background-color: var(--background-color); /* Lighter hover in both themes */
}

/* Hide Streamlit default elements */
#MainMenu, header, footer {
    visibility: hidden;
}

/* Spinner color */
.stSpinner > div > div {
    border-top-color: #2e72d2;
}

/* Candidate Info Box */
.candidate-info-box {
    background-color: var(--secondary-background-color); /* Use Streamlit's theme variable for background */
    color: var(--text-color); /* Use Streamlit's theme variable for text */
    border: 1px solid var(--border-color); /* Use Streamlit's theme variable for border */
    border-radius: 8px;
    padding: 1rem;
    margin-top: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.candidate-info-box h5 {
    color: #2e72d2; /* Keep blue for heading, should be visible in both modes */
    margin-bottom: 0.75rem;
    font-size: 1.1rem;
}
.candidate-info-box p {
    margin-bottom: 0.3rem;
    font-size: 0.95rem;
    color: var(--text-color); /* Use Streamlit's theme variable for text */
}
.candidate-info-box strong {
    color: var(--text-color); /* Use Streamlit's theme variable for text */
}
</style>
""", unsafe_allow_html=True)

# --- API Setup ---
gemini_api_key = st.secrets.get("google_gemini_api_key") or os.getenv("GOOGLE_API_KEY")
if not gemini_api_key:
    st.error("Gemini API Key not found. Please set it in `.streamlit/secrets.toml` or as an environment variable `GOOGLE_API_KEY`.")
    st.stop()

genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel("models/gemini-1.5-flash")

# --- Data Persistence Setup ---
PERSISTENCE_FILE = "talent_scout_session.json"

# --- Helper for Language-Specific Prompt ---
def get_initial_system_prompt(language="English"):
    """
    Generates the initial system prompt for the Gemini model, including
    instructions for the desired interaction language.
    """
    base_prompt = """
You are TalentScout, an AI Hiring Assistant for tech recruitment. Your primary goal is to systematically gather essential candidate information (Full Name, Email, Phone, Years of Experience, Desired Position(s), Current Location, Tech Stack) and then generate 3-5 relevant technical questions based on their declared tech stack. Maintain a polite, professional, and helpful tone. Ensure coherent and context-aware interactions. If you don't understand an input, politely ask for clarification or guide the user back to the main purpose. You will only provide a final, concise technical assessment *after* the candidate indicates they have completed answering the questions (e.g., by saying 'done' or 'thank you'). Gracefully conclude the conversation, thanking the candidate and informing them about the next steps when they express intent to exit or the screening process is complete. Always stay on topic for hiring assistance. After the initial greeting, *explicitly request* the candidate's personal and tech stack information before proceeding with any other step. Do not generate closing remarks or assessments until all required information is gathered and technical questions are answered AND the candidate signals completion.
"""
    initial_history = [
        {"role": "user", "parts": [base_prompt]},
        {"role": "model", "parts": ["Understood. I will follow the specified process for technical screening."]}
    ]

    # Add explicit language instruction if not English
    if language != "English":
        initial_history.append({"role": "user", "parts": [f"From now on, all your responses and interactions MUST be exclusively in {language}. You are forbidden from using any other language. Translate all your output into {language}."]})
        initial_history.append({"role": "model", "parts": [f"Understood. I will now respond ONLY in {language}."]})

    return initial_history

def save_state():
    """Saves all relevant session state to a JSON file."""
    state_to_save = {
        "messages": st.session_state.messages,
        "candidate_info": st.session_state.candidate_info,
        "info_requested": st.session_state.info_requested,
        "info_collected": st.session_state.info_collected,
        "tech_questions_asked": st.session_state.tech_questions_asked,
        "generated_tech_questions": st.session_state.generated_tech_questions,
        "conversation_ended": st.session_state.conversation_ended,
        "Youtube_map": st.session_state.Youtube_map, # Assuming 'Youtube_map' is intended to store Q&A
        "current_question_idx": st.session_state.current_question_idx,
        "awaiting_follow_up": st.session_state.awaiting_follow_up,
        "selected_language": st.session_state.get("selected_language", "English")
    }
    try:
        with open(PERSISTENCE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_to_save, f, indent=4)
    except Exception as e:
        st.error(f"Error saving session state: {e}")

def load_state():
    """Loads session state from JSON file with complete initialization."""
    if os.path.exists(PERSISTENCE_FILE):
        try:
            with open(PERSISTENCE_FILE, "r", encoding="utf-8") as f:
                loaded_state = json.load(f)
            
            # Initialize all state variables with defaults if missing in loaded state
            default_state = {
                "messages": [],
                "candidate_info": {},
                "info_requested": False,
                "info_collected": False,
                "tech_questions_asked": False,
                "generated_tech_questions": "",
                "conversation_ended": False,
                "Youtube_map": {},
                "current_question_idx": 0,
                "awaiting_follow_up": False,
                "selected_language": "English"
            }
            
            for key in default_state:
                st.session_state[key] = loaded_state.get(key, default_state[key])

            # Initialize chat session with proper history using the loaded language
            current_language = st.session_state.get("selected_language", "English")
            system_and_model_history = get_initial_system_prompt(current_language)
            
            # Reconstruct chat history from messages (excluding the initial hardcoded greeting)
            chat_history = system_and_model_history
            for msg in st.session_state.messages:
                # Exclude the hardcoded welcome message from the LLM's internal history
                if not (msg["role"] == "assistant" and msg["content"].startswith("👋 Hello! I'm **TalentScout**")):
                    chat_history.append({
                        "role": msg["role"],
                        "parts": [msg["content"]]
                    })
            
            st.session_state.chat_session = model.start_chat(history=chat_history)
            
            return True
        except Exception as e:
            st.warning(f"Error loading session state: {e}. Starting a new session.")
            return False
    return False

# --- Helper Functions for Chat Logic ---
def is_substantive_answer(text, min_words=15):
    """
    Checks if a candidate's answer meets minimum substance requirements.
    """
    completion_keywords = ["done", "thank", "finished", "complete", "skip", "n/a"]
    text_lower = text.lower().strip()
    return (
        len(text.split()) >= min_words and
        not any(kw in text_lower for kw in completion_keywords)
    )

def format_qa_for_assessment():
    """Formats the collected questions and answers for the final assessment prompt."""
    return "\n".join(
        f"Question {i+1}: {qa['question']}\nAnswer: {' '.join(qa['answers'])}\n"
        for i, qa in enumerate(st.session_state.Youtube_map.values())
    )

def generate_follow_up(question, answer, tech_stack):
    """Generates a targeted follow-up question based on a previous answer."""
    current_lang = st.session_state.get("selected_language", "English")
    prompt = f"""
    Based on this technical exchange:
    Question: "{question}"
    Answer: "{answer}"

    Generate exactly ONE follow-up question that:
    1. Targets the most important technical concept from the original question or answer.
    2. Asks for specific examples or implementation details.
    3. References these technologies if relevant: {tech_stack}
    4. Is 1-2 sentences maximum.
    5. MUST be exclusively in {current_lang}.

    Example formats:
    - "How would you implement this using [TECH]?"
    - "What metrics would you use to measure success?"
    - "How would this approach scale to 1 million users?"

    Make it specific and technical.
    """
    try:
        response = st.session_state.chat_session.send_message(prompt).text
        return f"To better understand: {response}" # Prepending with "To better understand:"
    except Exception as e:
        # Fallback message is in English, consider adding translations for these static messages
        return "Could you elaborate on your last point?"

def validate_candidate_info(info):
    """
    Validates extracted candidate information (email format, phone, years of experience).
    Returns if all required fields are present, a list of missing fields, and invalid fields.
    """
    required_fields = ["Full Name", "Email Address", "Tech Stack"]
    all_present = True
    missing_fields = []
    invalid_fields = []

    # Check required fields
    for field in required_fields:
        value = info.get(field, "").strip()
        if not value or value.lower() == "n/a":
            all_present = False
            missing_fields.append(field)

    # Validate email format
    email = info.get("Email Address", "")
    if email and email.lower() != "n/a":
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            invalid_fields.append("Email Address (invalid format)")

    # Validate phone number
    phone = info.get("Phone Number", "")
    if phone and phone.lower() != "n/a":
        if not re.match(r"^\+?[\d\s\-()]+$", phone): # Allows digits, spaces, hyphens, parentheses
            invalid_fields.append("Phone Number (invalid format)")

    # Validate years of experience
    years_exp = info.get("Years of Experience", "")
    if years_exp and years_exp.lower() != "n/a":
        try:
            exp = float(years_exp)
            if not (0 <= exp <= 50): # Assuming a reasonable range for experience
                invalid_fields.append("Years of Experience (unrealistic value)")
        except ValueError:
            invalid_fields.append("Years of Experience (not a number)")

    return all_present, missing_fields, invalid_fields

def generate_tech_questions():
    """Generates technical questions based on the candidate's tech stack."""
    tech_stack = st.session_state.candidate_info.get("Tech Stack", "programming")
    current_lang = st.session_state.get("selected_language", "English")

    prompt = f"""
    Generate 3-5 technical questions for a candidate with this tech stack: {tech_stack}
    Requirements:
    - Each question should test practical, hands-on knowledge.
    - Include at least one question about system design.
    - Include at least one question about debugging/optimization.
    - Questions should require detailed explanations, not just yes/no answers.
    - Format as a numbered list.
    - Avoid generic "what is" questions.
    - All questions MUST be exclusively in {current_lang}.
    """
    try:
        response = st.session_state.chat_session.send_message(prompt).text
        # Ensure questions are parsed correctly from the numbered list format
        return [q.strip() for q in response.split('\n') if q.strip() and re.match(r'^\d+\.', q.strip())]
    except Exception as e:
        # Fallback message is in English, consider adding translations
        st.error(f"Error generating questions: {e}")
        return []

def generate_assessment():
    """Generates the final technical assessment based on collected answers."""
    current_lang = st.session_state.get("selected_language", "English")
    assessment_prompt = f"""
    Candidate Tech Stack: {st.session_state.candidate_info.get("Tech Stack", "N/A")}
    
    Questions and Answers:
    {format_qa_for_assessment()}
    
    Provide a concise technical assessment (3-4 sentences) that:
    1. Highlights 2 specific strengths demonstrated in the answers.
    2. Identifies 2 concrete areas for improvement.
    3. Assesses overall technical competency (1-5 scale).
    4. Avoids generic statements - be specific to the answers given and Note the overall tone or confidence conveyed in their responses.
    5. Does not make hiring recommendations.
    6. All output MUST be exclusively in {current_lang}.
    """
    try:
        assessment = st.session_state.chat_session.send_message(assessment_prompt).text
        name = st.session_state.candidate_info.get("Full Name", "Candidate").split()[0]
        
        # This concluding message is static, consider adding translations for it.
        return f"""
🎯 Technical Assessment for {name}:
{assessment}

Thank you for your time! We'll be in touch within 5-7 business days.
"""
    except Exception as e:
        # Fallback message is in English, consider adding translations
        return f"Error generating assessment: {e}"

# --- Session Initialization ---
# This block handles initial setup or loading of state from persistence file
if "messages" not in st.session_state:
    if not load_state():
        # Initialize all state variables if no saved state found or load failed
        st.session_state.messages = []
        st.session_state.candidate_info = {}
        st.session_state.info_requested = False
        st.session_state.info_collected = False
        st.session_state.tech_questions_asked = False
        st.session_state.generated_tech_questions = ""
        st.session_state.conversation_ended = False
        st.session_state.Youtube_map = {} # Used to store question-answer pairs
        st.session_state.current_question_idx = 0
        st.session_state.awaiting_follow_up = False
        st.session_state.selected_language = "English" # Default language on fresh start

        # Start chat session with the dynamic initial prompt
        initial_history_for_chat = get_initial_system_prompt(st.session_state.selected_language)
        st.session_state.chat_session = model.start_chat(history=initial_history_for_chat)

        # Initial assistant message for the user (hardcoded, not translated by LLM)
        welcome_msg = """👋 Hello! I'm **TalentScout**, your AI hiring assistant. To begin your quick technical screening, please provide the following details:

- **Full Name**
- **Email**
- **Phone Number**
- **Years of Tech Experience**
- **Preferred Role(s)**
- **Current Location**
- **Your Tech Stack**

Once I have this, I'll generate a few technical questions for you. 🚀"""
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
        st.session_state.info_requested = True
        save_state()

# Fallback: Ensure chat_session exists even if loading failed or if it somehow disappeared during a rerun
if "chat_session" not in st.session_state:
    current_lang = st.session_state.get("selected_language", "English")
    fallback_history = get_initial_system_prompt(current_lang)

    chat_history_for_new_session = []
    for msg in st.session_state.messages:
        # Exclude the hardcoded welcome message from the LLM's history
        if not (msg["role"] == "assistant" and msg["content"].startswith("👋 Hello! I'm **TalentScout**")):
            chat_history_for_new_session.append({"role": msg["role"], "parts": [msg["content"]]})

    # Start the chat session with the dynamic system prompt and existing conversation
    st.session_state.chat_session = model.start_chat(history=fallback_history + chat_history_for_new_session)


# --- Main Chat Logic (`handle_user_input` function definition) ---
def handle_user_input(user_input):
    """
    Processes user input based on the current stage of the conversation.
    Handles navigation, info collection, technical Q&A, and conversation completion.
    """
    completion_keywords = ["thank", "done", "finished", "that's all", "no more", "complete", "bye"]
    navigation_keywords = ["next", "skip", "back"]
    user_input_lower = user_input.lower().strip()
    
    # Handle navigation commands
    if user_input_lower in navigation_keywords:
        if user_input_lower == "back":
            st.session_state.current_question_idx = max(0, st.session_state.current_question_idx - 1)
        else: # "next" or "skip"
            st.session_state.current_question_idx += 1
        
        questions = [q for q in st.session_state.generated_tech_questions.split('\n') if q.strip()]
        if st.session_state.current_question_idx < len(questions):
            return questions[st.session_state.current_question_idx]
        else:
            # This message is static, consider adding translations for it.
            return "You've completed all questions. Say 'done' for your assessment."
    
    # Handle completion request
    elif any(kw in user_input_lower for kw in completion_keywords):
        if not st.session_state.Youtube_map:
            # This message is static, consider adding translations for it.
            return "Please answer at least one question completely before saying 'done'."
        
        # Check if all answered questions have substantive answers before assessment
        for q_idx, qa in st.session_state.Youtube_map.items():
            if not any(is_substantive_answer(ans) for ans in qa["answers"]):
                # This message is static, consider adding translations for it.
                return f"Question {q_idx+1} needs a more detailed answer before completing."
        
        return generate_assessment() # Generate the final assessment
    
    # Handle technical Q&A phase
    elif st.session_state.tech_questions_asked and not st.session_state.conversation_ended:
        questions = [q for q in st.session_state.generated_tech_questions.split('\n') if q.strip()]
        current_q_idx = st.session_state.current_question_idx
        
        # Ensure we don't go out of bounds if questions were skipped or if model generated fewer
        if current_q_idx >= len(questions):
            # This message is static, consider adding translations for it.
            return "You've answered all questions or navigated past them. Say 'done' for your assessment."

        current_question = questions[current_q_idx]
        
        # Initialize question in answer map if not present
        if current_q_idx not in st.session_state.Youtube_map:
            st.session_state.Youtube_map[current_q_idx] = {
                "question": current_question,
                "answers": [],
                "complete": False
            }
        
        # Record current user's answer
        st.session_state.Youtube_map[current_q_idx]["answers"].append(user_input)
        
        # Check if answer is substantive
        if is_substantive_answer(user_input):
            st.session_state.Youtube_map[current_q_idx]["complete"] = True
            st.session_state.current_question_idx += 1 # Move to next question
            
            if st.session_state.current_question_idx < len(questions):
                return questions[st.session_state.current_question_idx] # Return next question
            else:
                # This message is static, consider adding translations for it.
                return "You've answered all questions. Say 'done' for your assessment."
        else:
            # Generate follow-up if answer is insufficient
            tech_stack = st.session_state.candidate_info.get("Tech Stack", "")
            return generate_follow_up(current_question, user_input, tech_stack)
    
    # Handle info collection phase (initial phase)
    elif not st.session_state.info_collected:
        current_lang = st.session_state.get("selected_language", "English")
        extraction_prompt = f"""
        Extract the following from: {user_input}
        Provide as JSON with these fields (use "N/A" if unknown):
        {{
            "Full Name": "...",
            "Email Address": "...",
            "Phone Number": "...",
            "Years of Experience": "...",
            "Desired Position(s)": "...",
            "Current Location": "...",
            "Tech Stack": "..."
        }}
        
        All responses, including confirmations or requests for clarification, MUST be exclusively in {current_lang}.
        """
        try:
            raw_response = st.session_state.chat_session.send_message(extraction_prompt).text
            json_match = re.search(r"```json\n(.*?)```", raw_response, re.DOTALL)
            
            if json_match:
                parsed_info = json.loads(json_match.group(1))
                st.session_state.candidate_info.update(parsed_info)
                
                # Validate extracted info
                all_present, missing, invalid = validate_candidate_info(parsed_info)
                
                if all_present and not invalid:
                    st.session_state.info_collected = True
                    name = st.session_state.candidate_info.get("Full Name", "Candidate").split()[0]
                    
                    # Generate technical questions
                    questions = generate_tech_questions()
                    if questions:
                        st.session_state.generated_tech_questions = "\n".join(questions)
                        st.session_state.tech_questions_asked = True
                        # This message is static, consider adding translations for it.
                        return f"✅ Thanks {name}! First question:\n\n{questions[0]}"
                    else:
                        # This message is static, consider adding translations for it.
                        return "Error generating questions. Please try again."
                else:
                    # These feedback messages are static, consider adding translations for them.
                    feedback = ["Please provide:"]
                    if missing:
                        feedback.append(f"Missing: {', '.join(missing)}")
                    if invalid:
                        feedback.append(f"Invalid: {', '.join(invalid)}")
                    feedback.append("\nExample format: Full Name: John Doe, Email: john@example.com, Tech Stack: Python, SQL")
                    return "\n".join(feedback)
            else:
                # This message is static, consider adding translations for it.
                return "I couldn't extract the information. Please provide details in this format:\nFull Name: John Doe, Email: john@example.com, Tech Stack: Python, SQL"
        
        except Exception as e:
            # This message is static, consider adding translations for it.
            return f"Error processing your information: {e}"
    
    # Default fallback message if no other condition is met
    # This message is static, consider adding translations for it.
    return "I'm not sure how to proceed. Please provide the requested information or answer the current question."

# --- UI Layout ---
# Using columns for sidebar and main chat area
col1, col2 = st.columns([1.2, 3])

with col1: # Sidebar column
    st.image("images.png", use_container_width=True, caption="TalentScout Logo")
    st.markdown('<div class="sidebar-title">About TalentScout</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-desc">Your intelligent recruitment partner for tech talent.</div>', unsafe_allow_html=True)

    # Reset Chat button
    if st.button("🔄 Reset Chat", key="reset"):
        for key in list(st.session_state.keys()):
            del st.session_state[key] # Clear all session state variables
        if os.path.exists(PERSISTENCE_FILE):
            os.remove(PERSISTENCE_FILE) # Delete persistence file
            st.toast("Session and saved data reset!") # User feedback
        st.rerun() # Rerun app to reset UI

    st.markdown("---") # Visual divider

    # --- Language Selector Logic ---
    # Store the previous language to detect a change
    if "prev_selected_language" not in st.session_state:
        st.session_state.prev_selected_language = st.session_state.get("selected_language", "English")

    selected_language_from_ui = st.selectbox(
        "Select Interface Language:",
        ("English", "Spanish", "French", "German", "Japanese", "Hindi"), # Customize available languages
        key="language_selector",
        # Set the default value to the current selected_language from session_state
        # This prevents the dropdown from resetting to "English" on every rerun if a different language was loaded
        index=("English", "Spanish", "French", "German", "Japanese", "Hindi").index(st.session_state.get("selected_language", "English"))
    )

    # Update session state with the new selection
    st.session_state.selected_language = selected_language_from_ui

    # Crucial Logic: Re-initialize chat session if language changes
    if st.session_state.selected_language != st.session_state.prev_selected_language:
        st.session_state.prev_selected_language = st.session_state.selected_language # Update previous state for next rerun
        
        # Re-initialize the chat session with the new language prompt.
        # This tells the LLM to start responding in the new language from now on.
        new_system_history = get_initial_system_prompt(st.session_state.selected_language)
        
        # Preserve existing user/assistant messages but restart the chat session with the new system prompt
        current_chat_history_for_reinit = []
        for msg in st.session_state.messages:
            # Exclude the initial hardcoded welcome message from the LLM's history to avoid duplicates
            if not (msg["role"] == "assistant" and msg["content"].startswith("👋 Hello! I'm **TalentScout**")):
                current_chat_history_for_reinit.append({"role": msg["role"], "parts": [msg["content"]]})
        
        st.session_state.chat_session = model.start_chat(history=new_system_history + current_chat_history_for_reinit)
        
        # Add a message to the chat confirming the language change (optional but good UX)
        language_change_msg = f"Language changed to **{st.session_state.selected_language}**. Please continue the conversation. New responses will be in this language."
        st.session_state.messages.append({"role": "assistant", "content": language_change_msg})
        st.toast(f"Language set to {st.session_state.selected_language}!")
        st.rerun() # Rerun the app to reflect the change immediately

    # Display collected candidate details if available
    if st.session_state.info_collected and st.session_state.candidate_info:
        with st.expander("📝 Candidate Details", expanded=True):
            st.markdown('<div class="candidate-info-box">', unsafe_allow_html=True)
            st.markdown('<h5>Collected Information</h5>', unsafe_allow_html=True)
            for key, value in st.session_state.candidate_info.items():
                if value and str(value).strip().lower() != "n/a":
                    st.markdown(f'<p><strong>{key}:</strong> {value}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

with col2: # Main chat column
    st.markdown("## TalentScout")
    st.markdown("### AI Hiring Assistant")

    # Display chat messages in the main chat area
    for msg in st.session_state.messages:
        role_class = "assistant" if msg["role"] == "assistant" else "user"
        st.markdown(
            f'<div class="message {role_class}">{msg["content"]}</div>',
            unsafe_allow_html=True
        )

    # Chat input form at the bottom
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Type your message here...", 
            key="chat_input", 
            disabled=st.session_state.conversation_ended,
            placeholder="Type your answer or say 'next'/'back' to navigate questions"
        )
        submitted = st.form_submit_button(
            "Send", 
            use_container_width=True, 
            disabled=st.session_state.conversation_ended
        )

        # Process user input if form is submitted and input is not empty
        if submitted and user_input.strip():
            st.session_state.messages.append({"role": "user", "content": user_input}) # Add user message to history
            response = handle_user_input(user_input) # Get response from chat logic
            st.session_state.messages.append({"role": "assistant", "content": response}) # Add assistant response to history
            save_state() # Save current state
            st.rerun() # Rerun to update the chat display
