import streamlit as st
import os
import openai

from streamlit.web.server.websocket_headers import _get_websocket_headers
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType

#Azure Search and OpenAI endpoints

AZURE_SEARCH_SERVICE =  "aidemo666-search"
AZURE_SEARCH_INDEX = "liebherr1"
AZURE_OPENAI_SERVICE =  "openaidemo666"
AZURE_OPENAI_GPT_DEPLOYMENT =  "gpt-35-turbo"
AZURE_OPENAI_CHATGPT_DEPLOYMENT =  "chat-gpt-35-turbo"

KB_FIELDS_CONTENT = "content"
KB_FIELDS_REQ_A = "requirement_area"
KB_FIELDS_REQ_D =  "requirement_detail"
KB_FIELDS_DELI_A=  "delivery_approach"
KB_FIELDS_TECH_A =  "technical_assumptions"
KB_FIELDS_FILE = "metadata_storage_name"
KB_FIELDS_SYSTEM = KB_FIELDS_CONTENT+"/"+"system"
KB_FIELDS_SEMANTIC_PROFILE = "default"

AZ_SEARCH_KEY = os.getenv('AZ_SEARCH_KEY', default='')
AZ_AI_KEY = os.getenv('AZ_AI_KEY', default='')

search_key = AzureKeyCredential(AZ_SEARCH_KEY)

ai_key = AZ_AI_KEY

# Used by the OpenAI SDK
openai.api_type = "azure"
openai.api_base = f"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"
openai.api_version = "2022-12-01"
openai.api_key = ai_key

# Set up clients for Cognitive Search and Storage
search_client = SearchClient(
    endpoint=f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
    index_name=AZURE_SEARCH_INDEX,
    credential=search_key)

# button_click to run AI (and search)

def button_click ():

    system = st.session_state.system
    full_system_name = "Salesforce"

    if system == 'D365':
        full_system_name = "Dynamics 365"
    elif system == 'SF':
        full_system_name = "Salesforce"

    requirement_area = st.session_state.requirement_area
    requirement_detail = st.session_state.requirement_detail

    ### Project Assumptions

    assumption = st.session_state.assumption

    ## filter for specific system
    filter = ""+KB_FIELDS_SYSTEM+" eq '{}'".format(system.replace("'", "''")) 

    r = search_client.search(requirement_detail, 
                         filter=filter,
                         query_type=QueryType.SEMANTIC, 
                         query_language="en-us", 
                         query_speller="lexicon", 
                         semantic_configuration_name=KB_FIELDS_SEMANTIC_PROFILE, 
                         top=4)
    # Iterate over the results and store in data
    data = []
    i=0
    for result in r:
        res = []
        res.append (result[KB_FIELDS_FILE][:-5])
        res.append (result[KB_FIELDS_CONTENT][KB_FIELDS_REQ_A].replace("\n", " ").replace("\r", "")) 
        res.append (result[KB_FIELDS_CONTENT][KB_FIELDS_REQ_D].replace("\n", " ").replace("\r", "")) 
        res.append (result[KB_FIELDS_CONTENT][KB_FIELDS_DELI_A].replace("\n", " ").replace("\r", "")) 
        res.append (result[KB_FIELDS_CONTENT][KB_FIELDS_TECH_A].replace("\n", " ").replace("\r", ""))
        print(res)
        data.append (res)
    
    requirements =""
    ## Loop thorugh data (max 3 examples)
    #print (len(data))
    i = 1
    if (len(data)<1):
        raise SystemExit("Stop right there! No requirement examples!")
    else:
        for req in data:
            requirements+=f"""\n[Requirement{req[0]}] "Requirement area" ="{req[1]}", "Requirement detail"="{req[2]}". "Delivery approach"="{req[3]}", "Technical assumptions"="{req[4]}""" 
            i+=1
    
    assumptions = f"""Also follow general assumptions for entire system:
{assumption}
"""

    prompt =f"""<|im_start|>system
Assistant helps users to prepare descriptions for the system requirements based on {full_system_name}.
Generate answers from similar requirements below as much as possible. 
{assumptions}
Each requirement has a name followed by colon and the actual information, always include the requirement name for each fact you use in the response. Use square brackets to reference the source, e.g. [Requirement1]. Don't combine sources, list each source separately, e.g. [Requirement1][Requirement2].
Each requirement is later divided into 4 parts: "Requirement area", "Requirement detail", "Delivery approach", "Technical assumptions" followed by equal sign and the actual information. "Delivery approach" and "Technical assumptions" are responses to "Requirement area", "Requirement detail". Requirements listed below are a source of information. In response, respond using data from "Requirement detail" and "Requirement area" from users' questions. Provide both "Delivery approach" and "Technical assumptions" in response.

Requirements:{requirements}
<|im_end|>
<|im_start|>user
Please provide "Delivery approach" and "Technical assumptions" for "Requirement area" ="{requirement_area}" and "Requirement detail"="{requirement_detail}"
<|im_end|>
<|im_start|>assistant
"""
    st.session_state.expand = prompt

    response = openai.Completion.create(
        engine=AZURE_OPENAI_CHATGPT_DEPLOYMENT,
        prompt=prompt,
        temperature=0.7,
        max_tokens=400,
        top_p=0.7,
        n=3,
        frequency_penalty=0,
        presence_penalty=0,
        stop="<|im_end|>")
    
    st.session_state.choice1 = response["choices"][0]["text"]
    st.session_state.choice2 = response["choices"][1]["text"]
    st.session_state.choice3 = response["choices"][2]["text"]

#streamlit webpage


st.set_page_config(initial_sidebar_state="collapsed",layout="wide")

hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)
st.write('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

#checking PwC domain

headers = _get_websocket_headers()

#for key in headers:
#    st.text(key+ '->'+ headers[key])

email = headers.get("X-Ms-Client-Principal-Name")

if email is None:
    #no header, need to stop :(
    st.text("E: not allowed")
    st.stop()

domain = email[email.index('@') + 1 : ]

if domain.lower() =='pwc.com':
# authenticated user
    st.text("I am from PwC!")
#
else: 
    st.text("W: not allowed")
    st.stop()

# Page title
#st.set_page_config(page_title='🤖 Requirement analyzer')
st.title('🤖 Requirement analyzer')

#Side by side
input,  output = st.columns(2)

# Text input
system = input.selectbox('Pick a system', ['D365', 'SF'],key='system')
requirement_area = input.text_input('Requirement area',key='requirement_area')

requirement_detail = input.text_area('Requirement detail', '',key='requirement_detail')
assumption = input.text_area('Assumptions', '',key='assumption')

if input.button('Generate!'):
    button_click()

#Output

choice_1 = output.text_area('Choice 1','',key="choice1")

choice_2 = output.text_area('Choice 2','',key="choice2")

choice_3 = output.text_area('Choice 3','',key="choice3")

st.divider()



expander = st.expander("More details...",expanded=False)
expander.text_area('AI prompt','Hit Generate button to generate AI response',key='expand')
