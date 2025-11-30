import streamlit as st
import os
import re
import ast
import requests

from launcher import Launcher

#
# run the following command:
#  streamlit run ./src/rag_ui.py -- --def ./resources/definition.json --env ./resources/application.env
#

# services
if "services" not in st.session_state:
    st.session_state.services = Launcher.start()

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
        for query_response in cur_service.process(user_query):
            yield query_response.get("answer", "")

st.title("Please ask your question")
st.markdown(
    """
        <style>
            .st-emotion-cache-4oy321 {
                flex-direction: row-reverse;
                text-align: left;
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
    c_service_list, c_service_info = st.columns([7, 4])
    with c_service_list:
        st.selectbox (
            label = 'Select Service', 
            options = [service.get_name() for service, _ in st.session_state.services],
            key = "cur_service",
            label_visibility = "collapsed",
        )
    with c_service_info:
        with st.popover("Prompt", use_container_width=False):
            st.markdown(
                """
                <style>
                textarea {
                    width: 480px !important;
                    min-width: 480px !important;
                    max-width: 100% !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )            
            st.text_area(
                label="Prompt",
                key = "cur_prompt",
                height=160,
                label_visibility="collapsed"
            )
            col1, col2 = st.columns([4, 1])
            with col2:
                st.button("Apply", type="primary")

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

