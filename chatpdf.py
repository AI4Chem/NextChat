"""
ChatPDF

ChatPDF is a Streamlit application that allows users to upload PDF and DOCX files
and then ask questions related to the content of those documents.
The content of the documents is indexed and vectorized to allow for natural
language interactions. The application uses the OpenAI API to power the conversational
interface, FAISS for fast similarity search, and various other utilities to parse
and handle document content.

Functions:
----------
- parse_docx(data: bytes) -> str:
    Parse a DOCX file and return its textual content.

- get_text(docs: list) -> str:
    Extract and combine the textual content of a list of uploaded PDF and DOCX files.

- get_chunks(data: str) -> list:
    Split the provided text into manageable chunks based on characters.

- get_vector(chunks: list) -> FAISS:
    Convert a list of text chunks into vectors using OpenAI embeddings and store them using FAISS.

- get_llm_chain(vectors: FAISS) -> ConversationalRetrievalChain:
    Create a conversational retrieval chain instance ready for processing user queries 
    using the provided set of vectors.

- main() -> None:
    The main function initializes and runs the Streamlit application. It handles 
    the file uploads, user input, and displays bot responses.

If you run this module directly, it will start the Streamlit application where you can
upload PDFs and DOCX files, and then interact with their content using natural language queries.
"""


import os

import streamlit as st
from docx import Document
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain_core.messages.human import HumanMessage
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain_community.embeddings.spacy_embeddings import SpacyEmbeddings
from langchain.memory import ConversationBufferMemory
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from PyPDF2 import PdfReader
from langchain.chains import (
    StuffDocumentsChain, LLMChain, ConversationalRetrievalChain
)
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import OpenAI
from langchain.chains import StuffDocumentsChain, LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import OpenAI
import json

os.environ["OPENAI_API_KEY"] = "sk-123"
os.environ["OPENAI_API_BASE"] = "http://10.140.24.111:10086/v1"

import chromadb
chroma_client = chromadb.Client()


def parse_docx(data):
    """
    Parse and extract text content from a DOCX file.

    Parameters:
    -----------
    data : bytes
        The binary content of the DOCX file.

    Returns:
    --------
    str
        The extracted text content from the DOCX file.
    """
    document = Document(docx=data)
    content = ""
    for para in document.paragraphs:
        data = para.text
        content += data
    return content

def get_text(docs):
    """
    Extract textual content from a list of uploaded PDF files.

    Parameters:
    -----------
    docs : list
        List of uploaded PDF files.

    Returns:
    --------
    str
        The combined textual content of all the provided PDFs.
    """
    doc_text = ""
    for doc in docs:
        if ".pdf" in doc.name:
            pdf_reader = PdfReader(doc)
            for each_page in pdf_reader.pages:
                doc_text += each_page.extract_text()
            doc_text += "\n"
        elif ".docx" in doc.name:
            doc_text += parse_docx(data=doc)

    return doc_text


def get_chunks(data):
    """
    Splits the provided text data into manageable chunks.

    Parameters:
    -----------
    data : str
        Text data that needs to be split.

    Returns:
    --------
    list
        A list containing chunks of the provided text data.
    """
    text_splitter = CharacterTextSplitter(
        separator="\n", chunk_size=1000, chunk_overlap=50, length_function=len
    )
    text_chunks = text_splitter.split_text(data)
    return text_chunks


def get_vector(chunks):
    """
    Generate vectors from text chunks using FAISS vector store and OpenAI embeddings.

    Parameters:
    -----------
    chunks : list
        List of text chunks that need to be vectorized.

    Returns:
    --------
    FAISS
        FAISS vector store containing vectors of the provided text chunks.
    """
    return FAISS.from_texts(texts=chunks, embedding=OpenAIEmbeddings())

import os
from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
    base_url=os.environ.get("OPENAI_API_BASE")
)

class Bot:
    def __init__(self,):
        pass

    def create_indexing(self,text_chunks):
        collection = chroma_client.create_collection(name='a'+str(hash(tuple(text_chunks)))[1:24] + 'b')
        print(len(text_chunks))
        collection.add(documents=text_chunks,ids=[str(i) for i,ix in enumerate(text_chunks)])
        return collection

    def query_chunks(self,texts,collection,n):
        results = collection.query(
        query_texts=texts,
        n_results=n
        )
        print(results)
        return results

    def template(self,query_results,text,file_name):
        print(type(query_results))
        resources = []
        for filename,res in zip(file_name.split('\n'),query_results['documents']):
            res_text = '\n'.join(res)
            resources.append(f'RELATED RESOURCES FROM file`{filename}`:\n{res_text}')
        resources = "\n\n".join(resources)
        return f'''Now You are reading the pdf files:
{file_name}
{resources}
USER QUERY:{text}
please give a anser to user query according to RELATED RESOURCES.
'''

    def ask(self,text,collection,file_name,history=[]):
        results = self.query_chunks(text,collection,2)
        question = self.template(results,text,file_name)
        print(question)
        messages = []
        for i,ix in enumerate(history):
            if i % 2 == 0:
                role = 'user'
            else:
                role = 'assistant'
            messages.append({
                "role": role,
                "content": ix,
            })
        messages += [
            {
                "role": "user",
                "content": question,
            }
        ]
        chat_completion = client.chat.completions.create(
        messages=messages,
        model="gpt-3.5-turbo",
        temperature=0.4
        )
        resp = chat_completion.choices[-1].message.content
        history += [text,resp]
        return history


def main():
    """
    Main function to initialize the Streamlit application.
    Handles file uploads, user queries, and bot responses.

    Returns:
    --------
    None
    """
    st.set_page_config(page_title="Read PDF with ChemLLM.")
    st.title("Read PDF📄 with ChemLLM.")

    if not "bot" in st.session_state:
        st.session_state.bot = None

    if not "chat_history" in st.session_state:
        st.session_state.chat_history = []

    if not "doc_len" in st.session_state:
        st.session_state.doc_len = 0
    
    if not 'collection' in st.session_state:
        st.session_state.collection = None
    
    if not 'filename' in st.session_state:
        st.session_state.filename = ''

    user_input = st.text_input("Ask any question related to the pdf")
    if user_input and st.session_state.bot:
        bot_response = st.session_state.bot.ask(user_input,st.session_state.collection,st.session_state.filename,st.session_state.chat_history)
        st.session_state.chat_history = bot_response
        for idx, msg in enumerate(st.session_state.chat_history):
            if idx % 2 == 0:
                with st.chat_message("user"):
                    st.write(msg)
            else:
                with st.chat_message("assistant"):
                    st.write(msg)

    elif user_input and not st.session_state.bot:
        st.error("Please upload files and click proceed before asking questions")

    with st.sidebar:
        st.subheader("About")

        docs = st.file_uploader(
            "Upload PDF and click proceed", accept_multiple_files=True
        )

        if len(docs) > st.session_state.doc_len:
            st.session_state.doc_len = len(docs)
            with st.spinner("Processing..."):
                st.session_state.filename = "\n".join([doc.name for doc in docs])
                doc_text = get_text(docs)
                doc_chunks = get_chunks(doc_text)
                # vectors = get_vector(doc_chunks)
                st.session_state.bot = Bot()
                st.session_state.collection = st.session_state.bot.create_indexing(doc_chunks)

    with st.chat_message("assistant"):
        st.write("Hello, Please upload your files and click proceed to ask questions.")


if __name__ == "__main__":
    main()
