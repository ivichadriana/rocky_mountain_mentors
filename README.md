# Rocky Mountain Mentors Presents: ALICIA
ALICIA is a custom GPT that uses RAG to help students access important information.

## Initial set-up (using macOS - for now):

### Make sure you have an OpenAI API key. This should go inside /ALICIA_GPT_Model/.env defined as PENAI_API_KEY={your key}

### 1. Rebuild env from scratch: in terminal:
chmod +x environment_builder.sh
./environment_builder.sh

### 2. Activate environment! (in terminal)
conda activate rmm-llm                    
     
### 3. Run the model; either Jupyter NB of Python script (method of choice).
python ALICIA.py or within ALICIA.ipynb

### This will start ALICIA chatbot. ALICIA's customization can be found in rocky_mountain_mentors/data/rmm_corpus/agent_description.txt, and the resources.txt file contains the informaiton ALICIA accessed while answering.
     