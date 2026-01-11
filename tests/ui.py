import streamlit as st
import os
import uuid
from pathlib import Path

from qwshen.launcher import Launcher

##########################################################################################################
# Note: 
#  In order to run this test, please run by_schedule.py first to index the documents used in this test.
#
# To launch the UI, please run the following command:
#  streamlit run ./tests/ui.py -- --def ./tests/defs/chat/chat.json --env ./tests/application.env
#
##########################################################################################################

# session id
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# services
if "services" not in st.session_state:
    tests_dir = Path(__file__).resolve().parent.parent
    os.environ["PROMPTS_DIRECTORY"] = str(tests_dir / "tests/chat/prompts")

    _, services = Launcher.start()
    st.session_state.services = services

if "cur_service" not in st.session_state:
    st.session_state.cur_service = st.session_state.services[0][0].get_name() if st.session_state.services is not None and len(st.session_state.services) > 0 else None

if st.session_state.cur_service is not None:        
    # retrieve the prompt for the current service
    st.session_state.cur_prompt = ""

# Streamed response emulator
def response_generator(user_query):
    if st.session_state.cur_service is None:
        yield "No service is selected."
    else:   
        selected_services = [service for service, _ in st.session_state.services if service.get_name() == st.session_state.cur_service]
        if len(selected_services) == 0:
            yield f"Service: {st.session_state.cur_service} is not found."
        cur_service = selected_services[0]
        for message in cur_service.process(user_query, kwargs={"session_id": st.session_state.session_id}):
            yield message.content if message is not None else "\n"

st.title("Please ask any")
st.markdown(
    """
        <style>
            .st-emotion-cache-1c7y2kd {
                flex-direction: row-reverse;
                text-align: right;
            }
            .st-key-service_toggle {
                position: fixed;
                top: 64px;
                right: 32px;
                width: 320px;
                z-index: 9001;
            }
        </style>
    """,
    unsafe_allow_html=True
)

with st.container(key="service_toggle"):
    st.selectbox (
        label = 'Select Service', 
        options = [service.get_name() for service, _ in st.session_state.services],
        key = "cur_service",
        label_visibility = "collapsed",
    )

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = st.write_stream(response_generator(prompt))
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})

