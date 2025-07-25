
# # Rocky Moutain Mentors: Using OpenAI's API for ALICIA: Academic Learning and Institutional Coaching Intelligent Assistant

# The following script contains the code to run a demo showcasing our custom GPT for the Rocky Mountain Mentors cooproporation.

# ## Imports, paths and setting

# %%
# imports & configuration
import os, pathlib, json, textwrap
from dotenv import load_dotenv
import openai
import tiktoken
import faiss
import numpy as np
import markdown, re
from pathlib import Path
from tkhtmlview import HTMLScrolledText     # instead of HTMLLabel
import datetime as dt
import os
from dotenv import load_dotenv, find_dotenv
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from tkinter import font as tkfont
from pathlib import Path
from PIL import Image, ImageTk
import threading

load_dotenv()                           # grabs OPENAI_API_KEY from .env
openai.api_key = os.getenv("OPENAI_API_KEY")

# Path of the script’s parent folder …/rocky_mountain_mentors
PROJECT_ROOT = Path.cwd().parent

CORPUS_PATH = PROJECT_ROOT / "data" / "rmm_corpus" / "resources.txt"
print(CORPUS_PATH)          # sanity-check
assert CORPUS_PATH.exists(), f"{CORPUS_PATH} not found."

AGENT_DESC_PATH = PROJECT_ROOT / "data" / "rmm_corpus" / "agent_description.txt"

EMBED_MODEL = "text-embedding-3-small"  # fast & inexpensive; switch if needed
TOKENIZER = tiktoken.encoding_for_model("gpt-4o")  # for length management
MAX_TOKENS_CONTEXT = 3000               # adjust for your target model

# ## Load & embed the corpus

# %%
#  read the corpus and split into passages
raw_text = CORPUS_PATH.read_text(encoding="utf-8")

# naive split by double-newline; you can swap in langchain text splitters later
passages = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
print(f"Loaded {len(passages)} passages.")

# %%
# embed passages and build a FAISS index (runs once; cache if large)
def embed(texts):
    resp = openai.embeddings.create(model=EMBED_MODEL, input=texts)
    return np.array([d.embedding for d in resp.data], dtype="float32")

emb_vectors = embed(passages)
index = faiss.IndexFlatIP(emb_vectors.shape[1])
index.add(emb_vectors)

print("FAISS index ready:", index.ntotal, "vectors")

# %%
print("dotenv found at:", find_dotenv())   # should show the absolute path

load_dotenv(find_dotenv())                 # explicit path, avoids guesswork
key = os.getenv("OPENAI_API_KEY")
print("Key length:", len(key) if key else key)
assert key and key.startswith("sk-"), "OPENAI_API_KEY is missing or malformed!"

#  Retrieval helper

# %%
# semantic search
def retrieve(query, k=4):
    q_vec = embed([query])[0].reshape(1, -1)
    scores, idxs = index.search(q_vec, k)
    return [(passages[i], float(scores[0][j])) for j, i in enumerate(idxs[0])]


# System prompt & conversation loop

# %%
SYSTEM_DESC = AGENT_DESC_PATH.read_text(encoding="utf-8").strip()
print("Loaded system prompt –", len(SYSTEM_DESC.split()), "words")

# %%
# ---------- 1) persistent memory ---------- #
student_profile = {}          # cleared each time you restart the process
conversation    = []          # running message list

def parse_student_info(text):
    """
    Very simple heuristic:
      • program keywords PhD|MS|Bachelor
      • year = 1–6  (or words like freshman, sophomore...)
    Modify as needed!
    """
    prog = None
    year = None

    program_match = re.search(r"\b(PhD|PHD|MS|M\.?S\.?|Bachelor'?s?)\b", text, re.I)
    if program_match:
        prog = program_match.group(1).upper().replace(".", "")
        if prog.startswith("B"):
            prog = "Bachelor's"

    # numeric year
    year_match = re.search(r"\b([1-6])(?:st|nd|rd|th)?\s*year\b", text, re.I)
    if year_match:
        year = int(year_match.group(1))
    else:
        # common words
        words = {"freshman":1,"sophomore":2,"junior":3,"senior":4}
        for w,n in words.items():
            if w in text.lower():
                year = n
                break
    return prog, year

