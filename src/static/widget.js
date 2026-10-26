/**
 * TPC Student Clearance Assistant - Embeddable Popup Widget
 * Talibon Polytechnic College
 *
 * Usage:
 *   <script src="https://minicap-production.up.railway.app/widget.js" async></script>
 */
(function() {
    'use strict';

    if (window.__TPC_WIDGET_INITIALIZED__) return;
    window.__TPC_WIDGET_INITIALIZED__ = true;

    // Detect base URL from currentScript
    let baseUrl = '';
    try {
        const script = document.currentScript || (function() {
            const scripts = document.getElementsByTagName('script');
            for (let i = scripts.length - 1; i >= 0; i--) {
                if (scripts[i].src && scripts[i].src.indexOf('widget.js') !== -1) {
                    return scripts[i];
                }
            }
            return null;
        })();
        if (script && script.src) {
            const url = new URL(script.src);
            baseUrl = url.origin;
        }
    } catch (e) {
        baseUrl = window.location.origin;
    }
    if (!baseUrl) {
        baseUrl = window.location.origin;
    }

    const widgetUrl = baseUrl + '/widget';
    let isOpen = false;
    let isIframeLoaded = false;

    // Create style element
    const style = document.createElement('style');
    style.id = 'tpc-widget-styles';
    style.textContent = `
        /* TPC Widget Host Styles */
        #tpc-widget-launcher {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
            box-shadow: 0 8px 24px rgba(37, 99, 235, 0.38), 0 2px 6px rgba(15, 23, 42, 0.15);
            border: 2px solid rgba(255, 255, 255, 0.9);
            cursor: pointer;
            z-index: 2147483640;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.25s ease;
            outline: none;
            padding: 0;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }

        #tpc-widget-launcher:hover {
            transform: scale(1.08);
            box-shadow: 0 12px 30px rgba(37, 99, 235, 0.48), 0 4px 10px rgba(15, 23, 42, 0.2);
        }

        #tpc-widget-launcher:active {
            transform: scale(0.95);
        }

        #tpc-widget-launcher .tpc-launcher-icon,
        #tpc-widget-launcher .tpc-launcher-close {
            position: absolute;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.25s ease, opacity 0.25s ease;
        }

        #tpc-widget-launcher .tpc-launcher-icon {
            opacity: 1;
            transform: scale(1) rotate(0deg);
        }

        #tpc-widget-launcher .tpc-launcher-close {
            opacity: 0;
            transform: scale(0.5) rotate(-90deg);
        }

        #tpc-widget-launcher.open .tpc-launcher-icon {
            opacity: 0;
            transform: scale(0.5) rotate(90deg);
        }

        #tpc-widget-launcher.open .tpc-launcher-close {
            opacity: 1;
            transform: scale(1) rotate(0deg);
        }

        /* Online pulse badge */
        #tpc-widget-badge {
            position: absolute;
            top: 2px;
            right: 2px;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #10b981;
            border: 2.5px solid #ffffff;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
        }

        /* Teaser Pill Tooltip */
        #tpc-widget-teaser {
            position: fixed;
            bottom: 94px;
            right: 24px;
            background: #ffffff;
            color: #0f172a;
            padding: 0.65rem 1rem;
            border-radius: 12px;
            box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.18), 0 0 0 1px rgba(15, 23, 42, 0.08);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 2147483639;
            cursor: pointer;
            transition: opacity 0.25s ease, transform 0.25s ease;
            white-space: nowrap;
            animation: tpcFloatTeaser 3s ease-in-out infinite;
        }

        @keyframes tpcFloatTeaser {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-4px); }
        }

        #tpc-widget-teaser .teaser-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #2563eb;
        }

        #tpc-widget-teaser .teaser-close {
            background: transparent;
            border: none;
            color: #94a3b8;
            cursor: pointer;
            padding: 2px;
            margin-left: 4px;
            font-size: 14px;
            line-height: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        #tpc-widget-teaser .teaser-close:hover {
            color: #0f172a;
        }

        /* The Iframe Container (Pop-up Modal / Docked Box) */
        #tpc-widget-container {
            position: fixed;
            bottom: 96px;
            right: 24px;
            width: 390px;
            max-width: calc(100vw - 32px);
            height: 600px;
            max-height: calc(100vh - 120px);
            border-radius: 18px;
            box-shadow: 0 20px 50px -10px rgba(15, 23, 42, 0.28), 0 0 0 1px rgba(15, 23, 42, 0.08);
            z-index: 2147483645;
            overflow: hidden;
            background: #ffffff;
            border: none;
            opacity: 0;
            visibility: hidden;
            pointer-events: none;
            transform: translateY(20px) scale(0.96);
            transform-origin: bottom right;
            transition: opacity 0.25s cubic-bezier(0.16, 1, 0.3, 1),
                        transform 0.25s cubic-bezier(0.16, 1, 0.3, 1),
                        visibility 0.25s;
        }

        #tpc-widget-container.active {
            opacity: 1;
            visibility: visible;
            pointer-events: auto;
            transform: translateY(0) scale(1);
        }

        #tpc-widget-container iframe {
            width: 100%;
            height: 100%;
            border: none;
            display: block;
            background: #ffffff;
        }

        /* Mobile Screens (<= 640px) */
        @media (max-width: 640px) {
            #tpc-widget-launcher {
                bottom: 84px !important; /* Floats safely above mobile bottom navigation bar */
                right: 16px !important;
                width: 52px !important;
                height: 52px !important;
            }

            #tpc-widget-teaser {
                bottom: 144px !important;
                right: 16px !important;
            }

            #tpc-widget-container {
                bottom: 0 !important;
                right: 0 !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                max-width: 100vw !important;
                height: 100% !important;
                height: 100dvh !important;
                max-height: 100dvh !important;
                border-radius: 0 !important;
                box-shadow: none !important;
                transform: translateY(100%);
                transform-origin: center bottom;
            }

            #tpc-widget-container.active {
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(style);

    // Create Launcher Button
    const launcher = document.createElement('button');
    launcher.id = 'tpc-widget-launcher';
    launcher.setAttribute('aria-label', 'Toggle TPC Clearance Assistant Chat');
    launcher.setAttribute('title', 'TPC Student Clearance Assistant');
    launcher.innerHTML = `
        <div class="tpc-launcher-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
        </div>
        <div class="tpc-launcher-close">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </div>
        <div id="tpc-widget-badge"></div>
    `;

    // Create Teaser Pill
    const teaser = document.createElement('div');
    teaser.id = 'tpc-widget-teaser';
    teaser.innerHTML = `
        <span class="teaser-dot"></span>
        <span>Need clearance help? Ask AI</span>
        <button type="button" class="teaser-close" title="Dismiss">&times;</button>
    `;

    // Create Container & Iframe
    const container = document.createElement('div');
    container.id = 'tpc-widget-container';

    let iframe = null;

    function initIframe() {
        if (isIframeLoaded) return;
        iframe = document.createElement('iframe');
        iframe.src = widgetUrl;
        iframe.title = 'TPC Student Clearance Assistant';
        iframe.setAttribute('allow', 'clipboard-write');
        container.appendChild(iframe);
        isIframeLoaded = true;
    }

    function openWidget() {
        if (isOpen) return;
        initIframe();
        isOpen = true;
        launcher.classList.add('open');
        container.classList.add('active');
        if (teaser && teaser.parentNode) {
            teaser.style.display = 'none';
        }

        // On mobile, lock background scroll so the experience feels native
        if (window.innerWidth <= 640) {
            document.body.dataset.tpcPrevOverflow = document.body.style.overflow || '';
            document.body.style.overflow = 'hidden';
        }
    }

    function closeWidget() {
        if (!isOpen) return;
        isOpen = false;
        launcher.classList.remove('open');
        container.classList.remove('active');

        // Restore background scroll on mobile
        if (window.innerWidth <= 640) {
            document.body.style.overflow = document.body.dataset.tpcPrevOverflow || '';
        }
    }

    function toggleWidget() {
        if (isOpen) {
            closeWidget();
        } else {
            openWidget();
        }
    }

    launcher.addEventListener('click', toggleWidget);

    teaser.addEventListener('click', function(e) {
        if (e.target.classList.contains('teaser-close')) {
            e.stopPropagation();
            teaser.style.display = 'none';
        } else {
            openWidget();
        }
    });

    // Listen for postMessage from inside iframe (e.g. close or minimize button clicks)
    window.addEventListener('message', function(event) {
        if (!event.data) return;
        if (event.data.type === 'tpc_close_widget' || event.data.type === 'tpc_minimize_widget') {
            closeWidget();
        } else if (event.data.type === 'tpc_open_widget') {
            openWidget();
        }
    });

    // Append to document
    function mount() {
        if (!document.body) {
            window.addEventListener('DOMContentLoaded', mount);
            return;
        }
        document.body.appendChild(container);
        document.body.appendChild(launcher);
        document.body.appendChild(teaser);

        // Preload iframe after 1.5s idle so it opens with zero lag
        setTimeout(function() {
            if (!isIframeLoaded) {
                initIframe();
            }
        }, 1500);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', mount);
    } else {
        mount();
    }

    // Expose programmatic API to host window
    window.TPCChatAssistant = {
        open: openWidget,
        close: closeWidget,
        toggle: toggleWidget,
        isOpen: function() { return isOpen; }
    };
})();
