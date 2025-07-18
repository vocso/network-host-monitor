let hosts = [];
let editingId = null;

// Load token from localStorage
let authToken = localStorage.getItem('auth_token');

// Dynamic auth header
const AUTH_HEADER = () => ({
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`
  }
});

const authenticate = () => {
  const input = document.getElementById("tokenInput").value.trim();
  fetch("/data.json", {
    headers: { 'Authorization': `Bearer ${input}` }
  })
    .then(res => {
      if (!res.ok) throw new Error("Unauthorized");
      return res.json();
    })
    .then(data => {
      authToken = input;
      localStorage.setItem('auth_token', authToken);
      document.getElementById("login").style.display = "none";
      document.getElementById("app").style.display = "block";
      hosts = data.hosts;
      renderHosts();
      loadTheme();
      setInterval(fetchAndRenderHosts, 10000);
    })
    .catch(() => {
      document.getElementById("loginError").style.display = "block";
    });
};

const loadTheme = () => {
  const mode = localStorage.getItem('theme') || 'dark';
  document.body.classList.toggle('light', mode === 'light');
};

const toggleTheme = () => {
  const isLight = document.body.classList.toggle('light');
  localStorage.setItem('theme', isLight ? 'light' : 'dark');
  document.getElementById("modeToggle").textContent = isLight ? '🌙' : '☀️';
};

const showForm = (id = null) => {
  editingId = id;
  const host = hosts.find(h => h.id === id);
  document.getElementById("name").value = host?.name || "";
  document.getElementById("ip").value = host?.ip || "";
  document.getElementById("hostForm").style.display = "block";
};

const hideForm = () => {
  document.getElementById("hostForm").style.display = "none";
  editingId = null;
};

const isValidIP = (ip) => {
  return /^(25[0-5]|2[0-4]\d|1?\d\d?|0)(\.(25[0-5]|2[0-4]\d|1?\d\d?|0)){3}$/.test(ip);
};

const saveHost = () => {
  const name = document.getElementById("name").value.trim();
  const ip = document.getElementById("ip").value.trim();

  if (!isValidIP(ip)) {
    alert("Invalid IP address.");
    return;
  }

  if (editingId) {
    const host = hosts.find(h => h.id === editingId);
    host.name = name;
    host.ip = ip;
  } else {
    hosts.push({
      id: Date.now(),
      name,
      ip,
      statusCurrent: 0,
      statusHistory: []
    });
  }

  saveToServer();
  hideForm();
};

const saveToServer = () => {
  fetch("/save", {
    method: "POST",
    ...AUTH_HEADER,
    body: JSON.stringify({ hosts })
  }).then(() => renderHosts());
};

const deleteHost = (id) => {
  hosts = hosts.filter(h => h.id !== id);
  saveToServer();
};

const renderHosts = () => {
  const grid = document.getElementById("hostGrid");
  const query = document.getElementById("search").value.toLowerCase();
  grid.innerHTML = "";

  if (!hosts || hosts.length === 0) {
    const msg = document.createElement("div");
    msg.className = "no-hosts-message";
    msg.textContent = "No hosts added yet.";
    grid.appendChild(msg);
    return;
  }

  const filteredHosts = hosts
    .filter(h => h.name.toLowerCase().includes(query))
    .sort((a, b) => b.id - a.id);

  updateStats();

  if (filteredHosts.length === 0) {
    const msg = document.createElement("div");
    msg.className = "no-hosts-message";
    msg.textContent = "No matching results found.";
    grid.appendChild(msg);
    return;
  }

  filteredHosts.forEach(host => {
    const uptime = host.statusHistory.length
      ? Math.round((host.statusHistory.filter(v => v === 1).length / host.statusHistory.length) * 100)
      : 0;

    const card = document.createElement("div");
    card.className = "host-card";
    card.innerHTML = `
      <div class="host-header">
        <div class="host-info">
          <div class="host-name">${host.name}</div>
          <div class="host-ip">${host.ip}</div>
          <div class="status-line">
            ${host.statusHistory.map(s => `<div class="dot ${s ? 'up' : 'down'}"></div>`).join("")}
          </div>
        </div>
        <div class="host-meta">
          <div class="status ${host.statusCurrent ? 'up-status' : 'down-status'}"></div>
          <div class="uptime">${uptime}% uptime</div>
          <div class="context-menu-btn" onclick="toggleMenu(event, ${host.id})">⋮</div>
          <div id="menu-${host.id}" class="context-menu">
            <button onclick="showForm(${host.id})">Edit</button>
            <button onclick="deleteHost(${host.id})">Delete</button>
          </div>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
};

const toggleMenu = (event, id) => {
  event.stopPropagation();
  document.querySelectorAll(".context-menu").forEach(m => m.style.display = "none");
  const menu = document.getElementById(`menu-${id}`);
  if (menu) menu.style.display = "flex";
};

window.addEventListener("click", () => {
  document.querySelectorAll(".context-menu").forEach(m => m.style.display = "none");
});

const fetchAndRenderHosts = () => {
  fetch("/data.json", AUTH_HEADER)
    .then(res => res.json())
    .then(data => {
      hosts = data.hosts;
      renderHosts();
    });
};

const refreshHosts = () => {
  fetch("/data.json", AUTH_HEADER)
    .then(res => res.json())
    .then(data => {
      hosts = data.hosts;
      renderHosts();
    });
};

const updateStats = () => {
  const total = hosts.length;
  const up = hosts.filter(h => h.statusCurrent).length;
  const down = total - up;

  document.getElementById("hostStats").innerHTML = `
    <div class="stat"><div class="stat-label">Total</div>${total}</div>
    <div class="stat"><div class="stat-label">Online</div>${up}</div>
    <div class="stat"><div class="stat-label">Down</div>${down}</div>
  `;
};

loadTheme();
fetchAndRenderHosts();
setInterval(fetchAndRenderHosts, 10000); // every 10 seconds
