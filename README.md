# ⚠️ SafeChem AI - Chemical Safety and SDS Assistant

SafeChem AI is an advanced, generative AI-powered safety assistant designed to help researchers, industrial workers, and safety officers instantly access Material Safety Data Sheets (MSDS/SDS).

Powered by a lightning-fast **Groq LPU Inference** backend and a custom **Retrieval-Augmented Generation (RAG)** pipeline, SafeChem AI ensures that critical, life-saving chemical information is accessible in real-time.

---

## ✨ Core Features

1. **Chemical Reactivity & Emergency Response**
   - If a user mentions a spill, an accidental mixture, or an exposure event (e.g., "I just spilled Sulfuric Acid on my arm" or "What happens if I mix bleach and ammonia?"), the bot instantly prioritizes emergency first-aid and evacuation protocols.
   - It cross-references chemical properties to predict severe reactions.

2. **Semantic Vector Search (RAG) over SDS Data**
   - Uses **Sentence Transformers** (`all-MiniLM-L6-v2`) to turn chemical names and properties into dense vectors.
   - Performs a rapid semantic search against the local `sds_dataset.csv` database to retrieve exact Handling, Storage, First Aid, and PPE data before passing it to the AI.

3. **Industrial Glassmorphism UI**
   - A highly customized, responsive Vanilla JS/HTML5 frontend featuring an "Industrial Dark" glassmorphism aesthetic.
   - Designed for clarity, featuring hazard yellow accents and dark translucent panels to ensure readability during stressful queries.

4. **Hallucination Prevention**
   - SafeChem AI is strictly instructed to **only** pull facts from the provided SDS context, minimizing the chance of an LLM generating dangerous or inaccurate safety advice.

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, Waitress
- **AI Inference**: Groq API (`llama-3.1-8b-instant`)
- **Embeddings & Vector Math**: `sentence-transformers`, `numpy`, `scikit-learn`
- **Data Engineering**: `pandas`
- **Frontend**: Vanilla HTML / CSS (Glassmorphism) / JS

---

## 🚀 Setup & Installation

1. **Initialize Virtual Environment**:
   ```bash
   python -m venv .venv
   
   # Windows:
   .\.venv\Scripts\Activate.ps1
   
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install flask flask-cors groq sentence-transformers pandas numpy scikit-learn python-dotenv waitress
   ```

3. **Environment Variables**:
   Create a `.env` file in the root folder and add your Groq API key:
   ```env
   GROQ_API_KEY="gsk_your_api_key_here"
   ```

4. **The SDS Dataset**:
   The app reads from `sds_dataset.csv`. You can easily add more rows (Chemical_Name, CAS_Number, Hazards, First_Aid, Handling_Storage, PPE) to expand its knowledge base.

---

## 🎮 Running the Server

Start the application:
```bash
python app.py
```

- If running for the first time, it will automatically download the local embedding model and compute `sds_embeddings.npy` from your dataset.
- Access the web interface at **`http://localhost:5000`**.
