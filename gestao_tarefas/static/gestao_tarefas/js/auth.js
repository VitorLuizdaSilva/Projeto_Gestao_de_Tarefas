function getCookie(name) {
    const found = document.cookie.split(";").map(item => item.trim()).find(item => item.startsWith(`${name}=`));
    return found ? decodeURIComponent(found.substring(name.length + 1)) : null;
}

async function getCsrf() {
    const response = await fetch("/api/auth/csrf/", {credentials:"same-origin"});
    if (!response.ok) throw new Error("Não foi possível iniciar a proteção CSRF.");
    const token = getCookie("csrftoken");
    if (!token) throw new Error("Cookie CSRF não encontrado.");
    return token;
}

function formatApiError(data) {
    if (typeof data?.detail === "string") return data.detail;
    return Object.entries(data || {}).map(([field, errors]) =>
        `${field}: ${Array.isArray(errors) ? errors.join(", ") : String(errors)}`
    ).join(" · ") || "Não foi possível concluir a operação.";
}

async function login(username, password) {
    const csrf = await getCsrf();
    const response = await fetch("/api/auth/login/", {
        method:"POST",
        credentials:"same-origin",
        headers:{"Content-Type":"application/json","X-CSRFToken":csrf},
        body:JSON.stringify({username,password})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(formatApiError(data));
    if (!data.access) throw new Error("A API não retornou o access token.");
    sessionStorage.setItem("accessToken", data.access);
    window.location.replace("/home/");
}

const loginForm = document.getElementById("login-form");
if (loginForm) {
    loginForm.addEventListener("submit", async event => {
        event.preventDefault();
        const message = document.getElementById("login-message");
        const button = loginForm.querySelector('button[type="submit"]');
        button.disabled = true;
        message.textContent = "Entrando...";
        try {
            await login(
                document.getElementById("username").value.trim(),
                document.getElementById("password").value
            );
        } catch (error) {
            message.textContent = error.message;
            button.disabled = false;
        }
    });
}

const registerForm = document.getElementById("register-form");
if (registerForm) {
    registerForm.addEventListener("submit", async event => {
        event.preventDefault();
        const message = document.getElementById("register-message");
        const button = registerForm.querySelector('button[type="submit"]');
        const username = document.getElementById("reg-username").value.trim();
        const email = document.getElementById("reg-email").value.trim();
        const password = document.getElementById("reg-password").value;
        const password2 = document.getElementById("reg-password2").value;
        if (password !== password2) {
            message.textContent = "As senhas não coincidem.";
            return;
        }
        button.disabled = true;
        message.textContent = "Criando sua conta...";
        try {
            const response = await fetch("/api/auth/cadastro/", {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({username,email,password,password2})
            });
            const data = await response.json();
            if (!response.ok) throw new Error(formatApiError(data));
            await login(username, password);
        } catch (error) {
            message.textContent = error.message;
            button.disabled = false;
        }
    });
}
