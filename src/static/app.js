document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const signupContainer = document.getElementById("signup-container");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const loginError = document.getElementById("login-error");
  const actionHeaders = { "X-Teacher-Action": "1" };
  let isTeacher = false;

  function setTeacherMode(authenticated) {
    isTeacher = authenticated;
    signupContainer.hidden = !authenticated;
    loginButton.hidden = authenticated;
    logoutButton.hidden = !authenticated;
    if (!authenticated) {
      signupForm.reset();
      activitiesList.querySelectorAll(".delete-btn").forEach((button) => button.remove());
    }
  }

  loginButton.addEventListener("click", () => {
    loginError.textContent = "";
    loginDialog.showModal();
  });
  document.getElementById("cancel-login").addEventListener("click", () => loginDialog.close());
  loginDialog.addEventListener("close", () => loginForm.reset());

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = loginForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    loginError.textContent = "";
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { ...actionHeaders, "Content-Type": "application/json" },
        body: JSON.stringify({
          username: document.getElementById("username").value,
          password: document.getElementById("password").value,
        }),
      });
      if (!response.ok) {
        loginError.textContent = response.status === 401
          ? "Invalid username or password."
          : "Teacher login is unavailable. Please try again later.";
        return;
      }
      setTeacherMode(true);
      loginDialog.close();
      await fetchActivities();
    } catch (error) {
      loginError.textContent = "Could not log in. Please try again.";
      console.error("Error logging in:", error);
    } finally {
      submit.disabled = false;
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST", headers: actionHeaders });
      if (!response.ok) throw new Error(`Unexpected logout status: ${response.status}`);
      setTeacherMode(false);
      messageDiv.classList.add("hidden");
      loginButton.focus();
    } catch (error) {
      messageDiv.textContent = "Could not log out. Please try again.";
      messageDiv.className = "message error";
      console.error("Error logging out:", error);
    }
  });

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error(`Unexpected activities status: ${response.status}`);
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.options.length = 1;

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        activityCard.innerHTML = `
          <h4></h4>
          <p class="activity-description"></p>
          <p><strong>Schedule:</strong> <span class="activity-schedule"></span></p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container"></div>
        `;
        activityCard.querySelector("h4").textContent = name;
        activityCard.querySelector(".activity-description").textContent = details.description;
        activityCard.querySelector(".activity-schedule").textContent = details.schedule;
        const participants = activityCard.querySelector(".participants-container");
        participants.innerHTML = details.participants.length
          ? '<div class="participants-section"><h5>Participants:</h5><ul class="participants-list"></ul></div>'
          : "<p><em>No participants yet</em></p>";
        const list = participants.querySelector("ul");
        details.participants.forEach((email) => {
          const item = document.createElement("li");
          const label = document.createElement("span");
          label.className = "participant-email";
          label.textContent = email;
          item.appendChild(label);
          if (isTeacher) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "delete-btn";
            button.textContent = "\u274c";
            button.setAttribute("aria-label", `Unregister ${email} from ${name}`);
            button.addEventListener("click", () => handleUnregister(name, email));
            item.appendChild(button);
          }
          list.appendChild(item);
        });

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(activity, email) {
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: actionHeaders,
        }
      );

      const result = await response.json();
      if (response.status === 401) setTeacherMode(false);

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: actionHeaders,
        }
      );

      const result = await response.json();
      if (response.status === 401) setTeacherMode(false);

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  async function initialize() {
    try {
      const response = await fetch("/auth/session");
      if (!response.ok && response.status !== 401) {
        throw new Error(`Unexpected session status: ${response.status}`);
      }
      setTeacherMode(response.ok);
    } catch (error) {
      messageDiv.textContent = "Could not check the teacher session.";
      messageDiv.className = "message error";
      console.error("Error checking the teacher session:", error);
    }
    await fetchActivities();
  }
  initialize();
});
