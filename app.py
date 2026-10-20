from flask import Flask, request, jsonify, render_template_string
import os

from sds_chatbot import chatbot

app = Flask(__name__)

HTML_TEMPLATE = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SafeChem AI | SDS Assistant</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-gradient: linear-gradient(135deg, #1a1a24 0%, #0d0d14 100%);
      --text-main: #e2e8f0;
      --text-muted: #94a3b8;
      
      --glass-bg: rgba(30, 41, 59, 0.5);
      --glass-border: rgba(255, 255, 255, 0.1);
      --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
      
      --bot-bg: rgba(255, 255, 255, 0.08);
      --user-bg: rgba(250, 204, 21, 0.15); /* Hazard Yellow tint */
      --accent: #facc15;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg-gradient);
      color: var(--text-main);
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      overflow: hidden;
    }
    
    /* Background Orbs for dynamic glass effect - Safety/Industrial Colors */
    .orb { position: absolute; border-radius: 50%; filter: blur(80px); z-index: -1; opacity: 0.4; animation: float 15s infinite alternate ease-in-out; }
    .orb-1 { width: 400px; height: 400px; background: #facc15; top: -100px; left: -100px; }
    .orb-2 { width: 500px; height: 500px; background: #0284c7; bottom: -150px; right: -100px; animation-delay: -3s; opacity: 0.2;}
    .orb-3 { width: 300px; height: 300px; background: #dc2626; bottom: 30%; left: 10%; opacity: 0.3; animation-delay: -7s; }
    @keyframes float { 0% { transform: translate(0, 0) scale(1); } 50% { transform: translate(30px, -50px) scale(1.1); } 100% { transform: translate(-30px, 50px) scale(0.9); } }
    
    .chat-panel {
      width: 100%;
      max-width: 850px;
      height: 92vh;
      display: flex;
      flex-direction: column;
      position: relative;
      background: var(--glass-bg);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border: 1px solid var(--glass-border);
      border-radius: 24px;
      box-shadow: var(--glass-shadow);
      z-index: 10;
    }

    .chat-header {
      padding: 24px 30px;
      text-align: center;
      color: #fff;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      background: rgba(0, 0, 0, 0.2);
      border-radius: 24px 24px 0 0;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 12px;
    }
    .chat-header h1 { font-size: 24px; font-weight: 700; letter-spacing: 1px; color: var(--accent); }

    .messages-container {
      flex: 1;
      overflow-y: auto;
      padding: 30px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      scroll-behavior: smooth;
    }
    .messages-container::-webkit-scrollbar { width: 4px; }
    .messages-container::-webkit-scrollbar-track { background: transparent; }
    .messages-container::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }

    .message-row { display: flex; align-items: flex-start; gap: 16px; animation: fadeIn 0.4s ease-out forwards; }
    .user-row { justify-content: flex-end; }
    .bot-row { justify-content: flex-start; }
    
    .avatar { 
      width: 44px; 
      height: 44px; 
      display: flex; 
      align-items: center; 
      justify-content: center; 
      flex-shrink: 0;
      font-size: 20px;
      background: rgba(0,0,0,0.4);
      border-radius: 50%;
      border: 1px solid var(--accent);
      backdrop-filter: blur(8px);
    }
    .user-avatar { display: none; }
    
    .message-bubble { 
      max-width: 80%; 
      padding: 18px 24px; 
      font-size: 15px; 
      line-height: 1.6; 
      border-radius: 16px;
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      border: 1px solid var(--glass-border);
    }
    .bot-bubble { 
      background: var(--bot-bg); 
      color: var(--text-main);
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
      border-top-left-radius: 4px;
    }

    .user-bubble { 
      background: var(--user-bg); 
      color: #fff;
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
      border-top-right-radius: 4px;
      border: 1px solid rgba(250, 204, 21, 0.3);
    }

    .bot-bubble strong { font-weight: 700; color: var(--accent); }
    .bot-bubble em { font-style: italic; }
    .bot-bubble ul { margin-left: 20px; margin-top: 8px; }
    .bot-bubble h3 { color: var(--accent); margin-top: 10px; margin-bottom: 5px; font-size: 16px;}

    .typing-row { display: none; }
    .typing-row.show { display: flex; }
    .typing-indicator span { 
      display: inline-block; width: 6px; height: 6px; 
      background: var(--text-muted); border-radius: 50%; margin: 0 2px; 
      animation: bounce 1.4s infinite both; 
    }
    .typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
    .typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

    /* Input Area */
    .input-area { 
      padding: 20px 30px 24px; 
      display: flex; 
      gap: 15px;
      justify-content: center;
      background: rgba(0,0,0,0.2);
      border-top: 1px solid rgba(255,255,255,0.05);
      border-radius: 0 0 24px 24px;
    }
    .input-glass { 
      width: 100%;
      display: flex; 
      align-items: stretch; 
      gap: 12px;
    }
    input { 
      flex: 1; 
      background: rgba(0, 0, 0, 0.4); 
      border: 1px solid var(--glass-border); 
      color: var(--text-main); 
      font-family: 'Inter', sans-serif; 
      font-size: 15px; 
      padding: 16px 20px;
      outline: none; 
      border-radius: 12px;
      transition: all 0.3s ease;
      backdrop-filter: blur(10px);
    }
    input:focus { 
      background: rgba(0, 0, 0, 0.6); 
      border-color: var(--accent);
      box-shadow: 0 0 0 2px rgba(250, 204, 21, 0.2);
    }
    input::placeholder { color: var(--text-muted); }
    
    .send-btn { 
      background: var(--accent); 
      border: none; 
      color: #000; 
      padding: 0 24px;
      font-family: 'Inter', sans-serif;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer; 
      transition: all 0.3s ease; 
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(250, 204, 21, 0.2);
    }
    .send-btn:hover { 
      background: #fde047;
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(250, 204, 21, 0.4);
    }

    .welcome-screen { text-align: center; margin: auto; animation: fadeIn 0.8s ease-out; color: #fff; }
    .welcome-screen h2 { font-size: 24px; margin-bottom: 12px; font-weight: 600; color: var(--accent);}
    .welcome-screen p { color: var(--text-muted); margin-bottom: 30px; font-size: 15px;}

    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1); } }
  </style>
