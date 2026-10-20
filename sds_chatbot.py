import os
import re
import json
import logging
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd
import numpy as np

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    SentenceTransformer = None
    cosine_similarity = None

import contextvars

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Session state management
session_state = contextvars.ContextVar('session_state', default={})

class SDSChatbot:
    def __init__(self, data_path: str = "sds_dataset.csv"):
        self.data_path = Path(data_path)
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        
        self.df = None
        self.embeddings = None
        self.embedder = None
        self.embedding_file = Path("sds_embeddings.npy")
        
        # Initialize Gemini client
        self.gemini_model = None
        if self.gemini_api_key and genai:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-3.5-flash-lite')
                logger.info("✨ Google Gemini AI (gemini-3.5-flash-lite) is ENABLED.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")

        # Initialize Groq client
        self.groq_client = None
        if self.groq_api_key and Groq:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key)
                logger.info("✨ Groq Generative AI (RAG) is ENABLED.")
            except Exception as e:
                logger.error(f"Failed to initialize Groq: {e}")

        self.llm_enabled = bool(self.gemini_model or self.groq_client)

        self._load_data_and_embeddings()

    def _load_data_and_embeddings(self):
        if not self.data_path.exists():
            logger.warning(f"Dataset {self.data_path} not found. Please create it.")
            self.df = pd.DataFrame(columns=["Chemical_Name", "CAS_Number", "Hazards", "First_Aid", "Handling_Storage", "PPE"])
            return

        self.df = pd.read_csv(self.data_path)
        self.df = self.df.fillna("")

        if not SentenceTransformer:
            logger.warning("sentence-transformers not installed. RAG disabled.")
            return

        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')

        if self.embedding_file.exists():
            self.embeddings = np.load(self.embedding_file)
            logger.info("Loaded cached SDS embeddings.")
        else:
            logger.info("Generating new embeddings for SDS dataset...")
            texts_to_embed = []
            for _, row in self.df.iterrows():
                text = f"Chemical: {row.get('Chemical_Name', '')}. CAS: {row.get('CAS_Number', '')}. Hazards: {row.get('Hazards', '')}. First Aid: {row.get('First_Aid', '')}. Storage: {row.get('Handling_Storage', '')}. PPE: {row.get('PPE', '')}."
                texts_to_embed.append(text)
            
            self.embeddings = self.embedder.encode(texts_to_embed, convert_to_numpy=True)
            np.save(self.embedding_file, self.embeddings)
            logger.info("Saved SDS embeddings to disk.")

    def _get_session(self, session_id: str) -> Dict[str, Any]:
        state = session_state.get()
        if session_id not in state:
            state[session_id] = {
                "history": [],
            }
        return state

    def semantic_search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        if self.embeddings is None or self.embedder is None or self.df.empty:
            return []
            
        query_emb = self.embedder.encode([query], convert_to_numpy=True)
        similarities = cosine_similarity(query_emb, self.embeddings)[0]
        
        top_indices = np.argsort(similarities)[::-1][:limit]
        results = []
        for idx in top_indices:
            if similarities[idx] > 0.2: # basic threshold
                results.append(self.df.iloc[idx].to_dict())
        return results

    def _build_context_str(self, semantic_results: List[Dict[str, Any]]) -> str:
        context_str = ""
        for i, item in enumerate(semantic_results):
            context_str += f"[{i+1}] Chemical: {item.get('Chemical_Name', 'Unknown')}\n"
            context_str += f"    CAS Number: {item.get('CAS_Number', 'N/A')}\n"
            context_str += f"    Hazards: {item.get('Hazards', 'N/A')}\n"
            context_str += f"    First Aid: {item.get('First_Aid', 'N/A')}\n"
            context_str += f"    Handling & Storage: {item.get('Handling_Storage', 'N/A')}\n"
            context_str += f"    PPE Required: {item.get('PPE', 'N/A')}\n\n"
        return context_str.strip()

    def _respond_rag(self, user_input: str, history: List[Dict[str, str]]) -> str:
        if not self.llm_enabled:
            return "AI is not configured. Please add GEMINI_API_KEY or GROQ_API_KEY to your .env file."

        # Detect emergency/reactivity logic
        is_emergency = any(word in user_input.lower() for word in ['spill', 'mix', 'mixed', 'fire', 'burn', 'swallowed', 'inhaled', 'emergency'])
        limit = 5 if is_emergency else 3
        
        semantic_results = self.semantic_search(user_input, limit=limit)
        context_str = self._build_context_str(semantic_results)
        
        if not context_str:
            context_str = "No specific chemicals matched in the local SDS database."

        system_prompt = f"""You are SafeChem AI, an expert, professional, and concise Chemical Safety and SDS Assistant.
Your goal is to provide accurate safety information based strictly on the provided SDS context.

CRITICAL DIRECTIVES:
1. EMERGENCY / REACTIVITY: If the user mentions mixing chemicals, a spill, or an exposure emergency, prioritize immediate first-aid, evacuation, or reactivity warnings in a bold, clear list.
2. ACCURACY: Do not hallucinate safety protocols. Rely heavily on the provided context. If the context is missing, state that the chemical is not in the database, but you can provide general guidance.
3. TONE: Professional, authoritative, and concise. No fluff.

SDS Context Database:
{context_str}
"""
        # 1. Try Google Gemini first
        if self.gemini_model:
            try:
                contents = []
                for turn in history:
                    contents.append({"role": "user", "parts": [turn["user"]]})
                    contents.append({"role": "model", "parts": [turn["bot"]]})
                
                full_prompt = f"System Directives & SDS Context:\n{system_prompt}\n\nUser Question:\n{user_input}"
                contents.append({"role": "user", "parts": [full_prompt]})

                response = self.gemini_model.generate_content(
                    contents,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=1024,
                    )
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                if not self.groq_client:
                    return f"Gemini error: {e}"

        # 2. Try Groq fallback
        if self.groq_client:
            messages = [{"role": "system", "content": system_prompt}]
            for turn in history:
                messages.append({"role": "user", "content": turn["user"]})
                messages.append({"role": "assistant", "content": turn["bot"]})
            messages.append({"role": "user", "content": user_input})

            try:
                chat_completion = self.groq_client.chat.completions.create(
                    messages=messages,
                    model="llama-3.1-8b-instant",
                    temperature=0.3,
                    max_tokens=1024
                )
                return chat_completion.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"Groq API error: {e}")
                return "An error occurred while communicating with the AI. Please try again."

        return "No active AI provider available. Please check your API keys."

    def respond(self, user_input: str, session_id: str = "default") -> str:
        state = self._get_session(session_id)
        history = state[session_id]["history"]
        
        query = user_input.strip()
        if not query:
            return "Please ask a chemical safety question."

        # Instant reply for common greetings without invoking heavy CPU embedding + LLM
        greetings = {'hi', 'hello', 'hey', 'greetings', 'help', 'who are you', 'good morning', 'good afternoon', 'good evening'}
        clean_query = re.sub(r'[^\w\s]', '', query.lower()).strip()
        if clean_query in greetings:
            reply = "Hello! I am **SafeChem AI**, your real-time Chemical Safety and SDS Assistant.\n\nAsk me about chemical hazards, handling & storage, required PPE, or emergency protocols (e.g., *\"What are the hazards of Sulfuric Acid?\"* or *\"What happens if I mix bleach and ammonia?\"*)."
            history.append({"user": query, "bot": reply})
            return reply

        reply = self._respond_rag(query, history)
        
        # Update history
        history.append({"user": query, "bot": reply})
        if len(history) > 6:
            state[session_id]["history"] = history[-6:]
            
        return reply

# Global instance for app.py
chatbot = SDSChatbot()
