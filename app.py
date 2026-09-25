import streamlit as st
import input_fetch_convert
import extract_info
import check_info_followup
import generate_report_recommendation
import base64
from langsmith import traceable

st.set_page_config(page_title="AI Emergency Voice Intelligence System")


@traceable(name="emergency-voice-intelligence-system")
def set_seamless_bg_with_sidebar_border(image_file):
    with open(image_file, "rb") as file:
        encoded_string = base64.b64encode(file.read())
    st.markdown(
        f"""
        <style>
        /* Apply background to the entire application wrapper */
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/png;base64,{encoded_string.decode()}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        /* Make sidebar transparent so the image flows through */
        [data-testid="stSidebar"] {{
            background-color: transparent !important;
            background-image: none !important;

            /* EXPLICIT SIDEBAR BORDERS & SEPARATION */
            border-right: 2px solid rgba(255, 90, 69, 0.4) !important;
            box-shadow: 5px 0px 15px rgba(0, 0, 0, 0.5);

            /* Subtle dark tint overlay so text remains readable */
            background-image: linear-gradient(
                rgba(18, 23, 42, 0.75),
                rgba(18, 23, 42, 0.75)
            ) !important;
        }}

        [data-testid="stSidebarHeader"] {{
            background-color: transparent !important;
        }}

        .stApp h1, .stApp h2, .stApp h3 {{
            border-bottom: 3px solid #FF5A45;
            padding-bottom: 0.35rem;
        }}

        .stButton > button {{
            background-color: #FF5A45;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            font-weight: 600;
        }}

        .stButton > button:hover {{
            background-color: #e14a36;
            color: #ffffff;
        }}

        [data-testid="stJson"] {{
            background-color: #12172A;
            border: 1px solid #FF5A45;
            border-radius: 10px;
            padding: 0.75rem;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )


set_seamless_bg_with_sidebar_border("assets/emergency_bg.png")

st.markdown(
    "<h1 style='text-align: center;'>🚨 AI Emergency Voice Intelligence System</h1>",
    unsafe_allow_html=True,
)

if "transcripts" not in st.session_state:
    st.session_state.transcripts = []

if "extracted_info" not in st.session_state:
    st.session_state.extracted_info = {
        "emergency_type": "Unknown",
        "location": "Unknown",
        "people_involved": "Unknown",
        "injuries": "Unknown",
        "severity": "Unknown",
    }

if "followup_questions" not in st.session_state:
    st.session_state.followup_questions = []

if "report" not in st.session_state:
    st.session_state.report = ""

if "recommendation" not in st.session_state:
    st.session_state.recommendation = ""


audio, duration = input_fetch_convert.record_audio()

if audio is not None and st.button("Submit Recording"):
    with st.spinner("🎙️ Recording received — processing..."):
        query = input_fetch_convert.speech_to_text(audio)

        if query:  
            st.session_state.transcripts.append({
                "text": query,
                "duration": duration,
            })

            # Extract factual information from the latest caller message.
            current_info = extract_info.extract_info(query)

            # Merge it with facts collected in previous turns.
            merged_info, missing_fields = check_info_followup.check_missing_fields(
                current_info,
                st.session_state.extracted_info,
            )

            # Derive severity from the complete accumulated incident state.
            # The caller never asked to choose a severity level.
            merged_info["severity"] = extract_info.assess_severity(merged_info)

            st.session_state.extracted_info = merged_info
            st.session_state.followup_questions = check_info_followup.ask_follow(
                missing_fields
            )

            # 4. Generate the final outputs once all factual required fields exist.
            if not st.session_state.followup_questions:
                complete_transcript = " ".join(
                    item["text"]
                    for item in st.session_state.transcripts
                )

                st.session_state.report = (
                    generate_report_recommendation.generate_report(
                        complete_transcript
                    )
                )

                st.session_state.recommendation = (
                    generate_report_recommendation.generate_recommendation(
                        st.session_state.extracted_info
                    )
                )
            else:
                st.session_state.report = ""
                st.session_state.recommendation = ""

    if query:
        st.toast("✅ Information captured from this recording.")
        if not st.session_state.followup_questions:
            st.success("✅ All required information collected — report generated.")
    else:
        st.error("No speech could be detected.")


for question in st.session_state.followup_questions:
    st.warning(question)


with st.sidebar:
    st.markdown(
        "<h1 style='text-align: center;'>📝 Transcript</h1>",
        unsafe_allow_html=True,
    )

    for item in st.session_state.transcripts:
        st.markdown(item["text"])
        st.caption(f"Audio duration: {item['duration']:.1f} seconds")


st.header("📋 Extracted Info")
st.json(st.session_state.extracted_info)

if st.session_state.report:
    st.header("📄 Incident Report")
    st.markdown(st.session_state.report)

if st.session_state.recommendation:
    st.header("🧭 Recommended Steps")
    st.markdown(st.session_state.recommendation)