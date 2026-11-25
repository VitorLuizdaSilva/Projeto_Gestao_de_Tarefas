// NexTask front-end: a autenticação e todas as operações de negócio passam pela API DRF.
let accessToken = sessionStorage.getItem("accessToken");
let currentUser = null;
let tasks = [];
let teams = [];
let users = [];
let editingTaskId = null;
let editingTeamId = null;
let managingTeamId = null;
let currentPage = "board";

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function cookie(name) {
    const item = document.cookie.split(";").map(v => v.trim()).find(v => v.startsWith(`${name}=`));
    return item ? decodeURIComponent(item.substring(name.length + 1)) : null;
}

async function csrfToken() {
    const response = await fetch("/api/auth/csrf/", { credentials: "same-origin" });
    if (!response.ok) throw new Error("Não foi possível obter o token CSRF.");
    const token = cookie("csrftoken");
    if (!token) throw new Error("Token CSRF não encontrado.");
    return token;
}

async function refreshToken() {
    const csrf = await csrfToken();
    const response = await fetch("/api/auth/refresh/", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRFToken": csrf }
    });
    if (!response.ok) {
        sessionStorage.removeItem("accessToken");
        accessToken = null;
        window.location.replace("/");
        throw new Error("Sua sessão expirou. Entre novamente.");
    }
    const data = await response.json();
    accessToken = data.access;
    if (!accessToken) throw new Error("A API não retornou um access token.");
    sessionStorage.setItem("accessToken", accessToken);
    return accessToken;
}

async function api(url, options = {}, retry = true) {
    if (!accessToken) await refreshToken();
    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${accessToken}`);
    if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }
    const response = await fetch(url, {
        ...options,
        headers,
        credentials: "same-origin"
    });
    if (response.status === 401 && retry) {
        await refreshToken();
        return api(url, options, false);
    }
    return response;
}

async function readResponse(response) {
    if (response.status === 204) return null;
    const type = response.headers.get("content-type") || "";
    if (type.includes("application/json")) return response.json();
    const body = await response.text();
    return body ? { detail: body } : {};
}

function apiError(data) {
    if (!data) return "Não foi possível concluir a operação.";
    if (typeof data.detail === "string") return data.detail;
    return Object.entries(data).map(([key, value]) => {
        const msg = Array.isArray(value) ? value.join(", ") : typeof value === "string" ? value : JSON.stringify(value);
        return `${key}: ${msg}`;
    }).join(" · ") || "Verifique os dados informados.";
}

function toast(message, error = false) {
    const region = $("#toast-region");
    if (!region) return;
    const item = document.createElement("div");
    item.className = `toast${error ? " error" : ""}`;
    item.textContent = message;
    region.appendChild(item);
    window.setTimeout(() => item.remove(), 3800);
}

function showModal(id) { $(`#${id}`).classList.add("active"); }
function hideModal(id) { $(`#${id}`).classList.remove("active"); }
function initials(name) { return (name || "?").trim().charAt(0).toUpperCase(); }
function fullName(user) {
    const name = `${user.first_name || ""} ${user.last_name || ""}`.trim();
    return name || user.username || "Usuário";
}
function statusName(code) { return ({AF:"A fazer", EA:"Em andamento", CO:"Concluído"})[code] || code; }
function priorityName(code) { return ({A:"Alta", M:"Média", B:"Baixa"})[code] || code; }
function safeDate(value) {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleString("pt-BR", { dateStyle:"short", timeStyle:"short" });
}

async function loadCurrentUser() {
    const response = await api("/api/auth/me/");
    const data = await readResponse(response);
    if (!response.ok) throw new Error(apiError(data));
    currentUser = data;
    $("#user-name").textContent = currentUser.username;
    $("#user-role").textContent = ({SUPREMO:"Supremo", GERENTE:"Gerente", FUNCIONARIO:"Funcionário"})[currentUser.papel] || "Usuário";
    $("#user-avatar").textContent = initials(currentUser.username);
}

async function loadTeams() {
    const response = await api("/api/equipes/");
    const data = await readResponse(response);
    if (!response.ok) throw new Error(apiError(data));
    teams = Array.isArray(data) ? data : data.results || [];
    fillTeamSelects();
    renderTeams();
}

async function loadTasks() {
    const response = await api("/api/tarefas/");
    const data = await readResponse(response);
    if (!response.ok) throw new Error(apiError(data));
    tasks = Array.isArray(data) ? data : data.results || [];
    renderAll();
}

async function loadUsers() {
    if (!["SUPREMO", "GERENTE"].includes(currentUser.papel)) {
        users = [];
        return;
    }
    const response = await api("/api/usuarios/");
    const data = await readResponse(response);
    if (!response.ok) throw new Error(apiError(data));
    users = Array.isArray(data) ? data : data.results || [];
}

function fillTeamSelects() {
    const options = teams.map(team => `<option value="${team.id}">${escapeHtml(team.nome)}</option>`).join("");
    ["#task-team", "#filter-team", "#dashboard-team-filter"].forEach(selector => {
        const select = $(selector);
        if (!select) return;
        const first = selector === "#task-team"
            ? '<option value="">Tarefa pessoal</option>'
            : '<option value="">Todas as equipes</option>';
        const previous = select.value;
        select.innerHTML = first + options;
        if ([...select.options].some(option => option.value === previous)) select.value = previous;
    });
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
    })[char]);
}

