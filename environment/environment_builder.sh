#!/usr/bin/env bash
# environment_builder.sh
# Creates a Conda environment “rmm-llm” ready for:
#   • Tkinter GUI work
#   • RAG with FAISS
#   • Jupyter notebooks (kernel + widgets)
#   • OpenAI client & helpers

set -e  # abort on any error

ENV_NAME="rmm-llm"

# 1. Create the environment with Python 3.11
conda create -n "$ENV_NAME" python=3.11 -y

# 2. Activate the env (enable Conda in non-interactive shells first)
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"

# 3. Core GUI & scientific libs via Conda (pulling from conda-forge for FAISS)
conda install -y \
    tk \
    faiss-cpu \
    ipykernel \
    ipywidgets \
    jupyterlab \
    -c conda-forge

# 4. Python packages via pip (latest versions)
pip install --upgrade \
    openai \
    tiktoken \
    python-dotenv \
    pillow

echo ""
echo "Environment '$ENV_NAME' is ready."
echo "Run 'conda activate $ENV_NAME' to start using it."
