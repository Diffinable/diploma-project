console.log('header.js: Script loaded');

// Check if token exists in global scope, otherwise initialize it
if (typeof window.token === 'undefined') {
    window.token = localStorage.getItem('token');
}
console.log('header.js: Initial token from localStorage:', window.token);

// Function to decode JWT token (base64url decode)
function decodeJWT(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) {
        console.error('header.js: Failed to decode JWT:', e);
        return null;
    }
}

// Function to check if token has expired
function isTokenExpired(token) {
    if (!token) return true;
    const payload = decodeJWT(token);
    if (!payload || !payload.exp) return true;
    const currentTime = Math.floor(Date.now() / 1000); // Current time in seconds
    return payload.exp < currentTime;
}

// Function to validate token with an API call
async function validateToken() {
    if (!window.token) {
        console.log('header.js: No token to validate');
        return false;
    }
    try {
        const response = await fetch('http://localhost:8000/repairs/me', {
            headers: { 'Authorization': `Bearer ${window.token}` }
        });
        if (!response.ok) {
            console.log('header.js: Token validation failed with status:', response.status, await response.text());
            return false;
        }
        console.log('header.js: Token validated successfully');
        return true;
    } catch (error) {
        console.error('header.js: Token validation failed:', error.message);
        return false;
    }
}

// Function to validate phone number (Russian format: +7 followed by 10 digits)
function isValidPhoneNumber(phone) {
    const phoneRegex = /^\+7\d{10}$/;
    return phoneRegex.test(phone);
}

// Function to update tab visibility based on authentication status
async function updateTabVisibility() {
    const loginTab = document.getElementById('loginTab');
    const cabinetTab = document.getElementById('cabinetTab');
    const logoutTab = document.getElementById('logoutTab');
    const homeBtn = document.getElementById('homeBtn');

    if (!loginTab || !cabinetTab || !logoutTab || !homeBtn) {
        console.error('header.js: One or more tab elements are missing');
        return;
    }

    let isAuthenticated = !!localStorage.getItem('token');
    if (isAuthenticated && isTokenExpired(localStorage.getItem('token'))) {
        console.log('header.js: Token has expired');
        localStorage.removeItem('token');
        window.token = null;
        isAuthenticated = false;
    } else if (isAuthenticated) {
        isAuthenticated = await validateToken();
        if (!isAuthenticated) {
            console.log('header.js: Token validation failed with server');
            localStorage.removeItem('token');
            window.token = null;
        } else {
            console.log('header.js: User is authenticated');
            window.token = localStorage.getItem('token');
        }
    }

    console.log('header.js: Setting tab visibility - isAuthenticated:', isAuthenticated);
    loginTab.style.display = isAuthenticated ? 'none' : 'inline';
    cabinetTab.style.display = isAuthenticated ? 'inline-block' : 'none';
    logoutTab.style.display = isAuthenticated ? 'inline' : 'none';

    if (isAuthenticated && logoutTab) {
        logoutTab.onclick = (e) => {
            console.log('header.js: Direct logout event handler triggered');
            e.preventDefault();
            logout();
        };
    }

    // Normalize the path for comparison
    const currentPath = window.location.pathname.toLowerCase();
    console.log('header.js: Current path:', currentPath);

    // Remove active class from all tabs/buttons
    [homeBtn, cabinetTab, loginTab].forEach(tab => {
        if (tab) tab.classList.remove('active');
    });

    // Check if we're on the index page (calculator)
    if (currentPath === '/static/index.html' || currentPath === '/static/' || currentPath === '/' || currentPath === '/index.html') {
        console.log('header.js: Activating homeBtn');
        homeBtn.classList.add('active');
    } else if (currentPath.includes('cabinet.html')) {
        console.log('header.js: Activating cabinetTab');
        cabinetTab.classList.add('active');
    }
}

