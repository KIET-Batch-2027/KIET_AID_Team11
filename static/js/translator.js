// Global translator with proper state management and view binding
(function(){
  const localesPath = '/static/i18n/locales';
  const supported = { en: 'en', bho: 'bho', mai: 'mai' };
  
  // Initialize language from localStorage (default: 'en')
  let currentLang = localStorage.getItem('app_lang') || 'en';
  if (!supported[currentLang]) currentLang = 'en';
  
  let bundles = {}; // cache loaded locales
  let listeners = []; // observers for language changes
  
  // Load and cache locale file
  async function loadLocale(lang) {
    if (bundles[lang]) return bundles[lang];
    try {
      const res = await fetch(`${localesPath}/${lang}.json?v=3`);
      if (!res.ok) throw new Error('locale not found');
      const j = await res.json();
      bundles[lang] = j;
      return j;
    } catch(e) {
      if (lang !== 'en') return loadLocale('en');
      return {};
    }
  }
  
  // Get translated string by key path (e.g., "nav.dashboard")
  function t(key) {
    const parts = key.split('.');
    let obj = bundles[currentLang] || {};
    for (let p of parts) {
      if (obj && p in obj) obj = obj[p];
      else { obj = null; break; }
    }
    return (obj !== null && obj !== undefined) ? String(obj) : key;
  }
  
  // Translate all [data-i18n] elements on the page
  async function translatePage() {
    await loadLocale(currentLang);
    
    // Translate elements with data-i18n attribute
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const attr = el.getAttribute('data-i18n-attr');
      const txt = t(key);
      
      if (attr === 'placeholder') {
        el.setAttribute('placeholder', txt);
      } else if (attr === 'title') {
        el.setAttribute('title', txt);
      } else {
        el.textContent = txt;
      }
    });
    
    // Notify all listeners (chat, other components) about language change
    listeners.forEach(cb => cb(currentLang));
  }
  
  // Change language globally and update all affected UI
  async function setLang(lang) {
    if (!(lang in supported)) lang = 'en';
    currentLang = lang;
    localStorage.setItem('app_lang', lang);
    await translatePage();
  }
  
  // Register observer/listener for language changes
  function onLanguageChange(callback) {
    if (typeof callback === 'function') {
      listeners.push(callback);
    }
  }
  
  // Initialize on DOM ready
  async function initTranslator() {
    const sel = document.getElementById('langSelect');
    if (sel) {
      sel.value = currentLang;
      sel.addEventListener('change', (e) => {
        setLang(e.target.value);
        // Optionally reload page to ensure full translation
        // location.reload();
      });
    }
    await translatePage();
  }
  
  // Export to window
  window._translator = { 
    setLang, 
    t, 
    getLang: () => currentLang, 
    translatePage,
    onLanguageChange
  };
  
  // Auto-init when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTranslator);
  } else {
    initTranslator();
  }
})();
