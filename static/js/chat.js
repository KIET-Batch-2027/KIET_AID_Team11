// Enhanced chat.js with strict language enforcement
(() => {
    const ctx = window.__CHAT_CONTEXT || {language: 'Bhojpuri', round: 'HR'};
    const chatWindow = document.getElementById('chatWindow');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const micBtn = document.getElementById('micBtn');
    const ttsToggle = document.getElementById('ttsToggle');
    const startBtn = document.getElementById('startChatBtn');
    const stopBtn = document.getElementById('stopChatBtn');
    const chatStatus = document.getElementById('chatStatus');
    const chatLangSelect = document.getElementById('chatLangSelect');

    let generating = false;
    let history = [];
    const supportedLangs = ['en', 'bho', 'mai'];

    function toLangCode(langValue) {
        const key = String(langValue || '').trim().toLowerCase();
        const langMap = {
            en: 'en',
            english: 'en',
            bho: 'bho',
            bhojpuri: 'bho',
            mai: 'mai',
            maithili: 'mai',
        };
        return langMap[key] || 'en';
    }

    let activeLanguage = toLangCode(ctx.language); // Enforce selected language strictly

    // Helper: Map short code to backend language name
    function getLangName(langCode) {
        const langMap = { en: 'English', bho: 'Bhojpuri', mai: 'Maithili' };
        return langMap[langCode] || 'English';
    }

    // Helper: Get current UI language from translator or context
    function getCurrentLang() {
        if (chatLangSelect && chatLangSelect.value) {
            const selectedLang = toLangCode(chatLangSelect.value);
            if (supportedLangs.includes(selectedLang)) {
                return selectedLang;
            }
        }

        if (window._translator && window._translator.getLang) {
            const translatedLang = toLangCode(window._translator.getLang());
            if (supportedLangs.includes(translatedLang)) {
                return translatedLang;
            }
        }

        const contextLang = toLangCode(ctx.language);
        if (supportedLangs.includes(contextLang)) {
            return contextLang;
        }

        const storedLang = toLangCode(localStorage.getItem('app_lang'));
        return supportedLangs.includes(storedLang) ? storedLang : 'en';
    }

    // Update active language and enforce it in chat
    function updateLanguage(lang) {
        const nextLang = toLangCode(lang || getCurrentLang());
        activeLanguage = supportedLangs.includes(nextLang) ? nextLang : 'en';
        if (chatLangSelect) {
            chatLangSelect.value = getLangName(activeLanguage);
        }
    }

    // Listen to language changes from translator
    if (window._translator && window._translator.onLanguageChange) {
        window._translator.onLanguageChange(updateLanguage);
    }

    if (chatLangSelect) {
        chatLangSelect.addEventListener('change', () => updateLanguage(chatLangSelect.value));
    }

    function escHtml(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

    function appendMessage(author, text, opts={}){
        const el = document.createElement('div');
        el.className = 'chat-msg';
        el.style.marginBottom = '12px';

        const header = document.createElement('div');
        header.style.fontSize = '12px';
        header.style.marginBottom = '4px';
        header.style.fontWeight = '600';
        header.style.color = author === 'AI' ? '#4f46e5' : '#64748b';
        header.textContent = author === 'AI' ? 'AI' : 'You';

        const body = document.createElement('div');
        body.style.padding = '10px 12px';
        body.style.borderRadius = '8px';
        body.style.whiteSpace = 'pre-wrap';
        body.style.wordWrap = 'break-word';
        body.style.fontSize = '14px';
        body.style.lineHeight = '1.5';
        body.innerHTML = escHtml(text);

        if(author === 'AI'){
            body.style.background = '#f0f4ff';
            body.style.border = '1px solid #e0e7ff';
            body.style.color = '#1e293b';
        } else {
            body.style.background = '#fef3c7';
            body.style.border = '1px solid #fde68a';
            body.style.color = '#78350f';
        }

        el.appendChild(header);
        el.appendChild(body);
        chatWindow.appendChild(el);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function setStatus(txt){
        if (chatStatus) chatStatus.textContent = txt || '';
    }

    async function apiCall(payload){
        try{
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(payload)
            });
            return await res.json();
        }catch(e){
            console.warn('API error:', e);
            return {error: 'Network error'};
        }
    }

    async function startInterview(){
        if(generating) return;
        setStatus('Starting...');
        generating = true;
        if (startBtn) startBtn.disabled = true;

        // ENFORCE: Use current UI language
        activeLanguage = getCurrentLang();
        const langName = getLangName(activeLanguage);

        const resp = await apiCall({action:'start', language: langName, round: ctx.round});
        generating = false;
        if (startBtn) startBtn.disabled = false;

        if(resp.error){
            setStatus(resp.error);
            return;
        }

        // clear window
        if (chatWindow) chatWindow.innerHTML = '';
        history = [];
        const startQuestion = resp?.data?.question || resp?.question || resp?.data?.reply || 'Interview started.';
        appendMessage('AI', startQuestion);
        setStatus('Live interview started');
        if (stopBtn) stopBtn.style.display = 'inline-block';
    }

    async function stopInterview(){
        const langName = getLangName(activeLanguage);
        await apiCall({action:'stop', language: langName, round: ctx.round});
        setStatus('Live interview stopped');
        if (stopBtn) stopBtn.style.display = 'none';
    }

    async function sendAnswer(){
        if(generating) return;
        const text = (chatInput.value || '').trim();
        if(!text) return;

        // show user message
        appendMessage('You', text);
        if (chatInput) chatInput.value = '';
        setStatus('Evaluating...');
        generating = true;
        if (sendBtn) sendBtn.disabled = true;

        // ENFORCE: Use current UI language strictly
        activeLanguage = getCurrentLang();
        const langName = getLangName(activeLanguage);

        const payload = {action:'answer', language: langName, round: ctx.round, message: text};
        const resp = await apiCall(payload);
        generating = false;
        if (sendBtn) sendBtn.disabled = false;

        if(!resp || resp.error || resp.success === false){
            appendMessage('AI', 'Error: ' + (resp?.message || resp?.error || 'Unknown'));
            setStatus('Error');
            return;
        }

        const data = resp.data || {};
        const feedback = data.feedback || resp.feedback || data.reply || '';
        const score = (data.score !== undefined ? data.score : resp.score);
        const nextQuestion = data.question || resp.question || '';

        appendMessage('AI', feedback + ((score !== undefined && score !== null && score !== '') ? `\n\nScore: ${score}` : ''));
        if(nextQuestion){
            appendMessage('AI', 'Next question: ' + nextQuestion);
            setStatus('Last score: ' + (score ?? ''));
        } else {
            setStatus('Interview complete');
        }

        // Optional TTS: speak AI response if enabled
        try{
            if(ttsToggle && ttsToggle.checked && window.speechSynthesis){
                const utter = new SpeechSynthesisUtterance(feedback || '');
                // choose voice lang based on active UI language
                if(activeLanguage === 'en') {
                    utter.lang = 'en-US';
                } else if(activeLanguage === 'bho' || activeLanguage === 'mai') {
                    utter.lang = 'hi-IN'; // Hindi/Devanagari fallback
                }
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(utter);
            }
        }catch(e){ console.warn('TTS error', e); }
    }

    // Event listeners
    if (startBtn) startBtn.addEventListener('click', startInterview);
    if (stopBtn) stopBtn.addEventListener('click', async ()=>{ await stopInterview(); });
    if (sendBtn) sendBtn.addEventListener('click', sendAnswer);
    if (chatInput) chatInput.addEventListener('keydown', (e)=>{ if(e.key === 'Enter'){ e.preventDefault(); sendAnswer(); } });

    // Microphone (Web Speech API)
    let recognizing = false;
    let recognition = null;
    if('webkitSpeechRecognition' in window || 'SpeechRecognition' in window){
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SR();
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = ()=>{
            recognizing = true;
            if (micBtn) micBtn.classList.add('listening');
            setStatus('Listening...');
        };
        recognition.onend = ()=>{
            recognizing = false;
            if (micBtn) micBtn.classList.remove('listening');
            setStatus('');
        };
        recognition.onerror = (e)=>{
            console.warn('Speech error', e);
            setStatus('Voice error');
        };
        recognition.onresult = (ev)=>{
            const text = Array.from(ev.results).map(r=>r[0].transcript).join('');
            if (chatInput) {
                chatInput.value = (chatInput.value ? chatInput.value + ' ' : '') + text;
            }
        };
    } else {
        if(micBtn) micBtn.style.display = 'none';
    }

    if(micBtn && recognition){
        micBtn.addEventListener('click', ()=>{
            if(!recognition) return;
            if(recognizing){
                recognition.stop();
            } else {
                // Enforce selected UI language for speech input
                activeLanguage = getCurrentLang();
                recognition.lang = (activeLanguage === 'en') ? 'en-US' : 'hi-IN';
                recognition.start();
            }
        });
    }

    // Expose for debugging
    window.__ai_chat = {startInterview, stopInterview, updateLanguage, getCurrentLang};
    updateLanguage(getCurrentLang());
})();