# %%
def build_prompt(user_message):
    # 1️⃣ base & personalization
    sys_base = {"role": "system", "content": SYSTEM_DESC}

    if student_profile:
        sys_personal = {"role": "system",
                        "content": f"Student program: {student_profile['program']}, "
                                   f"Year: {student_profile['year']}."}
    else:
        sys_personal = {"role": "system",
                        "content": ("Ask once for program + year, then remember.")}

    # 2️⃣ embed retrieval
    docs = retrieve(user_message, k=5)
    context = "\n\n".join(f"{i+1}. {d[0]}" for i, d in enumerate(docs))

    # 3️⃣ hard rule + context wrapped together
    assistant_context = {
        "role": "assistant",
        "content": (
            "**Grounding data – you MUST base your answer ONLY on these excerpts. "
            "If they don’t contain the answer, reply 'I don’t have that information, but I searched online and found {then search online and find a reliable source like the program website, find the answer and return the answer AND your source link}. Everything should be specific to the University of Colorado Anschutz Medical Campus and Denver campus, as well as the student's current program and year.'**\n\n"
            + context)
    }

    # 4️⃣ assemble (context is *immediately* before user)
    return [sys_base, sys_personal] + conversation + [
            assistant_context,
            {"role": "user", "content": user_message}]

def chat(user_message, model="gpt-4o-mini"):
    global student_profile, conversation

    # send the prompt
    messages = build_prompt(user_message)
    response = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=512,
    ).choices[0].message.content.strip()

    # 4) If we have no profile yet, try to parse it from the *user* message
    if not student_profile:
        prog, yr = parse_student_info(user_message)
        if prog and yr:
            student_profile = {"program": prog, "year": yr}

    # 5) Append turn to running conversation
    conversation.extend([
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": response},
    ])
    return response

# %%
conversation.clear()
student_profile.clear()

# Quick sanity test

# %%
# ---------- 1) persistent memory ---------- #
student_profile = {}          # cleared each time you restart the process
conversation    = []          # running message list

def parse_student_info(text):
    """
    Very simple heuristic:
      • program keywords PhD|MS|Bachelor
      • year = 1–6  (or words like freshman, sophomore...)
    Modify as needed!
    """
    prog = None
    year = None

    program_match = re.search(r"\b(PhD|PHD|MS|M\.?S\.?|Bachelor'?s?)\b", text, re.I)
    if program_match:
        prog = program_match.group(1).upper().replace(".", "")
        if prog.startswith("B"):
            prog = "Bachelor's"

    # numeric year
    year_match = re.search(r"\b([1-6])(?:st|nd|rd|th)?\s*year\b", text, re.I)
    if year_match:
        year = int(year_match.group(1))
    else:
        # common words
        words = {"freshman":1,"sophomore":2,"junior":3,"senior":4}
        for w,n in words.items():
            if w in text.lower():
                year = n
                break
    return prog, year

# Minimal Tkinter front-end

# %%
# ───────────── Palette ─────────────
HEADER_BG = "#3c6834"   # soft green
WINDOW_BG = "#c5b78a"   # light gold
CHAT_BG   = "#f9f5e9"   # creamy off-white
USER_BG = "#e9dfba"
BOT_BG    = "#f9f5e9" 
ACCENT    = "#a46d5e"
TEXT_DARK = "#000000"
TEXT_LIGHT= "#ffffff"

# ───────────── Root window ─────────────
root = tk.Tk()
root.title("Rocky Mountain Mentors (2025)")
root.configure(bg=WINDOW_BG)
root.geometry("910x650")

# ───────────── Font selection (after root exists) ─────────────
available_fonts = set(tkfont.families(root))
base_font = ("SF Pro Text" if "SF Pro Text" in available_fonts
             else "Helvetica Neue" if "Helvetica Neue" in available_fonts
             else "Helvetica")
SYSTEM_FONT = (base_font, 13)
TITLE_FONT  = (base_font, 26, "bold")

# ───────────── ttk styling ─────────────
style = ttk.Style(root)
style.theme_use("clam")
style.configure("TFrame",  background=WINDOW_BG)
style.configure("Header.TFrame", background=HEADER_BG)
style.configure("TButton", background=ACCENT, foreground=TEXT_LIGHT,
                font=SYSTEM_FONT, borderwidth=0)
style.map("TButton",
          background=[("active", HEADER_BG), ("pressed", HEADER_BG)])

# ───────────── Header (logo + title) ─────────────
# ───────────── Header (slim bar w/ big logo) ─────────────
HEADER_HEIGHT = 50                            # exact green-bar height
header = ttk.Frame(root, style="Header.TFrame", height=HEADER_HEIGHT)
header.pack(fill="x", pady=(4, 3))
header.pack_propagate(False)                     # prevent auto-expansion