function filteredTasks() {
    const term = ($("#task-search")?.value || "").trim().toLocaleLowerCase("pt-BR");
    const teamId = $("#filter-team")?.value || "";
    const priority = $("#filter-priority")?.value || "";
    return tasks.filter(task => {
        const textMatch = !term || [task.titulo, task.descricao, task.responsavel?.username, task.equipe_nome]
            .some(value => String(value || "").toLocaleLowerCase("pt-BR").includes(term));
        const teamMatch = !teamId || String(task.equipe || "") === teamId;
        const priorityMatch = !priority || task.urgencia === priority;
        return textMatch && teamMatch && priorityMatch;
    });
}

function createTaskCard(task) {
    const card = document.createElement("article");
    card.className = "task-card";
    card.draggable = true;
    card.dataset.id = task.id;

    const title = document.createElement("h3");
    title.textContent = task.titulo;
    const description = document.createElement("p");
    description.textContent = task.descricao || "Sem descrição.";
    const meta = document.createElement("div");
    meta.className = "task-card-meta";
    const responsible = document.createElement("span");
    responsible.className = "task-responsible";
    responsible.textContent = `◉ ${task.responsavel?.username || "Sem responsável"}`;
    const priority = document.createElement("span");
    priority.className = `priority priority-${task.urgencia}`;
    priority.textContent = priorityName(task.urgencia);
    meta.append(responsible, priority);
    card.append(title, description, meta);

    if (task.equipe_nome) {
        const team = document.createElement("div");
        team.className = "task-responsible";
        team.style.marginTop = "9px";
        team.textContent = `♧ ${task.equipe_nome}`;
        card.appendChild(team);
    }
    card.addEventListener("click", () => openTask(task));
    card.addEventListener("dragstart", event => {
        event.dataTransfer.setData("text/plain", String(task.id));
        event.dataTransfer.effectAllowed = "move";
        card.classList.add("dragging");
    });
    card.addEventListener("dragend", () => card.classList.remove("dragging"));
    return card;
}

function renderBoard(list = filteredTasks()) {
    ["AF", "EA", "CO"].forEach(status => {
        const container = $(`#tasks-${status}`);
        container.replaceChildren();
        const rows = list.filter(task => task.status === status);
        rows.forEach(task => container.appendChild(createTaskCard(task)));
        if (!rows.length) {
            const empty = document.createElement("div");
            empty.className = "empty-state";
            empty.textContent = "Nenhuma tarefa nesta coluna.";
            container.appendChild(empty);
        }
        $(`#count-${status}`).textContent = rows.length;
    });
}