// Function to show Call Me Back modal
function showCallBackModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'callBackModal';
    modal.innerHTML = `
        <div class="modal-content">
            <h2>Перезвоните мне</h2>
            <form id="callBackForm">
                <div class="form-group">
                    <label for="callBackPhone">Ваш номер телефона:</label>
                    <input type="tel" id="callBackPhone" placeholder="+71234567890" pattern="\+7\d{10}" required>
                </div>
                <div class="modal-buttons">
                    <button type="button" id="cancelCallBack" class="cancel">Отмена</button>
                    <button type="submit" id="submitCallBack" class="submit" disabled>Перезвоните мне</button>
                </div>
            </form>
            <p id="callBackError" class="error"></p>
        </div>
    `;
    document.body.appendChild(modal);

    const phoneInput = document.getElementById('callBackPhone');
    const submitButton = document.getElementById('submitCallBack');
    const errorMessage = document.getElementById('callBackError');

    phoneInput.addEventListener('input', () => {
        const phoneValue = phoneInput.value;
        if (isValidPhoneNumber(phoneValue)) {
            submitButton.disabled = false;
            errorMessage.style.display = 'none';
        } else {
            submitButton.disabled = true;
            errorMessage.textContent = 'Please enter a valid number (e.g., +71234567890)';
            errorMessage.style.display = 'block';
        }
    });

    document.getElementById('callBackForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const phone = phoneInput.value;
        try {
            const response = await fetch('http://localhost:8000/repairs/call-back', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone })
            });
            if (!response.ok) throw new Error('Failed to submit request');
            alert('Request submitted successfully! We will contact you shortly.');
            closeCallBackModal();
        } catch (error) {
            errorMessage.textContent = 'Error: ' + error.message;
            errorMessage.style.display = 'block';
        }
    });

    document.getElementById('cancelCallBack').addEventListener('click', () => {
        closeCallBackModal();
    });
}

// Function to close Call Me Back modal
function closeCallBackModal() {
    const modal = document.getElementById('callBackModal');
    if (modal) modal.remove();
}

document.addEventListener('DOMContentLoaded', async () => {
    console.log('header.js: DOMContentLoaded');
    
    if (typeof window.token === 'undefined') {
        window.token = localStorage.getItem('token');
    }

    await updateTabVisibility();

    setupEventListeners();

    // Add Event listener for Call Me Back button
    const callBackBtn = document.getElementById('callBackBtn');
    if (callBackBtn) {
        callBackBtn.addEventListener('click', () => {
            console.log('header.js: Call Back button clicked');
            showCallBackModal();
        });
    }

    // Add Event listener for Home button
    const homeBtn = document.getElementById('homeBtn');
    if (homeBtn) {
        homeBtn.addEventListener('click', (e) => {
            console.log('header.js: Home Button clicked');
            e.preventDefault(); // Prevent default button behavior
            window.location.href = '/static/index.html'; // Navigate to index.html
        });
    }
});

function setupEventListeners() {
    const navTabs = document.querySelector('.nav-tabs');
    const homeBtn = document.querySelector('#homeBtn');
    if (!navTabs || !homeBtn) {
        console.error('header.js: Navigation elements not found');
        return;
    }

    navTabs.addEventListener('click', async (e) => {
        console.log('header.js: Click detected in nav-tabs', e.target.id);
        const target = e.target;
        if (target.id === 'cabinetTab') {
            e.preventDefault();
            if (window.token && !isTokenExpired(window.token) && await validateToken()) {
                target.classList.add('active');
                window.location.href = target.href;
            } else {
                const loginEvent = new Event('showLoginModal');
                document.dispatchEvent(loginEvent);
            }
        } else if (target.id === 'logoutTab') {
            console.log('logout');
            e.preventDefault();
            logout();
        }
    });

    document.addEventListener('userLoggedIn', async () => {
        console.log('header.js: User logged in event received');
        window.token = localStorage.getItem('token');
        await updateTabVisibility();
    });
}

async function logout() {
    console.log('Logging out');
    localStorage.removeItem('token');
    window.token = null;
    await updateTabVisibility();
    setTimeout(() => {
        window.location.href = '/static/index.html';
    }, 100);
}

console.log('header.js: Event listeners attached');