
''' Chat swith PDF documents using Nvidia
client and LangChain libraries.

Notes:
  Choose between pre-trained LLM models

Usage:    
        main_rag_pdf.py

optional arguments:
  -h, --help                Show this help message and exit

Author:   Boris Duran
Email:    boris@yodir.com
Created:  2024-06-17
'''

import os
import argparse
#import time
import getpass

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredMarkdownLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter

def get_nvidia_key():
    # del os.environ['NVIDIA_API_KEY']  ## delete key and reset
    if os.environ.get("NVIDIA_API_KEY", "").startswith("nvapi-"):
        print("Valid NVIDIA_API_KEY already in environment. Delete to reset")
    else:
        nvapi_key = getpass.getpass("NVAPI Key (starts with nvapi-): ")
        assert nvapi_key.startswith("nvapi-"), f"{nvapi_key[:5]}... is not a valid key"
        os.environ["NVIDIA_API_KEY"] = nvapi_key
    
    return os.environ["NVIDIA_API_KEY"]

def get_model( models ):
    """Shows a list of available LLMs and returns the user's selection .
    Args:
      None
    Returns:
      model_name (str): Name of the selected LLM.
    """
    models_list = []
    for ix, model in enumerate(models):
        if model.model_type == 'chat':
            models_list.append(model.id)
    
    models_dict = {}
    for ix, model in enumerate(sorted( models_list )):
        models_dict[ix] = model
        print(f'{ix:>3}: {model}')

    model_ix = int( input( f'Choose your LLM: ' ) )
    if model_ix < len(models_dict): 
        ix_exist = True
        model_name = models_dict[model_ix]

    return model_name

def get_pdf_langchain( path ):
    if os.path.isdir(path):
        print('Argument is a folder!')
        #print(len([name for name in os.listdir(path) if os.path.isfile(os.path.join(path, name))]))
        documents = []
        for ix, file in enumerate(os.listdir(path)):
            if file.endswith('.pdf'):
                pdf_path = os.path.join(path, file)
                print(f'Loading {file} ...', end='')
                loader = PyMuPDFLoader(pdf_path)
                print(' done!')
                pages = loader.load_and_split()
                documents.extend( pages )
    else:
        print('Argument is a file!')
        print(f'Loading {path} ...', end='')
        loader = PyMuPDFLoader(path)
        print(' done!')
        print('Splitting in chunks:', end='')
        pages = loader.load_and_split()
        print(' ... done!')
        documents = pages
    print('Documents: ', len(documents))

    return pages

def main_loop( args ):
    """Main loop where all magic happens!
    Args:
      None
    Returns:
      None
    """
    api_key_nvidia = get_nvidia_key()
    model_name = get_model(ChatNVIDIA.get_available_models())

    print(60 * '-')
    print('Working with model:', model_name)
    print('===> Press Ctrl+C to exit! <===')

    llm = ChatNVIDIA(model=model_name, api_key=api_key_nvidia)
    emb = NVIDIAEmbeddings(model="NV-Embed-QA", truncate="END", api_key=api_key_nvidia)

    docs = get_pdf_langchain( args.document )

    vectorstore = FAISS.from_documents( docs, emb )
    retriever = vectorstore.as_retriever()
    
    prompt = ChatPromptTemplate.from_messages(
        [("system", "Answer solely based on the following context:\n<Documents>\n{context}\n</Documents>",),
         ("user", "{question}"),]
    )

    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    try:
        while True:
            print(60 * '-', '\n')
            query_txt = input( f'Enter your prompt (Ctrl+C to exit!): ' )
            print()
            for chunk in chain.stream( query_txt ):
                print(chunk, end="", flush=True)
            print()
    except KeyboardInterrupt:
        print('Bye!')
    print()

    return

if __name__ == '__main__':
    print(80 * '-')
    print("NVIDIA's Contest".center(80))
    print(80 * '-')

    parser = argparse.ArgumentParser(description='Chat with your documents')
    parser.add_argument('-d', '--document', help='Path to document to be ingested [PDF].')

    args = parser.parse_args()
    main_loop( args )

    print(80 * '-')
    print("The end!".center(80))
    print(80 * '-')