function renderStats(list = tasks) {
    const total = list.length;
    const pending = list.filter(t => t.status === "AF").length;
    const progress = list.filter(t => t.status === "EA").length;
    const done = list.filter(t => t.status === "CO").length;
    $("#stat-total").textContent = total;
    $("#stat-pending").textContent = pending;
    $("#stat-progress").textContent = progress;
    $("#stat-done").textContent = done;
    $("#completion-rate").textContent = total ? `${Math.round(done / total * 100)}%` : "0%";
    $("#high-priority-count").textContent = list.filter(t => t.urgencia === "A").length;
    $("#dashboard-progress").textContent = progress;
    $("#team-total").textContent = teams.length;
}

function renderAllTasks(list = filteredTasks()) {
    const body = $("#all-tasks-body");
    body.replaceChildren();
    if (!list.length) {
        body.innerHTML = '<tr><td colspan="6"><div class="empty-state">Nenhuma tarefa encontrada.</div></td></tr>';
        return;
    }
    list.forEach(task => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><span class="table-title">${escapeHtml(task.titulo)}</span></td>
          <td>${escapeHtml(task.equipe_nome || "Pessoal")}</td>
          <td>${escapeHtml(task.responsavel?.username || "—")}</td>
          <td><span class="status-pill ${task.status}">${statusName(task.status)}</span></td>
          <td><span class="priority priority-${task.urgencia}">${priorityName(task.urgencia)}</span></td>
          <td><div class="table-actions"><button type="button" data-action="edit">Abrir</button><button type="button" data-action="history">Histórico</button></div></td>`;
        tr.querySelector('[data-action="edit"]').addEventListener("click", () => openTask(task));
        tr.querySelector('[data-action="history"]').addEventListener("click", () => openHistory(task));
        body.appendChild(tr);
    });
}

function renderDashboard() {
    const teamFilter = $("#dashboard-team-filter").value;
    const list = tasks.filter(task => !teamFilter || String(task.equipe || "") === teamFilter);
    renderStats(list);
    const body = $("#team-performance-body");
    body.replaceChildren();
    const rows = teams.filter(team => !teamFilter || String(team.id) === teamFilter).map(team => {
        const teamTasks = list.filter(task => String(task.equipe || "") === String(team.id));
        const total = teamTasks.length;
        const done = teamTasks.filter(t => t.status === "CO").length;
        return {team, total, pending:teamTasks.filter(t=>t.status==="AF").length, progress:teamTasks.filter(t=>t.status==="EA").length, done, rate:total?Math.round(done/total*100):0};
    });
    if (!rows.length) {
        body.innerHTML = '<tr><td colspan="6"><div class="empty-state">Não há equipes disponíveis.</div></td></tr>';
        return;
    }
    rows.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td><span class="table-title">${escapeHtml(row.team.nome)}</span></td><td>${row.total}</td><td>${row.pending}</td><td>${row.progress}</td><td>${row.done}</td><td>${row.rate}%</td>`;
        body.appendChild(tr);
    });
}

function renderTeams() {
    const grid = $("#team-grid");
    grid.replaceChildren();
    if (!teams.length) {
        grid.innerHTML = '<div class="empty-state">Nenhuma equipe disponível.</div>';
        return;
    }
    teams.forEach(team => {
        const card = document.createElement("article");
        card.className = "team-card";
        const manager = team.gerente?.username || "Não informado";
        const canManage = currentUser.papel === "SUPREMO" ||
            (currentUser.papel === "GERENTE" && team.gerente?.id === currentUser.id);
        card.innerHTML = `
          <h3>${escapeHtml(team.nome)}</h3>
          <p>${escapeHtml(team.descricao || "Sem descrição cadastrada.")}</p>
          <div class="team-card-meta"><span>Gerente: ${escapeHtml(manager)}</span><span>${(team.membros || []).length} membro(s)</span></div>
          <div class="team-card-actions">
            <button type="button" class="manage-members">Membros</button>
            ${canManage ? '<button type="button" class="edit-team">Editar</button><button type="button" class="delete-team">Excluir</button>' : ""}
          </div>`;
        card.querySelector(".manage-members").addEventListener("click", () => openMembers(team));
        card.querySelector(".edit-team")?.addEventListener("click", () => openTeam(team));
        card.querySelector(".delete-team")?.addEventListener("click", () => deleteTeam(team));
        grid.appendChild(card);
    });
}