</head>
<body>

  <div class="orb orb-1"></div>
  <div class="orb orb-2"></div>
  <div class="orb orb-3"></div>

  <div class="chat-panel">
    <div class="chat-header">
      <span style="font-size: 28px;">⚠️</span>
      <h1>SafeChem AI</h1>
    </div>

    <div class="messages-container" id="chatArea">
      <div class="welcome-screen" id="welcomeCard">
        <h2>Industrial SDS & Chemical Safety Assistant</h2>
        <p>Ask about handling protocols, emergency first-aid, PPE requirements, or chemical reactivity.</p>
      </div>

      <div class="message-row bot-row typing-row" id="typingRow">
        <div class="avatar">⚠️</div>
        <div class="message-bubble bot-bubble typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>

    <div class="input-area">
      <div class="input-glass">
        <input id="userInput" type="text" placeholder="E.g., What are the hazards of Sulfuric Acid?" autocomplete="off" />
        <button class="send-btn" onclick="sendMessage()">Scan</button>
      </div>
    </div>
  </div>

  <script>
    const chatArea = document.getElementById('chatArea');
    const typingRow = document.getElementById('typingRow');
    const inp = document.getElementById('userInput');
    const welcomeCard = document.getElementById('welcomeCard');
    let hasStarted = false;

    function md(text) {
      // Basic markdown parser
      let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                     .replace(/\*(.*?)\*/g, '<em>$1</em>');
                     
      // Handle headers (###)
      html = html.replace(/### (.*?)\n/g, '<h3>$1</h3>');
      
      return html.replace(/\n/g, '<br/>');
    }

    function addMsg(text, isUser) {
      if (!hasStarted) { welcomeCard.style.display = 'none'; hasStarted = true; }
      typingRow.classList.remove('show');
      
      const row = document.createElement('div');
      row.className = `message-row ${isUser ? 'user-row' : 'bot-row'}`;
      
      const bub = document.createElement('div');
      bub.className = `message-bubble ${isUser ? 'user-bubble' : 'bot-bubble'}`;
      if (isUser) bub.textContent = text;
      else bub.innerHTML = md(text);

      if (!isUser) {
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = '⚠️'; 
        row.appendChild(avatar);
      }
      
      row.appendChild(bub);
      chatArea.insertBefore(row, typingRow);
      chatArea.scrollTop = chatArea.scrollHeight;
    }

    async function sendMessage() {
      const text = inp.value.trim();
      if (!text) return;
      inp.value = '';
      addMsg(text, true);
      
      typingRow.classList.add('show');
      chatArea.scrollTop = chatArea.scrollHeight;

      try {
        const res = await fetch('/chat', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({message: text})
        });
        const data = await res.json();
        addMsg(data.reply, false);
      } catch(e) {
        addMsg("Network error or server is down. Please verify your connection.", false);
      }
    }

    inp.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });
  </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get('message', '')
    
    # Process through SafeChem AI RAG Engine
    reply = chatbot.respond(message)
    
    return jsonify({'reply': reply})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7860))
    print(f"Starting SafeChem AI on http://0.0.0.0:{port}...")
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        print("Waitress not found. Falling back to Flask development server.")
        app.run(debug=False, host='0.0.0.0', port=port)
