document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginForm = document.getElementById("login-form");
  const logoutButton = document.getElementById("logout-button");
  const accountCreateForm = document.getElementById("account-create-form");
  const accountStatus = document.getElementById("account-status");
  const accountMessage = document.getElementById("account-message");
  const signupContainer = document.getElementById("signup-container");
  let currentAccount = null;

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character]);
  }

  function showMessage(element, text, type) {
    element.textContent = text;
    element.className = `message ${type}`;
    setTimeout(() => element.classList.add("hidden"), 5000);
  }

  async function refreshAccount() {
    const response = await fetch("/auth/me");
    const result = await response.json();
    currentAccount = result.authenticated ? result : null;
    loginForm.classList.toggle("hidden", currentAccount !== null);
    logoutButton.classList.toggle("hidden", currentAccount === null);
    accountStatus.classList.toggle("hidden", currentAccount === null);
    accountCreateForm.classList.toggle("hidden", currentAccount?.role !== "admin");
    signupContainer.classList.toggle("hidden", currentAccount?.role !== "student");
    if (currentAccount) {
      accountStatus.textContent = `${currentAccount.email} (${currentAccount.role})`;
    }
    await fetchActivities();
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Unable to load activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft = details.max_participants - details.participant_count;

        // Create participants HTML with delete icons instead of bullet points
        const participants = details.participants || [];
        const participantsHTML =
          participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${escapeHtml(email)}</span><button class="delete-btn" data-activity="${escapeHtml(name)}" data-email="${escapeHtml(email)}" aria-label="Remove ${escapeHtml(email)}">Remove</button></li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : currentAccount?.role === "staff" || currentAccount?.role === "admin"
              ? `<p><em>No participants yet</em></p>`
              : "";

        activityCard.innerHTML = `
          <h4>${escapeHtml(name)}</h4>
          <p>${escapeHtml(details.description)}</p>
          <p><strong>Schedule:</strong> ${escapeHtml(details.schedule)}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          ${details.is_registered ? "<p class='registered-status'>You are signed up</p>" : ""}
          ${details.is_registered ? `<button class="delete-btn" data-activity="${escapeHtml(name)}" aria-label="Cancel your signup for ${escapeHtml(name)}">Cancel signup</button>` : ""}
          <div class="participants-container">
            ${details.participant_count} registered
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");
    const emailQuery = email ? `?email=${encodeURIComponent(email)}` : "";

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister${emailQuery}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage(messageDiv, "Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(`/activities/${encodeURIComponent(activity)}/signup`, {
        method: "POST",
      });

      const result = await response.json();

      if (response.ok) {
        showMessage(messageDiv, result.message, "success");
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(messageDiv, result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage(messageDiv, "Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: document.getElementById("login-email").value,
          password: document.getElementById("login-password").value,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Sign in failed");
      loginForm.reset();
      showMessage(accountMessage, `Signed in as ${result.role}`, "success");
      await refreshAccount();
    } catch (error) {
      showMessage(accountMessage, error.message, "error");
    }
  });

  logoutButton.addEventListener("click", async () => {
    await fetch("/auth/logout", { method: "POST" });
    await refreshAccount();
  });

  accountCreateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/admin/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: document.getElementById("new-email").value,
          password: document.getElementById("new-password").value,
          role: document.getElementById("new-role").value,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Account creation failed");
      accountCreateForm.reset();
      showMessage(accountMessage, `Created ${result.role} account for ${result.email}`, "success");
    } catch (error) {
      showMessage(accountMessage, error.message, "error");
    }
  });

  // Initialize app
  refreshAccount().catch((error) => {
    console.error("Error loading account:", error);
    fetchActivities();
  });
});