function renderAll() {
    renderBoard();
    renderStats(tasks);
    renderAllTasks();
    renderDashboard();
}

function openPage(page) {
    currentPage = page;
    $$(".page-section").forEach(section => section.classList.toggle("active", section.id === `page-${page}`));
    $$(".sidebar-link").forEach(button => button.classList.toggle("active", button.dataset.page === page));
    $("#page-breadcrumb").textContent = ({board:"Meu quadro",tasks:"Todas as tarefas",teams:"Equipes",dashboard:"Desempenho"})[page];
    $("#new-task-button").classList.toggle("hidden", !["board","tasks"].includes(page));
    $("#task-search").classList.toggle("hidden", !["board","tasks"].includes(page));
    if (page === "dashboard") renderDashboard();
}

function populateResponsibleSelect(selectedId = null) {
    const teamId = $("#task-team").value;
    const select = $("#task-responsible");
    select.replaceChildren();
    const placeholder = new Option("Selecione o responsável", "");
    select.add(placeholder);

    let candidates = [];
    if (teamId) {
        const team = teams.find(item => String(item.id) === String(teamId));
        if (!team) return;
        if (currentUser.papel === "FUNCIONARIO") {
            candidates = [currentUser];
        } else {
            candidates = [team.gerente, ...(team.membros || [])].filter(Boolean);
        }
    } else if (["SUPREMO", "GERENTE"].includes(currentUser.papel)) {
        candidates = [currentUser, ...users];
    } else {
        candidates = [currentUser];
    }
    const unique = new Map(candidates.map(user => [String(user.id), user]));
    unique.forEach(user => select.add(new Option(fullName(user), user.id)));
    if (selectedId && [...select.options].some(option => option.value === String(selectedId))) {
        select.value = String(selectedId);
    } else if (unique.size === 1) {
        select.value = String([...unique.keys()][0]);
    }
}

function openTask(task = null, status = "AF") {
    editingTaskId = task?.id ?? null;
    $("#task-form").reset();
    $("#task-modal-title").textContent = task ? "Editar tarefa" : "Nova tarefa";
    $("#save-task-button").textContent = task ? "Salvar alterações" : "Criar tarefa";
    $("#delete-task-button").classList.toggle("hidden", !task);
    $("#task-title").value = task?.titulo || "";
    $("#task-description").value = task?.descricao || "";
    $("#task-status").value = task?.status || status;
    $("#task-priority").value = task?.urgencia || "M";
    $("#task-team").value = task?.equipe ? String(task.equipe) : "";
    populateResponsibleSelect(task?.responsavel?.id || currentUser.id);
    const employee = currentUser.papel === "FUNCIONARIO";
    $("#task-responsible").disabled = employee && !!task;
    $("#task-team").disabled = employee && !!task;
    $("#task-form-message").textContent = "";
    showModal("task-modal");
}