LOGO_W = 75                                    # logo is wide
logo_path = Path.cwd().parent / "data" / "RMM_logo_cropped.png"
if logo_path.exists():
    # Resize keeping aspect ratio; the image height may exceed HEADER_HEIGHT,
    # which is fine—the frame will crop it vertically.
    logo_img = Image.open(logo_path)
    w_percent = LOGO_W / float(logo_img.width)
    new_size = (LOGO_W, int(logo_img.height * w_percent))
    logo_img = logo_img.resize(new_size, Image.LANCZOS)
    logo_photo = ImageTk.PhotoImage(logo_img)
    tk.Label(header, image=logo_photo, bg=HEADER_BG)\
      .pack(side="left", padx=20)

TITLE_FONT = (base_font, 20, "bold")
tk.Label(header, text="ALICIA: Academic Learning and Institutional Coaching Intelligent Assistant", font=TITLE_FONT,
         bg=HEADER_BG, fg=TEXT_DARK)\
  .pack(side="left", padx=(0, 1))

# ───────────── Chat area ─────────────

chat_frame = ttk.Frame(root)
chat_frame.pack(fill="both", expand=True, padx=15, pady=6)

chat_log = HTMLScrolledText(                # Markdown-aware widget
    chat_frame,
    html="",                                # start empty
    background=CHAT_BG,                     # overall chat bg
    font=SYSTEM_FONT,
    fg=TEXT_DARK,
    relief="flat", bd=0, width=150
)
chat_log.pack(fill="both", expand=True)

# keep the whole transcript as one HTML string
conversation_html = ""
transcript = []          # list of tuples: (tag, md_text)
def insert_bubble(md_text: str, tag: str):
    transcript.append((tag, md_text))          # store raw data

    # ── rebuild the entire document every time ──
    doc = ""
    for who, md in transcript:
        doc += _one_bubble_html(md, who)       # call helper that returns HTML

    chat_log.set_html(doc)
    chat_log.yview_moveto(1.0)

MAX_W      = "60%"
PAD_USER   = "8px 10px"
GAP_USER   = "8px"
GAP_BOT    = "3px"

def _one_bubble_html(md_text: str, tag: str) -> str:
    html = markdown.markdown(md_text,
                             extensions=["fenced_code", "tables", "nl2br"])
    html = re.sub(r"</?p[^>]*>", "", html, flags=re.S).replace("<br>", "")

    if tag == "user":
        return (
            #  ▼ overflow:auto ⇒ new BFC ⇒ margins no longer collapse
            f'<div style="margin:{GAP_USER} 0; overflow:auto;">'
            f'  <div style="text-align:right;">'
            f'    <span style="background-color:{USER_BG}; color:{TEXT_DARK}; '
            f'          padding:{PAD_USER}; border-radius:10px; '
            f'          display:inline-block; max-width:{MAX_W}; '
            f'          font-family:{base_font}; font-size:15px; '
            f'          line-height:1.35;">{html}</span>'
            f'  </div>'
            f'</div>'
        )

    # bot branch (unchanged)
    return (
        f'<div style="padding:{GAP_BOT} 0; text-align:left; '
        f'            max-width:{MAX_W}; font-family:{base_font}; '
        f'            font-size:15px; line-height:1.35; color:{TEXT_DARK};">'
        f'{html}</div>'
    )

# Intro banner (first bot bubble)
intro = ("Hi, I'm ALICIA. Here to help! Ask me anything about the "
         "program, mentorship, resources, and more. How can I help you today?")

insert_bubble(intro, "bot")

# ───────────── Entry & send button ─────────────
input_frame = ttk.Frame(root)
input_frame.pack(fill="x", padx=15, pady=(0, 15))

entry = tk.Text(input_frame, font=SYSTEM_FONT, height=2, wrap="word",
                relief="flat", highlightthickness=1, highlightbackground="#aaaaaa")
entry.pack(side="left", fill="x", expand=True, pady=3)

def send_query():
    user_msg = entry.get("1.0", "end-1c").strip()
    if not user_msg:
        return
    entry.delete("1.0", tk.END)

    insert_bubble(user_msg, "user")   # show the user’s text immediately

    def worker():
        try:
            bot_reply = chat(user_msg)      # your LLM function
        except Exception as e:
            bot_reply = f"[Error] {e}"
        # update GUI safely from the main thread
        root.after(0, lambda: insert_bubble(bot_reply, "bot"))

    threading.Thread(target=worker, daemon=True).start()

ttk.Button(input_frame, text="Send", command=send_query)\
   .pack(side="right", padx=(12, 0), ipadx=10, ipady=6)

def on_enter(event):
    send_query()
    return "break"        # prevents newline in the Text widget

entry.bind("<Return>", on_enter)

# ───────────── Launch ─────────────
root.mainloop()


