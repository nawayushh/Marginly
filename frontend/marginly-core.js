/**
 * Marginly Core Unified Client Script
 * Powers consistent branding, auth, user session, navigation, 
 * language translation (EN/HI), outlet switcher, notifications, and profile modals across all pages.
 */

(function () {
  'use strict';

  // 1. Session & Auth State Management
  const isLoginPage = window.location.pathname.includes('login.html');
  const isRegisterPage = window.location.pathname.includes('register.html');

  // Check auth
  let currentUser = null;
  try {
    const rawUser = localStorage.getItem('marginly_user');
    if (rawUser) {
      currentUser = JSON.parse(rawUser);
    }
  } catch (e) {
    console.warn('Could not parse user from storage:', e);
  }

  // If user visits a protected page and has no active session, redirect to login
  if (!currentUser && !isLoginPage && !isRegisterPage) {
    localStorage.removeItem('marginly_token');
    localStorage.removeItem('marginly_user');
    window.location.href = '/login.html';
    return;
  }

  // Expose global logout helper so inline onclick="logout()" always works
  window.logout = function () {
    if (confirm('Are you sure you want to sign out of Marginly?')) {
      localStorage.removeItem('marginly_token');
      localStorage.removeItem('marginly_user');
      localStorage.setItem('marginly_logged_out', 'true');
      window.location.href = '/login.html';
    }
  };

  // Expose global profile modal opener
  window.openMarginlyProfile = function () {
    const modal = document.getElementById('marginly-profile-modal');
    if (modal) {
      modal.classList.remove('hidden');
    }
  };

  // Current Language
  let currentLang = localStorage.getItem('marginly_lang') || 'en';

  // Comprehensive Dictionary for EN / HI translations
  const I18N = {
    en: {
      dashboard: 'Dashboard',
      dishes: 'Dishes & Recipes',
      addRecipe: 'Add Recipe',
      menuLayout: 'Menu Layout',
      priceAlerts: 'Price Alerts',
      simulator: 'What-If Simulator',
      reports: 'Reports',
      tagline: 'Know which dishes make you money',
      switchOutlet: 'Switch Outlet',
      activeOutlet: 'Active Outlet',
      allOutlets: 'All Restaurant Outlets',
      addNewOutlet: '+ Add New Outlet / Location',
      notifications: 'Live Market & Price Radar',
      markAllRead: 'Mark all as read',
      profile: 'Account Profile',
      logout: 'Sign Out / Log Out',
      ownerChef: 'Owner & Head Chef',
      speakIt: 'Speak it',
      photoIt: 'Photograph it',
      typeIt: 'Type it',
      avgProfit: 'Avg profit per cover',
      foodCost: 'Food cost percentage',
      highRisk: 'High-risk dishes',
      monthlyLeak: 'Monthly profit leak',
      save: 'Save Changes',
      cancel: 'Cancel',
      phoneEmailAlerts: 'SMS & WhatsApp Alert Channel',
      alertChannelDesc: 'Receive automated Mandi price spike alerts before your distributor charges higher rates.',
      linkedContact: 'Alerts Contact:',
      updateContact: 'Update Channel',
      addRecipeShortcut: '+ Add Menu Dish to Price Watchlist'
    },
    hi: {
      dashboard: 'डैशबोर्ड',
      dishes: 'व्यंजन और रेसिपी',
      addRecipe: 'रेसिपी जोड़ें',
      menuLayout: 'मेनू लेआउट',
      priceAlerts: 'मूल्य अलर्ट',
      simulator: 'व्हाट-इफ़ सिम्युलेटर',
      reports: 'रिपोर्ट्स',
      tagline: 'जानिए कौन से व्यंजन आपको मुनाफा देते हैं',
      switchOutlet: 'आउटलेट बदलें',
      activeOutlet: 'सक्रिय आउटलेट',
      allOutlets: 'सभी रेस्टोरेंट आउटलेट्स',
      addNewOutlet: '+ नया आउटलेट जोड़ें',
      notifications: 'लाइव मार्केट एवं मूल्य रडार',
      markAllRead: 'सभी को पढ़ा हुआ चिह्नित करें',
      profile: 'खाता प्रोफ़ाइल',
      logout: 'लॉगआउट करें',
      ownerChef: 'मालिक और मुख्य शेफ',
      speakIt: 'बोलकर जोड़ें',
      photoIt: 'फोटो खींचें',
      typeIt: 'टाइप करें',
      avgProfit: 'प्रति थाली औसत लाभ',
      foodCost: 'खाद्य लागत प्रतिशत',
      highRisk: 'जोखिम वाले व्यंजन',
      monthlyLeak: 'मासिक लाभ रिसाव',
      save: 'सहेजें',
      cancel: 'रद्द करें',
      phoneEmailAlerts: 'एसएमएस एवं व्हाट्सएप अलर्ट चैनल',
      alertChannelDesc: 'मंडी में सामग्री के दाम बढ़ते ही तुरंत अपने फोन पर सूचना पाएं।',
      linkedContact: 'अलर्ट संपर्क:',
      updateContact: 'नंबर अपडेट करें',
      addRecipeShortcut: '+ मूल्य वॉचलिस्ट में व्यंजन जोड़ें'
    }
  };

  // Run on DOM Ready and retry for dynamic content
  document.addEventListener('DOMContentLoaded', () => {
    initCore();
    // Re-check shortly after to ensure dynamic frameworks haven't overwritten
    setTimeout(initCore, 150);
    setTimeout(initCore, 500);
  });

  function initCore() {
    try { setupDarkMode(); } catch (e) { console.warn('setupDarkMode error:', e); }
    try { fixBrandingAndTitles(); } catch (e) { console.warn('fixBranding error:', e); }
    try { fixUserProfileData(); } catch (e) { console.warn('fixUserProfile error:', e); }
    try { fixNavigationLinks(); } catch (e) { console.warn('fixNavigation error:', e); }
    try { setupLanguageSwitcher(); } catch (e) { console.warn('setupLanguage error:', e); }
    try { setupOutletDropdown(); } catch (e) { console.warn('setupOutlet error:', e); }
    try { setupNotificationCenter(); } catch (e) { console.warn('setupNotification error:', e); }
    try { setupProfileAndLogoutModal(); } catch (e) { console.warn('setupProfile error:', e); }
    try { applyLanguage(currentLang); } catch (e) { console.warn('applyLanguage error:', e); }
  }

  // 2. Fix Title & Branding
  function fixBrandingAndTitles() {
    let currentTitle = document.title || 'Marginly';
    currentTitle = currentTitle.replace(/MenuMitra/gi, 'Marginly').trim();
    if (!currentTitle.toLowerCase().includes('marginly')) {
      document.title = `Marginly — ${currentTitle}`;
    } else {
      document.title = currentTitle;
    }

    // Replace text nodes containing "MenuMitra"
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    const nodesToReplace = [];
    while ((node = walker.nextNode())) {
      if (node.nodeValue && node.nodeValue.includes('MenuMitra')) {
        nodesToReplace.push(node);
      }
    }
    nodesToReplace.forEach(n => {
      n.nodeValue = n.nodeValue.replace(/MenuMitra/g, 'Marginly');
    });
  }

  // 3. Fix User Profile and Restaurant Display
  function fixUserProfileData() {
    if (!currentUser) return;

    const initials = (currentUser.display_name || currentUser.username || 'User')
      .split(' ')
      .map(part => part[0])
      .join('')
      .substring(0, 2)
      .toUpperCase();

    const displayName = currentUser.display_name || currentUser.username || 'Restaurant Owner';
    const restaurantName = currentUser.restaurant_name || 'Doon Bistro & Kitchen';
    const loc = currentUser.location ? `, ${currentUser.location.split(',')[0]}` : '';
    const outletDisplay = `${restaurantName}${loc}`;

    // Replace all text matching Vikram Anand or Café Doon Brew using TreeWalker
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while ((node = walker.nextNode())) {
      const parentTag = node.parentElement ? node.parentElement.tagName : '';
      if (['SCRIPT', 'STYLE', 'TEXTAREA'].includes(parentTag)) continue;

      let val = node.nodeValue;
      if (!val) continue;

      let changed = false;
      // Vikram Anand variations
      if (/Vikram\s+Anand/i.test(val)) {
        val = val.replace(/Chef\s+Vikram\s+Anand/gi, displayName).replace(/Vikram\s+Anand/gi, displayName);
        changed = true;
      }

      // Café Doon Brew variations
      if (/Caf[eé\ufffd]\s+Doon\s+Brew/i.test(val) || /CAFE\s+DOON\s+BREW/i.test(val)) {
        val = val.replace(/Caf[eé\ufffd]\s+Doon\s+Brew(,\s*Rajpur\s*Rd)?/gi, outletDisplay)
                 .replace(/CAFE\s+DOON\s+BREW/gi, restaurantName.toUpperCase());
        changed = true;
      }

      if (changed) {
        node.nodeValue = val;
      }
    }

    // Replace initials / avatar indicators
    document.querySelectorAll('*').forEach(el => {
      if (['INPUT', 'TEXTAREA', 'SCRIPT', 'STYLE'].includes(el.tagName)) return;
      if (el.children.length === 0 && el.textContent) {
        const text = el.textContent.trim();
        if (text === 'VA' || text === 'RO') {
          el.textContent = initials;
        }
      }
    });

    // Replace profile avatar image if it's Vikram Anand's stock photo
    document.querySelectorAll('img[src*="aida-public"], img[src*="AB6AXu"], img[data-alt*="Vikram"]').forEach(img => {
      const parent = img.parentElement;
      if (parent) {
        parent.innerHTML = `<span class="font-bold text-on-primary text-sm">${initials}</span>`;
        parent.className = 'w-9 h-9 rounded-full bg-primary-container text-on-primary flex items-center justify-center border-2 border-surface-container-lowest shadow-sm cursor-pointer';
        parent.title = `${displayName} — Click to view profile`;
      }
    });

    // Update specific ID elements if they exist
    const userDisplayEl = document.getElementById('user-display-name');
    if (userDisplayEl) userDisplayEl.textContent = displayName;

    const outletNameEl = document.getElementById('outlet-name');
    if (outletNameEl) outletNameEl.textContent = outletDisplay;

    const dropdownOutletNameEl = document.getElementById('dropdown-outlet-name');
    if (dropdownOutletNameEl) dropdownOutletNameEl.textContent = outletDisplay;

    const userInitialsEl = document.getElementById('user-initials');
    if (userInitialsEl) userInitialsEl.textContent = initials;
  }

  // 4. Fix Navigation Links Across All Pages
  function fixNavigationLinks() {
    const currentPath = window.location.pathname;

    const navMap = [
      { keywords: ['dashboard', 'डैशबोर्ड'], url: '/index.html' },
      { keywords: ['dishes', 'recipes', 'व्यंजन'], url: '/menumitra_dishes_recipes/code.html' },
      { keywords: ['add recipe', 'add', 'रेसिपी जोड़ें'], url: '/menumitra_add_recipe_smart_voice_photo_capture/code.html' },
      { keywords: ['menu layout', 'layout', 'heatmap', 'लेआउट'], url: '/menumitra_printed_menu_layout_heatmap/code.html' },
      { keywords: ['price alerts', 'alerts', 'मूल्य अलर्ट'], url: '/menumitra_price_alerts_volatility_radar/code.html' },
      { keywords: ['what-if', 'simulator', 'सिम्युलेटर'], url: '/menumitra_what_if_simulator/code.html' }
    ];

    document.querySelectorAll('header nav a, nav.md\\:hidden a, nav a').forEach(a => {
      const text = a.textContent.toLowerCase().trim();
      for (const item of navMap) {
        if (item.keywords.some(k => text.includes(k))) {
          a.setAttribute('href', item.url);
          const isActive = (item.url === '/index.html' && (currentPath === '/' || currentPath.endsWith('index.html'))) ||
                           (item.url !== '/index.html' && currentPath.includes(item.url.split('/')[1]));
          
          if (isActive) {
            a.classList.remove('text-on-surface-variant');
            a.classList.add('bg-primary-container', 'text-on-primary', 'font-semibold');
          }
          break;
        }
      }
    });

    // Make Marginly logo click navigate to /index.html
    let brandHomeLogo = document.querySelector('header .flex.items-center.space-x-2\\.5, header .flex.items-center.gap-2\\.5');
    if (!brandHomeLogo) {
      document.querySelectorAll('header a, header div').forEach(el => {
        if (!brandHomeLogo && el.textContent && el.textContent.includes('Marginly')) {
          brandHomeLogo = el;
        }
      });
    }
    if (brandHomeLogo) {
      brandHomeLogo.style.cursor = 'pointer';
      brandHomeLogo.onclick = () => { window.location.href = '/index.html'; };
    }
  }

  // 5. Language Switcher (EN / HI) — Universal across all page header variants
  //
  // Pages use 3 different markup patterns:
  //   A) Two-button container:  <div><button>EN</button><button>हिं</button></div>
  //   B) Single button spans:   <button><span>EN</span> | <span>हिं</span></button>
  //   C) Single button spans:   <button><span>EN</span><span>/</span><span>हिं</span></button>
  //
  // This rewrite discovers ALL of them reliably.

  let _langElements = []; // cached references: { type: 'two-btn'|'single-btn', container, enBtn, hiBtn, enSpan, hiSpan }

  function discoverLangElements() {
    _langElements = [];

    // Strategy 1: Find containers that hold exactly 2 buttons where first says "EN"
    document.querySelectorAll('header div, header span').forEach(container => {
      const btns = container.querySelectorAll(':scope > button');
      if (btns.length === 2) {
        const first = btns[0].textContent.trim();
        const second = btns[1].textContent.trim();
        if (first === 'EN' && (second === 'हिं' || second === 'HI')) {
          container.setAttribute('data-lang-toggle', 'true');
          btns[0].setAttribute('data-lang-toggle', 'true');
          btns[1].setAttribute('data-lang-toggle', 'true');
          _langElements.push({ type: 'two-btn', container, enBtn: btns[0], hiBtn: btns[1] });
        }
      }
    });

    // Strategy 2: Find single buttons that contain both EN and हिं as child spans
    document.querySelectorAll('header button').forEach(btn => {
      // Skip if already captured as part of a two-button container
      if (_langElements.some(el => el.enBtn === btn || el.hiBtn === btn)) return;

      const spans = btn.querySelectorAll('span');
      let enSpan = null, hiSpan = null;
      spans.forEach(sp => {
        const t = sp.textContent.trim();
        if (t === 'EN') enSpan = sp;
        if (t === 'हिं' || t === 'HI') hiSpan = sp;
      });

      // Also check direct text for "EN | हिं" pattern (text node between spans)
      if (!enSpan && !hiSpan) {
        const btnText = btn.textContent.trim();
        if (/EN\s*[|\/]\s*हिं/.test(btnText) || /EN\s*[|\/]\s*HI/.test(btnText)) {
          spans.forEach(sp => {
            const t = sp.textContent.trim();
            if (t === 'EN' || t.startsWith('EN')) enSpan = sp;
            if (t === 'हिं' || t === 'HI') hiSpan = sp;
          });
        }
      }

      if (enSpan && hiSpan) {
        btn.setAttribute('data-lang-toggle', 'true');
        _langElements.push({ type: 'single-btn', container: btn, enSpan, hiSpan, enBtn: btn, hiBtn: btn });
      }
    });
  }

  function setupLanguageSwitcher() {
    discoverLangElements();

    _langElements.forEach(el => {
      if (el.type === 'two-btn') {
        el.enBtn.onclick = (e) => { e.preventDefault(); e.stopPropagation(); setLanguage('en'); };
        el.hiBtn.onclick = (e) => { e.preventDefault(); e.stopPropagation(); setLanguage('hi'); };
      } else if (el.type === 'single-btn') {
        el.container.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          setLanguage(currentLang === 'en' ? 'hi' : 'en');
        };
      }
    });
  }

  function setLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('marginly_lang', lang);
    applyLanguage(lang);
    window.dispatchEvent(new CustomEvent('marginly_lang_change', { detail: { lang } }));
  }

  function applyLanguage(lang) {
    const t = I18N[lang] || I18N.en;

    // Re-discover if needed (dynamic pages)
    if (_langElements.length === 0) discoverLangElements();

    // Update visual state of all language toggles
    _langElements.forEach(el => {
      if (el.type === 'two-btn') {
        if (lang === 'en') {
          applyBtnActive(el.enBtn);
          applyBtnInactive(el.hiBtn);
        } else {
          applyBtnActive(el.hiBtn);
          applyBtnInactive(el.enBtn);
        }
      } else if (el.type === 'single-btn') {
        if (lang === 'en') {
          if (el.enSpan) { el.enSpan.className = 'font-bold text-primary'; }
          if (el.hiSpan) { el.hiSpan.className = 'text-on-surface-variant font-medium'; }
        } else {
          if (el.hiSpan) { el.hiSpan.className = 'font-bold text-primary'; }
          if (el.enSpan) { el.enSpan.className = 'text-on-surface-variant font-medium'; }
        }
      }
    });

    // Comprehensive dictionary for complete page translation
    const pairs = [
      // Navigation & Header
      { en: 'Dashboard', hi: 'डैशबोर्ड' },
      { en: 'Dishes & Recipes', hi: 'व्यंजन और रेसिपी' },
      { en: 'Dishes', hi: 'व्यंजन' },
      { en: 'Add Recipe', hi: 'रेसिपी जोड़ें' },
      { en: 'Add', hi: 'जोड़ें' },
      { en: 'Menu Layout', hi: 'मेनू लेआउट' },
      { en: 'Price Alerts', hi: 'मूल्य अलर्ट' },
      { en: 'What-If Simulator', hi: 'व्हाट-इफ़ सिम्युलेटर' },
      { en: 'Simulator', hi: 'सिम्युलेटर' },
      { en: 'Reports', hi: 'रिपोर्ट्स' },
      { en: 'Know which dishes make you money', hi: 'जानिए कौन से व्यंजन आपको मुनाफा देते हैं' },
      { en: 'Switch Outlet', hi: 'आउटलेट बदलें' },
      { en: 'Active Outlet', hi: 'सक्रिय आउटलेट' },
      { en: 'All Restaurant Outlets', hi: 'सभी रेस्टोरेंट आउटलेट्स' },
      { en: 'Add New Outlet / Location', hi: 'नया आउटलेट / स्थान जोड़ें' },
      { en: 'Notifications', hi: 'सूचनाएं' },
      { en: 'Account Profile', hi: 'खाता प्रोफ़ाइल' },
      { en: 'Sign Out / Log Out', hi: 'लॉगआउट करें' },
      { en: 'Sign Out', hi: 'साइन आउट' },
      { en: 'Log Out', hi: 'लॉगआउट' },
      { en: 'Back to Dashboard', hi: 'डैशबोर्ड पर वापस' },
      { en: 'Head Chef & Owner', hi: 'मुख्य शेफ और मालिक' },
      { en: 'Owner & Head Chef', hi: 'मालिक और मुख्य शेफ' },
      { en: 'Owner & Chef', hi: 'मालिक और शेफ' },
      { en: 'Chef & Owner', hi: 'शेफ और मालिक' },

      // Sub-banner & Mode Switchers
      { en: 'Turn kitchen talk or register photos into exact plate costing without tedious spreadsheet typing.', hi: 'रजिस्टर के पन्नों या बोलकर अपनी रेसिपी बताएं, बिना स्प्रेडशीट के सटीक थाली लागत निकालें।' },
      { en: 'Add Recipe to MenuMitra', hi: 'MenuMitra में नई रेसिपी जोड़ें' },
      { en: 'Add Recipe to Marginly', hi: 'Marginly में नई रेसिपी जोड़ें' },
      { en: 'New Recipe Capture', hi: 'नई रेसिपी कैप्चर' },
      { en: 'AI Ingredient Engine v3.4 Active', hi: 'एआई सामग्री इंजन v3.4 सक्रिय' },
      { en: 'Auto-saves Draft', hi: 'ड्राफ्ट स्वतः सहेजता है' },
      { en: 'Fastest / सबसे आसान', hi: 'सबसे तेज़ / सबसे आसान' },
      { en: 'Fastest', hi: 'सबसे तेज़' },
      { en: 'Speak it', hi: 'बोलकर जोड़ें' },
      { en: 'Natural voice input in Hindi & café dialects', hi: 'हिंदी और रेस्टोरेंट बोलियों में स्वाभाविक आवाज इनपुट' },
      { en: 'Photograph it', hi: 'फोटो खींचें' },
      { en: 'Scan handwritten bahi-khata or dairy recipes', hi: 'हाथ से लिखी बही-खाता या डायरी की रेसिपी स्कैन करें' },
      { en: 'Type it', hi: 'टाइप करें' },
      { en: 'Enter grams, litres, and pack costs manually', hi: 'ग्राम, लीटर और पैकेट की लागत मैन्युअल रूप से दर्ज करें' },

      // Dialect Bar & Mic Recording
      { en: 'Spoken Dialect / बोली:', hi: 'बोली / भाषा चयन:' },
      { en: 'हिन्दी (Hindi - Natural kitchen phrasing)', hi: 'हिन्दी (रसोई की स्वाभाविक भाषा)' },
      { en: 'Garhwali-mix (Doon café slang)', hi: 'गढ़वाली-मिश्रित (कैफ़े शब्दावली)' },
      { en: 'Hinglish / English', hi: 'हिंग्लिश / अंग्रेज़ी' },
      { en: 'LISTENING... Speak clearly', hi: 'सुन रहे हैं... कृपया स्पष्ट बोलें' },
      { en: 'RECORDING... Speak recipe ingredients now', hi: 'रिकॉर्डिंग चालू है... सामग्री बोलें' },
      { en: 'AI TRANSCRIBING... Converting spoken recipe to costs', hi: 'एआई ट्रांसक्राइब कर रहा है... लागत रूपांतरण जारी' },
      { en: 'Finish Speaking & Calculate Cost / हो गया', hi: 'बोलना समाप्त और लागत निकालें / हो गया' },
      { en: 'Finish Speaking', hi: 'बोलना समाप्त' },
      { en: '"Bolo apni recipe, jaise aap kitchen mein bolte ho"', hi: '"बोलो अपनी रेसिपी, जैसे आप किचन में बोलते हो"' },
      { en: 'Speak freely. Mention ingredients in cups, spoons, pouches or grams. Continuous listening is active.', hi: 'खुले तौर पर बोलें। कप, चम्मच, पाउच या ग्राम में सामग्री बताएं।' },
      { en: 'Quick 1-Click Samples / बोल कर देखें:', hi: 'त्वरित 1-क्लिक नमूने / बोल कर देखें:' },
      { en: 'Live Spoken Words / जो बोला गया:', hi: 'लाइव बोले गए शब्द:' },
      { en: 'Mic Ready • Click mic to speak', hi: 'माइक तैयार • बोलने के लिए माइक पर क्लिक करें' },
      { en: 'Mic Standby • Click mic to speak', hi: 'माइक स्टैंडबाय • बोलने के लिए क्लिक करें' },
      { en: 'Mic Ready', hi: 'माइक तैयार' },
      { en: 'Mic Standby', hi: 'माइक स्टैंडबाय' },
      { en: 'Voice Detected', hi: 'आवाज पहचानी गई' },
      { en: 'Listening', hi: 'सुन रहे हैं' },
      { en: 'Transcribing...', hi: 'ट्रांसक्राइब हो रहा है...' },
      { en: 'Recipe Costed!', hi: 'रेसिपी लागत तैयार!' },
      { en: 'Calculate Recipe Cost', hi: 'रेसिपी की लागत निकालें' },

      // Live Kitchen Transcript Box
      { en: 'Live Kitchen Transcript', hi: 'लाइव किचन ट्रांसक्रिप्ट' },
      { en: 'parsed entities detected', hi: 'सामग्रियां पहचानी गईं' },
      { en: 'ingredient(s) detected', hi: 'सामग्रियां पहचानी गईं' },
      { en: 'not on menu', hi: 'मेनू में नहीं' },
      { en: 'ON MENU ✓', hi: 'मेनू में मौजूद ✓' },
      { en: 'NOT ON MENU', hi: 'मेनू में नहीं' },
      { en: 'Not on Menu (₹0)', hi: 'मेनू में नहीं (₹0)' },

      // AI Progress Pipeline Strip
      { en: 'AI Recipe Conversion Engine', hi: 'एआई रेसिपी रूपांतरण इंजन' },
      { en: 'Listening & Transcribing', hi: 'सुनना और लिखना' },
      { en: 'Converting Units', hi: 'इकाई रूपांतरण' },
      { en: 'Plate Cost & Margin', hi: 'थाली लागत और मुनाफा' },
      { en: 'Captured kitchen audio', hi: 'किचन ऑडियो कैप्चर किया गया' },
      { en: 'Standardising café portions', hi: 'मानक रेस्टोरेंट भाग निर्धारित हो रहे हैं' },
      { en: 'Smart Café Defaults Enabled', hi: 'स्मार्ट रेस्टोरेंट मानक सक्रिय' },
      { en: "Don't worry about exact gram weights. We calibrate standard café portions (like 'do chammach' = 20g or 'ek cup' = 200ml) with zero-cost support for home-grown mint/lemon.", hi: "सटीक ग्राम वजन की चिंता न करें। हम सामान्य रसोई भागों (जैसे 'दो चम्मच' = 20 ग्राम या 'एक कप' = 200 मिली) को स्वतः मापते हैं।" },

      // CTA Buttons
      { en: 'Convert to standard recipe & calculate cost', hi: 'मानक रेसिपी में बदलें और लागत निकालें' },
      { en: 'Discard & restart', hi: 'रद्द करें और पुनः शुरू करें' },

      // Live Draft Output Card
      { en: 'Live Draft Output', hi: 'लाइव ड्राफ्ट आउटपुट' },
      { en: 'High Popularity Potential', hi: 'उच्च लोकप्रियता की संभावना' },
      { en: 'Est. Cost of Goods (COGS)', hi: 'अनुमानित खाद्य लागत (COGS)' },
      { en: 'Suggested Menu Price', hi: 'सुझाया गया मेनू मूल्य' },
      { en: 'Total Batch / Portion Cost', hi: 'कुल बैच / प्रति थाली लागत' },
      { en: 'Standard 300ml café tumbler', hi: 'मानक 300 मिली सर्विंग' },
      { en: 'Detected Components (Ready to map):', hi: 'पहचानी गई सामग्रियां (मैपिंग के लिए तैयार):' },
      { en: 'Below ₹30 budget target', hi: '₹30 बजट लक्ष्य से कम' },
      { en: 'Potential STAR if ₹125', hi: '₹125 पर संभावित STAR' },

      // Dashboard & Metric Cards
      { en: 'Avg profit per cover', hi: 'प्रति थाली औसत लाभ' },
      { en: 'Food cost percentage', hi: 'खाद्य लागत प्रतिशत' },
      { en: 'High-risk dishes', hi: 'उच्च जोखिम वाले व्यंजन' },
      { en: 'Monthly profit leak', hi: 'मासिक लाभ रिसाव' },
      { en: 'Selling Price', hi: 'बिक्री मूल्य' },
      { en: 'Food Cost', hi: 'खाद्य लागत' },
      { en: 'Margin', hi: 'मार्जिन' },
      { en: 'Price', hi: 'मूल्य' },
      { en: 'Profit / plate', hi: 'लाभ / थाली' },
      { en: 'Profit / Plate', hi: 'लाभ / थाली' },
      { en: 'Total Profit', hi: 'कुल लाभ' },
      { en: 'View Recipe Costing', hi: 'रेसिपी लागत देखें' },
      { en: 'Add New Dish & Recipe Cost', hi: '+ नया व्यंजन और रेसिपी लागत जोड़ें' },
      { en: 'Category', hi: 'श्रेणी' },
      { en: 'Actions', hi: 'कार्रवाई' },
      { en: 'Search dishes...', hi: 'व्यंजन खोजें...' },

      // Modality 2 (Photograph it)
      { en: 'Capture Kitchen Register / Diary', hi: 'किचन रजिस्टर / डायरी कैप्चर करें' },
      { en: 'Take a live photo of handwritten notes or upload an invoice/recipe card', hi: 'हाथ से लिखे नोट्स की लाइव फोटो लें या इनवॉइस/रेसिपी कार्ड अपलोड करें' },
      { en: 'OCR Ready', hi: 'ओसीआर तैयार' },
      { en: 'Take Live Camera Photo', hi: 'कैमरे से लाइव फोटो लें' },
      { en: 'Instant snapshot from phone/tablet', hi: 'फोन या टैबलेट से तुरंत फोटो लें' },
      { en: 'Upload Bahi-Khata / Image', hi: 'बही-खाता / फोटो अपलोड करें' },
      { en: 'Run AI OCR Scan', hi: 'एआई ओसीआर स्कैन चलाएं' },
      { en: 'Accept Scanned Recipe & Calculate Cost', hi: 'स्कैन की गई रेसिपी स्वीकार करें और लागत निकालें' },

      // Modality 3 (Type it)
      { en: 'Type Recipe Manually', hi: 'रेसिपी मैन्युअल रूप से टाइप करें' },
      { en: 'Enter ingredients with exact weights, packaging prices, or ₹0 kitchen-grown items', hi: 'सटीक वजन, पैकेजिंग मूल्य या ₹0 की स्वदेशी सामग्री दर्ज करें' },
      { en: 'Dish Name / व्यंजन का नाम', hi: 'व्यंजन का नाम' },
      { en: 'Target Portion Cost', hi: 'लक्ष्य प्रति थाली लागत' },
      { en: '+ Add Ingredient Row', hi: '+ सामग्री की पंक्ति जोड़ें' },
      { en: 'Accept Manual Recipe & Calculate Cost', hi: 'मैन्युअल रेसिपी स्वीकार करें और लागत निकालें' },

      // What-If Simulator
      { en: 'Simulate Price & Volume Changes', hi: 'मूल्य और बिक्री बदलाव का सिमुलेशन' },
      { en: 'Projected Monthly Profit', hi: 'अनुमानित मासिक लाभ' },
      { en: 'Profit Impact', hi: 'लाभ पर प्रभाव' },
      { en: 'Baseline Price', hi: 'वर्तमान मूल्य' },
      { en: 'Simulated Price', hi: 'सिम्युलेटेड मूल्य' },
      { en: 'Volume Change', hi: 'बिक्री में बदलाव' },
      { en: 'Test Another Dish', hi: 'दूसरा व्यंजन जांचें' },
      { en: 'Save Scenario', hi: 'परिदृश्य सहेजें' },
      { en: 'Download PDF', hi: 'पीडीएफ डाउनलोड करें' },

      // Footer
      { en: 'MenuMitra Operating System', hi: 'MenuMitra ऑपरेटिंग सिस्टम' },
      { en: 'Marginly Operating System', hi: 'Marginly ऑपरेटिंग सिस्टम' },
      { en: 'Version 2.8.4 (Dehradun Region Server)', hi: 'संस्करण 2.8.4 (देहरादून रीजन सर्वर)' },
      { en: 'Voice Audio Socket Online', hi: 'वॉयस ऑडियो सॉकेट ऑनलाइन' },
      { en: 'Ingredient Price Index (Uttarakhand)', hi: 'सामग्री मूल्य सूचकांक (उत्तराखंड)' },
      { en: 'Help & Hindi Tutorials', hi: 'सहायता और हिंदी ट्यूटोरियल' },
      { en: 'Feedback', hi: 'प्रतिक्रिया' }
    ];

    // Sort translation pairs by length descending so longer phrases match first
    const sortedPairs = pairs.slice().sort((a, b) => b.en.length - a.en.length);
    const sortedHiPairs = pairs.slice().sort((a, b) => b.hi.length - a.hi.length);

    // Fast exact lookup maps
    const exactEnToHi = new Map();
    const exactHiToEn = new Map();
    pairs.forEach(p => {
      exactEnToHi.set(p.en.trim().toLowerCase(), p.hi);
      exactHiToEn.set(p.hi.trim(), p.en);
    });

    const isDevanagari = (str) => /[\u0900-\u097F]/.test(str);

    // TreeWalker for 100% complete bidirectional text translation
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
    let node;
    while ((node = walker.nextNode())) {
      const parent = node.parentElement;
      if (!parent || ['SCRIPT', 'STYLE', 'INPUT', 'TEXTAREA', 'SELECT'].includes(parent.tagName)) continue;
      // Never translate material icon ligatures
      if (parent.classList && (parent.classList.contains('material-symbols-outlined') || parent.classList.contains('material-symbols-filled'))) continue;
      // Never translate the EN/HI toggle buttons themselves
      if (parent.hasAttribute && parent.hasAttribute('data-lang-toggle')) continue;
      if (parent.closest && parent.closest('[data-lang-toggle]')) continue;

      const currentVal = node.nodeValue;
      if (!currentVal || !currentVal.trim()) continue;

      // Initialize or repair _origEnText cache
      if (node._origEnText === undefined) {
        if (!isDevanagari(currentVal)) {
          node._origEnText = currentVal;
        } else {
          // If node was captured already in Hindi, reconstruct its English version
          let recovered = currentVal;
          const trimmed = currentVal.trim();
          if (exactHiToEn.has(trimmed)) {
            recovered = currentVal.replace(trimmed, exactHiToEn.get(trimmed));
          } else {
            for (const p of sortedHiPairs) {
              if (recovered.includes(p.hi)) {
                recovered = recovered.split(p.hi).join(p.en);
              }
            }
          }
          node._origEnText = recovered;
        }
      }

      if (lang === 'en') {
        // Switching to English
        if (node._origEnText && !isDevanagari(node._origEnText)) {
          node.nodeValue = node._origEnText;
        } else {
          // Fallback reverse-translation if _origEnText was missing or contained Hindi
          let text = node.nodeValue;
          const trimmed = text.trim();
          if (exactHiToEn.has(trimmed)) {
            text = text.replace(trimmed, exactHiToEn.get(trimmed));
          } else {
            for (const p of sortedHiPairs) {
              if (text.includes(p.hi)) {
                text = text.split(p.hi).join(p.en);
              }
            }
          }
          node.nodeValue = text;
          node._origEnText = text;
        }
      } else {
        // Switching to Hindi
        const baseEnglish = node._origEnText || currentVal;
        const trimmed = baseEnglish.trim();
        const trimmedLower = trimmed.toLowerCase();

        // 1. Direct exact match (fast & clean)
        if (exactEnToHi.has(trimmedLower)) {
          const hiTranslation = exactEnToHi.get(trimmedLower);
          node.nodeValue = baseEnglish.replace(trimmed, hiTranslation);
        } else {
          // 2. Substring phrase match for complex nodes
          let translated = baseEnglish;
          for (const p of sortedPairs) {
            if (translated.toLowerCase().includes(p.en.toLowerCase())) {
              const regex = new RegExp(escapeRegExp(p.en), 'gi');
              translated = translated.replace(regex, p.hi);
            }
          }
          node.nodeValue = translated;
        }
      }
    }

    // Also translate input/textarea placeholders
    document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(input => {
      if (input._origPlaceholder === undefined) {
        input._origPlaceholder = input.placeholder;
      }
      if (lang === 'en') {
        input.placeholder = input._origPlaceholder;
      } else {
        const ph = input._origPlaceholder.trim().toLowerCase();
        if (exactEnToHi.has(ph)) {
          input.placeholder = exactEnToHi.get(ph);
        } else {
          for (const p of sortedPairs) {
            if (input._origPlaceholder.toLowerCase().includes(p.en.toLowerCase())) {
              input.placeholder = input._origPlaceholder.replace(new RegExp(escapeRegExp(p.en), 'gi'), p.hi);
              break;
            }
          }
        }
      }
    });
  }

  // Helpers for button active/inactive styling (two-button containers)
  function applyBtnActive(btn) {
    // Preserve rounded-full if present
    const isRoundedFull = btn.className.includes('rounded-full');
    const rounded = isRoundedFull ? 'rounded-full' : 'rounded';
    // Preserve px/py sizing
    const pxMatch = btn.className.match(/px-[\d.]+/);
    const pyMatch = btn.className.match(/py-[\d.]+/);
    const px = pxMatch ? pxMatch[0] : 'px-2.5';
    const py = pyMatch ? pyMatch[0] : 'py-1';
    btn.className = `${px} ${py} ${rounded} bg-surface-container-lowest text-primary font-bold shadow-xs transition-all`;
  }

  function applyBtnInactive(btn) {
    const isRoundedFull = btn.className.includes('rounded-full');
    const rounded = isRoundedFull ? 'rounded-full' : 'rounded';
    const pxMatch = btn.className.match(/px-[\d.]+/);
    const pyMatch = btn.className.match(/py-[\d.]+/);
    const px = pxMatch ? pxMatch[0] : 'px-2.5';
    const py = pyMatch ? pyMatch[0] : 'py-1';
    btn.className = `${px} ${py} ${rounded} text-on-surface-variant hover:text-primary transition-colors font-medium`;
  }

  function escapeRegExp(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // 6. Outlet Switcher Dropdown (Req 4)
  function setupOutletDropdown() {
    let outletBtn = document.getElementById('outlet-name')?.closest('button') ||
                    document.querySelector('header .relative.group button') ||
                    document.querySelector('header .hidden.sm\\:flex button');

    if (!outletBtn) {
      document.querySelectorAll('header *').forEach(el => {
        if (!outletBtn && (el.getAttribute('data-icon') === 'storefront' || el.textContent.trim() === 'storefront')) {
          outletBtn = el.closest('.flex.items-center.gap-space-sm, .flex.items-center.space-x-2, .flex.items-center') || el.parentElement;
        }
      });
    }

    if (!outletBtn) return;
    outletBtn.style.cursor = 'pointer';

    // Remove any static preview box that appears on group-hover
    const staticPreview = outletBtn.parentElement?.querySelector('.group-hover\\:block');
    if (staticPreview) {
      staticPreview.classList.remove('group-hover:block');
      staticPreview.classList.add('hidden');
    }

    // Load outlets from localStorage or initialize with user data
    let outlets = [];
    try {
      outlets = JSON.parse(localStorage.getItem('marginly_outlets')) || [];
    } catch (e) {}

    if (outlets.length === 0 && currentUser) {
      outlets = [
        { id: 1, name: `${currentUser.restaurant_name || 'Main Kitchen'}`, location: currentUser.location || 'Central City', active: true },
        { id: 2, name: `${currentUser.restaurant_name || 'Express'} - Branch 2`, location: 'Highway Outlet', active: false }
      ];
      localStorage.setItem('marginly_outlets', JSON.stringify(outlets));
    }

    const dropdownWrapper = outletBtn.closest('.relative') || outletBtn.parentElement;
    dropdownWrapper.style.position = 'relative';
    let menu = dropdownWrapper.querySelector('.outlet-dropdown-menu');

    if (!menu) {
      menu = document.createElement('div');
      menu.className = 'outlet-dropdown-menu hidden absolute left-0 top-full mt-2 w-72 bg-surface-container-lowest rounded-xl custom-shadow-elevated border border-outline-variant/40 p-2 z-50 shadow-xl';
      dropdownWrapper.appendChild(menu);
    }

    function renderOutlets() {
      menu.innerHTML = `
        <div class="flex items-center justify-between px-2.5 py-1.5 border-b border-outline-variant/20 mb-1">
          <span class="text-[11px] font-bold uppercase tracking-wider text-primary">All Restaurant Outlets</span>
          <span class="text-[10px] text-on-surface-variant font-medium">${outlets.length} Outlets</span>
        </div>
        <div class="space-y-1 max-h-60 overflow-y-auto">
          ${outlets.map((o, idx) => `
            <div class="outlet-item flex items-center justify-between p-2 rounded-lg cursor-pointer transition ${o.active ? 'bg-primary-container/10 border border-primary/30 font-bold text-primary' : 'hover:bg-surface-container text-on-surface'}" data-index="${idx}">
              <div class="leading-snug truncate pr-2">
                <div class="text-xs font-semibold truncate">${o.name}</div>
                <div class="text-[10px] text-on-surface-variant/80 truncate">${o.location}</div>
              </div>
              ${o.active ? '<span class="material-symbols-outlined text-primary text-[18px]">check_circle</span>' : ''}
            </div>
          `).join('')}
        </div>
        <div class="pt-2 mt-1 border-t border-outline-variant/20">
          <button id="add-outlet-btn" type="button" class="w-full py-1.5 px-2.5 rounded-lg text-xs font-semibold text-primary hover:bg-primary-container/10 flex items-center justify-center gap-1 transition">
            <span class="material-symbols-outlined text-base">add_business</span>
            <span>+ Add New Outlet / Location</span>
          </button>
        </div>
      `;

      menu.querySelectorAll('.outlet-item').forEach(item => {
        item.onclick = (e) => {
          e.stopPropagation();
          const idx = parseInt(item.getAttribute('data-index'), 10);
          outlets.forEach((o, i) => o.active = (i === idx));
          localStorage.setItem('marginly_outlets', JSON.stringify(outlets));
          const chosen = outlets[idx];
          if (currentUser) {
            currentUser.restaurant_name = chosen.name;
            currentUser.location = chosen.location;
            localStorage.setItem('marginly_user', JSON.stringify(currentUser));
          }
          fixUserProfileData();
          renderOutlets();
          menu.classList.add('hidden');
        };
      });

      const addOutletBtn = menu.querySelector('#add-outlet-btn');
      if (addOutletBtn) {
        addOutletBtn.onclick = (e) => {
          e.stopPropagation();
          const outletName = prompt('Enter New Outlet / Branch Name:', 'Outlet #3 Downtown');
          if (outletName) {
            const outletLoc = prompt('Enter City / Area Location:', 'Indiranagar, Bengaluru');
            outlets.push({
              id: Date.now(),
              name: outletName,
              location: outletLoc || 'Branch Outlet',
              active: true
            });
            outlets.forEach((o, i) => o.active = (i === outlets.length - 1));
            localStorage.setItem('marginly_outlets', JSON.stringify(outlets));
            if (currentUser) {
              currentUser.restaurant_name = outletName;
              currentUser.location = outletLoc || '';
              localStorage.setItem('marginly_user', JSON.stringify(currentUser));
            }
            fixUserProfileData();
            renderOutlets();
            menu.classList.add('hidden');
          }
        };
      }
    }

    renderOutlets();

    outletBtn.onclick = (e) => {
      e.stopPropagation();
      menu.classList.toggle('hidden');
    };

    document.addEventListener('click', (e) => {
      if (!dropdownWrapper.contains(e.target)) {
        menu.classList.add('hidden');
      }
    });
  }

  // 7. Notification Center & Channel Auth (Req 4, Req 9)
  function setupNotificationCenter() {
    let bellBtn = null;
    document.querySelectorAll('header button').forEach(b => {
      const icon = b.querySelector('.material-symbols-outlined, .material-symbols');
      const iconText = icon ? icon.textContent.trim() : '';
      if (b.textContent.includes('notifications') || b.querySelector('[data-icon="notifications"]') || iconText === 'notifications') {
        bellBtn = b;
      }
    });

    if (!bellBtn) return;

    const bellWrapper = bellBtn.parentElement;
    bellWrapper.style.position = 'relative';

    let notifMenu = bellWrapper.querySelector('.notif-dropdown-menu');
    if (!notifMenu) {
      notifMenu = document.createElement('div');
      notifMenu.className = 'notif-dropdown-menu hidden absolute right-0 top-full mt-2 w-80 sm:w-96 bg-surface-container-lowest rounded-2xl custom-shadow-elevated border border-outline-variant/40 p-4 z-50 shadow-2xl';
      bellWrapper.appendChild(notifMenu);
    }

    function renderNotifMenu() {
      const userPhone = currentUser?.phone || '+91 98765 43210';

      notifMenu.innerHTML = `
        <div class="flex items-center justify-between pb-3 border-b border-outline-variant/20">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-primary text-xl">notifications_active</span>
            <span class="font-bold text-sm text-on-surface">Live Market & Price Radar</span>
          </div>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-error-container text-on-error-container">2 Alert(s)</span>
        </div>

        <div class="py-3 space-y-2.5 max-h-56 overflow-y-auto">
          <div class="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5">
            <span class="material-symbols-outlined text-amber-600 text-lg shrink-0 mt-0.5">trending_up</span>
            <div>
              <div class="text-xs font-bold text-amber-900">Dairy Price Surge: Amul Milk +8%</div>
              <div class="text-[11px] text-amber-800 leading-tight mt-0.5">Local mandi rate jumped from ₹58 to ₹64/L. Cold Coffee margin drops 3.2%.</div>
              <span class="text-[9px] text-amber-700 font-semibold mt-1 inline-block">18 mins ago</span>
            </div>
          </div>

          <div class="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-start gap-2.5">
            <span class="material-symbols-outlined text-emerald-600 text-lg shrink-0 mt-0.5">trending_down</span>
            <div>
              <div class="text-xs font-bold text-emerald-900">Cooking Oil Mandi Dip: -4%</div>
              <div class="text-[11px] text-emerald-800 leading-tight mt-0.5">Refined oil wholesale down by ₹6/L in your region. Profit opportunity.</div>
              <span class="text-[9px] text-emerald-700 font-semibold mt-1 inline-block">2 hours ago</span>
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-outline-variant/20 space-y-2.5">
          <div class="bg-surface-container p-2.5 rounded-xl border border-outline-variant/30">
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs font-bold text-primary flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">sms</span>
                SMS / WhatsApp Alert Channel
              </span>
              <span class="text-[9px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded">Active</span>
            </div>
            <p class="text-[10px] text-on-surface-variant leading-tight mb-2">
              Receive automated Mandi price spike alerts before your distributor charges higher rates.
            </p>
            <div class="flex gap-1.5">
              <input id="notif-contact-input" type="text" value="${userPhone}" class="flex-1 px-2.5 py-1.5 text-xs bg-surface border border-outline-variant rounded-lg text-on-surface font-medium focus:outline-none focus:ring-1 focus:ring-primary" placeholder="Enter phone or email" />
              <button id="save-notif-channel" type="button" class="px-3 py-1.5 bg-primary text-on-primary text-xs font-bold rounded-lg hover:bg-primary-container transition shadow-xs">
                Save
              </button>
            </div>
            <div id="channel-saved-msg" class="text-[10px] text-emerald-700 font-semibold mt-1 hidden">✓ Alert channel updated!</div>
          </div>

          <a href="/menumitra_add_recipe_smart_voice_photo_capture/code.html" class="w-full py-2 px-3 rounded-xl bg-primary-container text-on-primary text-xs font-bold flex items-center justify-center gap-1.5 hover:bg-primary transition shadow-sm">
            <span class="material-symbols-outlined text-base">add_circle</span>
            <span>+ Add Menu Dish to Price Watchlist</span>
          </a>
        </div>
      `;

      const saveBtn = notifMenu.querySelector('#save-notif-channel');
      const input = notifMenu.querySelector('#notif-contact-input');
      const savedMsg = notifMenu.querySelector('#channel-saved-msg');

      if (saveBtn && input) {
        saveBtn.onclick = (e) => {
          e.stopPropagation();
          const val = input.value.trim();
          if (val && currentUser) {
            currentUser.phone = val;
            localStorage.setItem('marginly_user', JSON.stringify(currentUser));
            savedMsg.classList.remove('hidden');
            setTimeout(() => savedMsg.classList.add('hidden'), 2500);
          }
        };
      }
    }

    renderNotifMenu();

    bellBtn.onclick = (e) => {
      e.stopPropagation();
      notifMenu.classList.toggle('hidden');
    };

    document.addEventListener('click', (e) => {
      if (!bellWrapper.contains(e.target)) {
        notifMenu.classList.add('hidden');
      }
    });
  }

  // 8. Profile Modal & Sign Out (Req 1 & Req 3)
  function setupProfileAndLogoutModal() {
    let profileTrigger = document.querySelector('header .flex.items-center.space-x-2.pl-1, header .flex.items-center.gap-2.pl-2');
    if (!profileTrigger) {
      document.querySelectorAll('header *').forEach(el => {
        if (el.textContent && (el.textContent.includes('VA') || (currentUser && el.textContent.includes(currentUser.display_name)))) {
          if (el.closest('.flex.items-center')) profileTrigger = el.closest('.flex.items-center');
        }
      });
    }

    // Also ensure a visible Logout button exists in the header
    const headerRightContainer = document.querySelector('header .flex.items-center.space-x-3, header .flex.items-center.space-x-4, header .flex.items-center.gap-3');
    if (headerRightContainer && !headerRightContainer.querySelector('button[title*="Sign Out"], button[title*="Log Out"], button[onclick*="logout"]')) {
      const logoutBtn = document.createElement('button');
      logoutBtn.className = 'p-1.5 rounded-lg hover:bg-surface-container text-on-surface-variant hover:text-error transition-colors';
      logoutBtn.title = 'Sign Out / Log Out';
      logoutBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">logout</span>';
      logoutBtn.onclick = window.logout;
      headerRightContainer.appendChild(logoutBtn);
    }

    // Create modal backdrop and dialog if not already created
    let modal = document.getElementById('marginly-profile-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'marginly-profile-modal';
      modal.className = 'fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 hidden';
      document.body.appendChild(modal);
    }

    function updateModalContent() {
      const u = currentUser || {
        username: 'abc123',
        display_name: 'Ayush Anand',
        restaurant_name: 'Doon Bistro & Kitchen',
        cuisine_type: 'Multi-Cuisine',
        location: 'Rajpur Road, Dehradun',
        phone: '+91 98765 43210'
      };

      const initials = (u.display_name || u.username)
        .split(' ')
        .map(p => p[0])
        .join('')
        .substring(0, 2)
        .toUpperCase();

      modal.innerHTML = `
        <div class="bg-surface rounded-2xl max-w-md w-full border border-outline-variant/40 shadow-2xl overflow-hidden p-6 space-y-5">
          <div class="flex items-center justify-between pb-3 border-b border-outline-variant/30">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 rounded-2xl bg-primary-container text-on-primary font-bold text-lg flex items-center justify-center shadow-md">
                ${initials}
              </div>
              <div>
                <h3 class="font-bold text-base text-on-surface">${u.display_name || u.username}</h3>
                <span class="text-xs text-primary font-semibold">@${u.username} • Owner & Head Chef</span>
              </div>
            </div>
            <button id="close-profile-modal" class="w-8 h-8 rounded-full hover:bg-surface-container flex items-center justify-center text-outline transition">
              <span class="material-symbols-outlined text-lg">close</span>
            </button>
          </div>

          <div class="space-y-3 text-xs">
            <div class="flex items-center justify-between p-3 rounded-xl bg-surface-container">
              <span class="text-on-surface-variant font-medium">Restaurant / Outlet:</span>
              <span class="font-bold text-on-surface">${u.restaurant_name}</span>
            </div>
            <div class="flex items-center justify-between p-3 rounded-xl bg-surface-container">
              <span class="text-on-surface-variant font-medium">Cuisine Calibration:</span>
              <span class="font-bold text-primary">${u.cuisine_type || 'Multi-Cuisine'}</span>
            </div>
            <div class="flex items-center justify-between p-3 rounded-xl bg-surface-container">
              <span class="text-on-surface-variant font-medium">Region / Location:</span>
              <span class="font-bold text-on-surface">${u.location || 'Local Mandi'}</span>
            </div>
            <div class="flex items-center justify-between p-3 rounded-xl bg-surface-container">
              <span class="text-on-surface-variant font-medium">Contact Phone:</span>
              <span class="font-bold text-on-surface">${u.phone || 'Not linked'}</span>
            </div>
          </div>

          <div class="pt-2 flex flex-col gap-2">
            <a href="/register.html" class="w-full py-2.5 px-4 rounded-xl border border-outline-variant text-on-surface hover:bg-surface-container text-center text-xs font-semibold flex items-center justify-center gap-1.5 transition">
              <span class="material-symbols-outlined text-base">store</span>
              <span>Register Another Restaurant / Edit Onboarding</span>
            </a>
            
            <button id="logout-btn" type="button" class="w-full py-2.5 px-4 rounded-xl bg-error text-on-error hover:bg-red-700 text-center text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm transition">
              <span class="material-symbols-outlined text-base">logout</span>
              <span>Sign Out / Log Out of Marginly</span>
            </button>
          </div>
        </div>
      `;

      modal.querySelector('#close-profile-modal').onclick = () => modal.classList.add('hidden');
      modal.onclick = (e) => {
        if (e.target === modal) modal.classList.add('hidden');
      };
      modal.querySelector('#logout-btn').onclick = window.logout;
    }

    if (profileTrigger) {
      profileTrigger.style.cursor = 'pointer';
      profileTrigger.title = 'Click to view profile & sign out';
      profileTrigger.onclick = (e) => {
        // If clicked specifically on the logout button inside the container, don't open modal
        if (e.target.closest('button[onclick*="logout"]')) return;
        e.stopPropagation();
        updateModalContent();
        modal.classList.remove('hidden');
      };
    }
  }

  // 7. Simple, Sleek Dark Mode (Req 2)
  function setupDarkMode() {
    // Inject Dark Mode Stylesheet once if not present
    if (!document.getElementById('marginly-dark-mode-styles')) {
      const style = document.createElement('style');
      style.id = 'marginly-dark-mode-styles';
      style.textContent = `
        html.dark {
          color-scheme: dark;
        }
        html.dark body {
          background-color: #111414 !important;
          color: #e2e8f0 !important;
        }
        html.dark .bg-background,
        html.dark .bg-surface,
        html.dark .bg-surface-bright {
          background-color: #111414 !important;
        }
        html.dark .bg-surface-container,
        html.dark .bg-surface-container-low,
        html.dark .bg-surface-container-high,
        html.dark .bg-surface-container-highest {
          background-color: #191f1f !important;
        }
        html.dark .bg-surface-container-lowest {
          background-color: #1e2525 !important;
        }
        html.dark .text-on-surface {
          color: #f1f5f9 !important;
        }
        html.dark .text-on-surface-variant {
          color: #94a3b8 !important;
        }
        html.dark .text-primary {
          color: #90d2d1 !important;
        }
        html.dark header, html.dark nav {
          background-color: #151a1a !important;
          border-color: #273131 !important;
        }
        html.dark .border-outline-variant,
        html.dark .border-outline-variant\\/40,
        html.dark .border-outline-variant\\/30,
        html.dark .border-outline-variant\\/20,
        html.dark .border-outline-variant\\/60,
        html.dark [class*="border-outline"] {
          border-color: #2d3838 !important;
        }
        html.dark .level-1-card, html.dark article {
          background-color: #1a2121 !important;
          border-color: #2c3737 !important;
        }
        html.dark input, html.dark select, html.dark textarea {
          background-color: #161c1c !important;
          color: #f1f5f9 !important;
          border-color: #354242 !important;
        }
        html.dark .shadow-sm, html.dark .shadow-md, html.dark .shadow-xl {
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45) !important;
        }
        html.dark footer {
          background-color: #131717 !important;
          border-color: #242c2c !important;
        }
      `;
      document.head.appendChild(style);
    }

    const currentTheme = localStorage.getItem('marginly_theme') || 'light';
    const isDark = currentTheme === 'dark';
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    // Insert toggle button if not already present
    if (!document.getElementById('marginly-theme-toggle')) {
      const toggleBtn = document.createElement('button');
      toggleBtn.id = 'marginly-theme-toggle';
      toggleBtn.type = 'button';
      toggleBtn.className = 'w-8 h-8 rounded-lg bg-surface-container hover:bg-surface-container-high flex items-center justify-center text-on-surface-variant hover:text-primary transition-all border border-outline-variant/30 cursor-pointer shrink-0';
      toggleBtn.title = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';
      toggleBtn.innerHTML = `<span class="material-symbols-outlined text-[18px]">${isDark ? 'light_mode' : 'dark_mode'}</span>`;

      toggleBtn.onclick = (e) => {
        e.preventDefault();
        const nextDark = !document.documentElement.classList.contains('dark');
        if (nextDark) {
          document.documentElement.classList.add('dark');
          localStorage.setItem('marginly_theme', 'dark');
          toggleBtn.title = 'Switch to Light Mode';
          toggleBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">light_mode</span>';
        } else {
          document.documentElement.classList.remove('dark');
          localStorage.setItem('marginly_theme', 'light');
          toggleBtn.title = 'Switch to Dark Mode';
          toggleBtn.innerHTML = '<span class="material-symbols-outlined text-[18px]">dark_mode</span>';
        }
      };

      // Place toggle button beside the language switcher or notifications
      const headerRightCluster = document.querySelector('header .flex.items-center.space-x-3, header .flex.items-center.gap-3, header .flex.items-center.gap-2, header .flex.items-center');
      const langContainer = document.querySelector('header div:has(> button)');
      if (langContainer && langContainer.parentElement) {
        langContainer.parentElement.insertBefore(toggleBtn, langContainer);
      } else if (headerRightCluster) {
        headerRightCluster.appendChild(toggleBtn);
      }
    }
  }

})();