async function saveTask(event) {
    event.preventDefault();
    const message = $("#task-form-message");
    const responsibleId = $("#task-responsible").value;
    if (!responsibleId) {
        message.textContent = "Selecione um responsável.";
        return;
    }
    const payload = {
        titulo: $("#task-title").value.trim(),
        descricao: $("#task-description").value.trim(),
        status: $("#task-status").value,
        urgencia: $("#task-priority").value,
        equipe: $("#task-team").value ? Number($("#task-team").value) : null
    };
    if (!payload.titulo) {
        message.textContent = "Informe o título da tarefa.";
        return;
    }
    if (!editingTaskId || currentUser.papel !== "FUNCIONARIO") {
        payload.responsavel_id = Number(responsibleId);
    }
    const button = $("#save-task-button");
    button.disabled = true;
    message.textContent = "Salvando...";
    try {
        const response = await api(editingTaskId ? `/api/tarefas/${editingTaskId}/` : "/api/tarefas/", {
            method: editingTaskId ? "PATCH" : "POST",
            body: JSON.stringify(payload)
        });
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        hideModal("task-modal");
        await loadTasks();
        toast(editingTaskId ? "Tarefa atualizada." : "Tarefa criada.");
    } catch (error) {
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
}

async function deleteTask() {
    if (!editingTaskId || !confirm("Tem certeza de que deseja excluir esta tarefa?")) return;
    const button = $("#delete-task-button");
    button.disabled = true;
    try {
        const response = await api(`/api/tarefas/${editingTaskId}/`, {method:"DELETE"});
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        hideModal("task-modal");
        await loadTasks();
        toast("Tarefa excluída.");
    } catch (error) {
        toast(error.message, true);
    } finally {
        button.disabled = false;
    }
}

async function moveTask(taskId, status) {
    const task = tasks.find(item => String(item.id) === String(taskId));
    if (!task || task.status === status) return;
    const previous = task.status;
    task.status = status;
    renderAll();
    try {
        const response = await api(`/api/tarefas/${taskId}/`, {
            method:"PATCH", body:JSON.stringify({status})
        });
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        await loadTasks();
    } catch (error) {
        task.status = previous;
        renderAll();
        toast(error.message, true);
    }
}

async function openHistory(task) {
    $("#history-task-title").textContent = task.titulo;
    $("#history-list").innerHTML = '<div class="empty-state">Carregando histórico...</div>';
    showModal("history-modal");
    try {
        const response = await api(`/api/tarefas/${task.id}/historico/`);
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        const list = $("#history-list");
        list.replaceChildren();
        if (!data.length) {
            list.innerHTML = '<div class="empty-state">Ainda não há registros de histórico.</div>';
            return;
        }
        data.forEach(item => {
            const row = document.createElement("div");
            row.className = "history-item";
            const detailText = item.detalhes && Object.keys(item.detalhes).length
                ? Object.entries(item.detalhes).map(([key, value]) => `${key}: ${JSON.stringify(value.de)} → ${JSON.stringify(value.para)}`).join(" · ")
                : "";
            row.innerHTML = `<strong>${escapeHtml(item.acao)}</strong><p>${escapeHtml(item.autor)}${detailText ? ` — ${escapeHtml(detailText)}` : ""}</p><time>${safeDate(item.criado_em)}</time>`;
            list.appendChild(row);
        });
    } catch (error) {
        $("#history-list").textContent = error.message;
    }
}

function openTeam(team = null) {
    if (!["SUPREMO", "GERENTE"].includes(currentUser.papel)) return;
    editingTeamId = team?.id ?? null;
    $("#team-form").reset();
    $("#team-modal-title").textContent = team ? "Editar equipe" : "Nova equipe";
    $("#team-name").value = team?.nome || "";
    $("#team-description").value = team?.descricao || "";
    $("#team-form-message").textContent = "";
    const managerField = $("#team-manager-field");
    managerField.classList.toggle("hidden", currentUser.papel !== "SUPREMO");
    if (currentUser.papel === "SUPREMO") {
        const managers = users.filter(user => user.papel === "GERENTE");
        const select = $("#team-manager");
        select.replaceChildren();
        managers.forEach(user => select.add(new Option(fullName(user), user.id)));
        if (team?.gerente?.id) select.value = String(team.gerente.id);
    }
    showModal("team-modal");
}

async function saveTeam(event) {
    event.preventDefault();
    const message = $("#team-form-message");
    const payload = {
        nome: $("#team-name").value.trim(),
        descricao: $("#team-description").value.trim()
    };
    if (currentUser.papel === "SUPREMO") {
        if (!$("#team-manager").value) {
            message.textContent = "Selecione o gerente responsável.";
            return;
        }
        payload.gerente_id = Number($("#team-manager").value);
    }
    const button = $("#team-form button[type='submit']");
    button.disabled = true;
    try {
        const response = await api(editingTeamId ? `/api/equipes/${editingTeamId}/` : "/api/equipes/", {
            method: editingTeamId ? "PATCH" : "POST",
            body:JSON.stringify(payload)
        });
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        hideModal("team-modal");
        await loadTeams();
        await loadTasks();
        toast(editingTeamId ? "Equipe atualizada." : "Equipe criada.");
    } catch (error) {
        message.textContent = error.message;
    } finally {
        button.disabled = false;
    }
}

async function deleteTeam(team) {
    if (!confirm(`Excluir a equipe "${team.nome}"? Equipes com tarefas vinculadas não podem ser excluídas.`)) return;
    try {
        const response = await api(`/api/equipes/${team.id}/`, {method:"DELETE"});
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        await loadTeams();
        toast("Equipe excluída.");
    } catch (error) {
        toast(error.message, true);
    }
}

async function openMembers(team) {
    managingTeamId = team.id;
    $("#members-title").textContent = `Membros — ${team.nome}`;
    $("#members-message").textContent = "";
    $("#members-list").innerHTML = '<div class="empty-state">Carregando membros...</div>';
    $("#add-member-form").classList.toggle("hidden", !["SUPREMO","GERENTE"].includes(currentUser.papel));
    showModal("members-modal");
    try {
        const response = await api(`/api/equipes/${team.id}/membros/`);
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        renderMembers(data);
        if (["SUPREMO","GERENTE"].includes(currentUser.papel)) {
            const already = new Set(data.map(member => String(member.usuario)));
            const select = $("#member-user");
            select.replaceChildren();
            users.filter(user => user.papel === "FUNCIONARIO" && !already.has(String(user.id)))
                .forEach(user => select.add(new Option(fullName(user), user.id)));
            if (!select.options.length) select.add(new Option("Nenhum funcionário disponível", ""));
        }
    } catch (error) {
        $("#members-list").textContent = error.message;
        $("#add-member-form").classList.add("hidden");
    }
}

function renderMembers(members) {
    const list = $("#members-list");
    list.replaceChildren();
    if (!members.length) {
        list.innerHTML = '<div class="empty-state">Esta equipe ainda não possui membros.</div>';
        return;
    }
    const canManage = ["SUPREMO","GERENTE"].includes(currentUser.papel);
    members.forEach(member => {
        const row = document.createElement("div");
        row.className = "member-row";
        row.innerHTML = `<strong>${escapeHtml(member.usuario_nome)}</strong>
          <label><input type="checkbox" data-perm="pode_criar_tarefa" ${member.pode_criar_tarefa?"checked":""} ${canManage?"":"disabled"}> Criar</label>
          <label><input type="checkbox" data-perm="pode_editar_tarefa" ${member.pode_editar_tarefa?"checked":""} ${canManage?"":"disabled"}> Editar</label>
          <label><input type="checkbox" data-perm="pode_excluir_tarefa" ${member.pode_excluir_tarefa?"checked":""} ${canManage?"":"disabled"}> Excluir</label>
          ${canManage?'<button type="button" class="remove-member">Remover</button>':""}`;
        if (canManage) {
            row.querySelectorAll("input[data-perm]").forEach(input => input.addEventListener("change", () => updateMember(member.id, row)));
            row.querySelector(".remove-member").addEventListener("click", () => removeMember(member.id, member.usuario_nome));
        }
        list.appendChild(row);
    });
}

async function updateMember(memberId, row) {
    const payload = {};
    row.querySelectorAll("input[data-perm]").forEach(input => payload[input.dataset.perm] = input.checked);
    try {
        const response = await api(`/api/equipes/${managingTeamId}/membros/${memberId}/`, {
            method:"PATCH", body:JSON.stringify(payload)
        });
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        toast("Permissões atualizadas.");
    } catch (error) {
        toast(error.message, true);
        openMembers(teams.find(team => team.id === managingTeamId));
    }
}

async function removeMember(memberId, username) {
    if (!confirm(`Remover ${username} desta equipe?`)) return;
    try {
        const response = await api(`/api/equipes/${managingTeamId}/membros/${memberId}/`, {method:"DELETE"});
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        await loadTeams();
        await openMembers(teams.find(team => team.id === managingTeamId));
        toast("Membro removido.");
    } catch (error) {
        toast(error.message, true);
    }
}

async function addMember(event) {
    event.preventDefault();
    const userId = $("#member-user").value;
    if (!userId) {
        $("#members-message").textContent = "Não há funcionário disponível para adicionar.";
        return;
    }
    try {
        const response = await api(`/api/equipes/${managingTeamId}/membros/`, {
            method:"POST",
            body:JSON.stringify({
                usuario:Number(userId),
                pode_criar_tarefa:false,
                pode_editar_tarefa:false,
                pode_excluir_tarefa:false
            })
        });
        const data = await readResponse(response);
        if (!response.ok) throw new Error(apiError(data));
        await loadTeams();
        await openMembers(teams.find(team => team.id === managingTeamId));
        toast("Membro adicionado.");
    } catch (error) {
        $("#members-message").textContent = error.message;
    }
}

async function logout() {
    try {
        const csrf = await csrfToken();
        await fetch("/api/auth/logout/", {
            method:"POST", credentials:"same-origin",
            headers:{"X-CSRFToken":csrf}
        });
    } catch (error) {
        console.warn("Falha ao encerrar refresh token:", error);
    } finally {
        sessionStorage.removeItem("accessToken");
        accessToken = null;
        window.location.replace("/");
    }
}

function configureEvents() {
    $$(".sidebar-link").forEach(button => button.addEventListener("click", () => openPage(button.dataset.page)));
    $("#logout-button").addEventListener("click", logout);
    $("#new-task-button").addEventListener("click", () => openTask());
    $("#new-task-button-alt").addEventListener("click", () => openTask());
    $$(".add-task-column").forEach(button => button.addEventListener("click", () => openTask(null, button.dataset.status)));
    $("#task-form").addEventListener("submit", saveTask);
    $("#delete-task-button").addEventListener("click", deleteTask);
    $("#task-team").addEventListener("change", () => populateResponsibleSelect());
    $("#task-search").addEventListener("input", () => { renderBoard(); renderAllTasks(); });
    $("#filter-team").addEventListener("change", renderBoard);
    $("#filter-priority").addEventListener("change", renderBoard);
    $("#dashboard-team-filter").addEventListener("change", renderDashboard);
    $("#new-team-button").addEventListener("click", () => openTeam());
    $("#team-form").addEventListener("submit", saveTeam);
    $("#add-member-form").addEventListener("submit", addMember);
    $$("[data-close]").forEach(button => button.addEventListener("click", () => hideModal(button.dataset.close)));
    $$(".modal-overlay").forEach(overlay => overlay.addEventListener("click", event => {
        if (event.target === overlay) overlay.classList.remove("active");
    }));
    $$(".kanban-column").forEach(column => {
        column.addEventListener("dragover", event => event.preventDefault());
        column.addEventListener("drop", event => {
            event.preventDefault();
            const taskId = event.dataTransfer.getData("text/plain");
            if (taskId) moveTask(taskId, column.dataset.status);
        });
    });
    $("#today-label").textContent = new Date().toLocaleDateString("pt-BR", {weekday:"long", day:"numeric", month:"long", year:"numeric"});
}

async function initApp() {
    try {
        configureEvents();
        await loadCurrentUser();
        await loadUsers();
        await loadTeams();
        await loadTasks();
        if (currentUser.papel === "FUNCIONARIO") {
            $("#new-team-button").classList.add("hidden");
        }
        openPage("board");
    } catch (error) {
        console.error(error);
        toast(error.message || "Não foi possível carregar o NexTask.", true);
        if (!accessToken) window.location.replace("/");
    }
}

document.addEventListener("DOMContentLoaded", initApp);
