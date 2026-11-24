(function () {
    function csrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) return meta.content;
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    async function api(url, options) {
        const opts = options || {};
        const headers = Object.assign(
            { "X-CSRFToken": csrfToken(), Accept: "application/json" },
            opts.headers || {}
        );
        if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
            headers["Content-Type"] = "application/json";
            opts.body = JSON.stringify(opts.body);
        }
        const res = await fetch(url, Object.assign({ credentials: "same-origin" }, opts, { headers }));
        let data = {};
        try {
            data = await res.json();
        } catch (e) {}
        return { ok: res.ok && data.ok !== false, status: res.status, data };
    }

    function applyApiProfile(profile) {
        if (!profile) return;
        applyRegisteredProfile(
            profile.firstName || "",
            profile.lastName || "",
            profile.username || "",
            profile.email || "",
            profile.playerId,
            profile.stats || { wins: 0, losses: 0, matches: 0, playSeconds: 0 },
            ""
        );
    }

    const originalSubmitLogin = window.submitLogin;
    const originalSubmitRegistration = window.submitRegistration;
    const originalLogoutAccount = window.logoutAccount;
    const originalSearchPlayerProfile = window.searchPlayerProfile;
    const originalRecordMatchOutcome = window.recordMatchOutcome;
    const originalCreatePvpRoom = window.createPvpRoom;
    const originalJoinPvpRoomById = window.joinPvpRoomById;
    const originalCancelPvpWait = window.cancelPvpWait;
    const originalSyncPvpStateToCloud = window.syncPvpStateToCloud;

    window.submitLogin = async function () {
        const rawId = document.getElementById("loginIdentifierInput").value.trim();
        const password = document.getElementById("loginPasswordInput").value;
        const errEl = document.getElementById("loginErrorText");
        errEl.classList.add("hidden");
        if (!rawId || !password) {
            errEl.innerText = "Введите Email / Username / ID и пароль.";
            errEl.classList.remove("hidden");
            return;
        }
        const result = await api("/api/login/", { method: "POST", body: { identifier: rawId, password } });
        if (!result.ok) {
            if (originalSubmitLogin) return originalSubmitLogin();
            errEl.innerText = (result.data && result.data.error) || "Не удалось войти.";
            errEl.classList.remove("hidden");
            return;
        }
        applyApiProfile(result.data.profile);
        closeAuthModal();
        showToast("С возвращением, " + state.userProfile.fullName + "!");
    };

    window.submitRegistration = async function () {
        const firstName = document.getElementById("regFirstNameInput").value.trim();
        const lastName = document.getElementById("regLastNameInput").value.trim();
        const rawUser = document.getElementById("regUsernameInput").value.trim();
        const email = document.getElementById("regEmailInput").value.trim();
        const password = document.getElementById("regPasswordInput").value;
        const errEl = document.getElementById("regErrorText");
        const result = await api("/api/register/", {
            method: "POST",
            body: { firstName, lastName, username: rawUser, email, password },
        });
        if (!result.ok) {
            errEl.innerText = (result.data && result.data.error) || "Не удалось зарегистрироваться.";
            errEl.classList.remove("hidden");
            return;
        }
        applyApiProfile(result.data.profile);
        closeAuthModal();
        showToast("Аккаунт создан! Ваш игровой ID: " + result.data.profile.playerId);
    };

    window.logoutAccount = async function () {
        await api("/api/logout/", { method: "POST", body: {} });
        if (originalLogoutAccount) originalLogoutAccount();
    };

    window.searchPlayerProfile = async function () {
        const raw = document.getElementById("profileSearchInput").value.trim();
        const errEl = document.getElementById("profileSearchError");
        errEl.classList.add("hidden");
        if (!raw) {
            errEl.innerText = "Введите ID (например, CV-482910) или Username игрока.";
            errEl.classList.remove("hidden");
            return;
        }
        const result = await api("/api/players/search/?q=" + encodeURIComponent(raw), { method: "GET" });
        if (result.ok && result.data.profile) {
            const logoutBar = document.getElementById("profLogoutBar");
            if (result.data.isOwn) {
                viewMyProfile();
            } else {
                document.getElementById("profNotRegisteredHint").classList.add("hidden");
                if (logoutBar) logoutBar.classList.add("hidden");
                renderProfileCard(result.data.profile, false);
            }
            return;
        }
        if (originalSearchPlayerProfile) return originalSearchPlayerProfile();
        errEl.innerText = (result.data && result.data.error) || "Игрок не найден.";
        errEl.classList.remove("hidden");
    };

    window.recordMatchOutcome = async function (didWin) {
        if (originalRecordMatchOutcome) await originalRecordMatchOutcome(didWin);
        if (!state.userProfile) return;
        const elapsedSec = state.matchStartTime
            ? Math.max(10, Math.round((Date.now() - state.matchStartTime) / 1000))
            : 60;
        const result = await api("/api/stats/", { method: "POST", body: { didWin: !!didWin, elapsedSec } });
        if (result.ok && result.data.profile) applyApiProfile(result.data.profile);
    };

    function stopPvpPoll() {
        if (state.pvpPollTimer) {
            clearInterval(state.pvpPollTimer);
            state.pvpPollTimer = null;
        }
    }

    async function pollPvpRoom() {
        if (!state.pvpRoomId) return;
        const result = await api("/api/pvp/room/" + encodeURIComponent(state.pvpRoomId) + "/", { method: "GET" });
        if (!result.ok || !result.data.room) return;
        const data = result.data.room;
        if (data.status === "active" && data.guest && !data.gameState) {
            const isHost = state.userProfile && data.host && data.host.playerId === state.userProfile.playerId;
            if (isHost && !state.pvpHostStarted) {
                state.pvpHostStarted = true;
                document.getElementById("pvpWaitingBox").classList.add("hidden");
                startPvpHostMatch(data.host, data.guest);
            }
        } else if (data.gameState && data.actionId > state.pvpLastActionId) {
            state.pvpLastActionId = data.actionId;
            applySyncedPvpState(data.gameState);
        }
    }

    function startPvpPoll() {
        stopPvpPoll();
        state.pvpPollTimer = setInterval(pollPvpRoom, 900);
        pollPvpRoom();
    }

    window.createPvpRoom = async function () {
        if (!state.userProfile) {
            showToast("Сначала войдите в аккаунт.");
            return;
        }
        const result = await api("/api/pvp/create/", { method: "POST", body: { gameType: state.selectedGame } });
        if (!result.ok) {
            if (originalCreatePvpRoom) return originalCreatePvpRoom();
            showToast((result.data && result.data.error) || "Не удалось создать стол.");
            return;
        }
        state.pvpRoomId = result.data.room.roomId;
        state.pvpHostId = result.data.room.roomId;
        state.pvpHostStarted = false;
        document.getElementById("pvpWaitingBox").classList.remove("hidden");
        document.getElementById("pvpWaitingText").innerText =
            "Ожидание друга по вашему ID (" + state.pvpRoomId + ")...";
        startPvpPoll();
    };

    window.joinPvpRoomById = async function () {
        if (!state.userProfile) return;
        const rawInput = document.getElementById("friendIdInput").value.trim().toUpperCase();
        const targetId = rawInput.startsWith("CV-") ? rawInput : "CV-" + rawInput;
        if (targetId.length < 6) {
            showToast("Введите корректный ID друга!");
            return;
        }
        const result = await api("/api/pvp/join/", { method: "POST", body: { roomId: targetId } });
        if (!result.ok) {
            if (originalJoinPvpRoomById) return originalJoinPvpRoomById();
            showToast((result.data && result.data.error) || "Комната не найдена.");
            return;
        }
        state.selectedGame = result.data.room.gameType;
        state.pvpRoomId = result.data.room.roomId;
        state.pvpHostId = result.data.room.roomId;
        document.getElementById("pvpWaitingBox").classList.remove("hidden");
        document.getElementById("pvpWaitingText").innerText = "Подключение к столу друга...";
        startPvpPoll();
    };

    window.cancelPvpWait = function () {
        stopPvpPoll();
        if (state.pvpRoomId) api("/api/pvp/cancel/", { method: "POST", body: {} });
        if (originalCancelPvpWait) originalCancelPvpWait();
    };

    window.syncPvpStateToCloud = async function () {
        if (state.matchMode !== "pvp" || !state.pvpRoomId) {
            if (originalSyncPvpStateToCloud) return originalSyncPvpStateToCloud();
            return;
        }
        state.pvpLastActionId += 1;
        const payload = {
            players: state.players,
            deck: state.deck,
            discardPile: state.discardPile,
            currentTurnIdx: state.currentTurnIdx,
            direction: state.direction,
            activeColor: state.activeColor,
            stackedPenalty: state.stackedPenalty,
            flipSide: state.flipSide,
            gameOver: state.gameOver,
            durakTrumpSuit: state.durakTrumpSuit,
            durakTrumpCard: state.durakTrumpCard,
            durakPairs: state.durakPairs,
            durakAttackerIdx: state.durakAttackerIdx,
            durakDefenderIdx: state.durakDefenderIdx,
            winnerIdx: state.winnerIdx,
            selectedGame: state.selectedGame,
        };
        await api("/api/pvp/sync/", {
            method: "POST",
            body: {
                roomId: state.pvpRoomId,
                actionId: state.pvpLastActionId,
                gameState: JSON.stringify(payload),
            },
        });
    };

    document.addEventListener("DOMContentLoaded", async function () {
        if (typeof initCloudServices === "function") {
            await initCloudServices();
        }
        const me = await api("/api/me/", { method: "GET" });
        if (me.ok && me.data.profile) applyApiProfile(me.data.profile);
    });
})();
