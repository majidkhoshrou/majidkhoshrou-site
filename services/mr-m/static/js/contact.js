(() => {
  const form = document.getElementById("contactForm");
  const statusEl = document.getElementById("status");
  if (!form || !statusEl) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    statusEl.textContent = "Sending…";

    const fd = new FormData(form);
    const payload = {
      name: (fd.get("name") || "").trim(),
      email: (fd.get("email") || "").trim(),
      message: (fd.get("message") || "").trim(),

      // Backend expects `company` for the honeypot (historical),
      // so map your hidden hp_field to that key:
      company: (fd.get("hp_field") || "").trim(),

      // Pass the human-timing trap too:
      submitted_at: fd.get("form_started") || ""
    };

    if (!payload.name || !payload.email || !payload.message) {
      statusEl.textContent = "❌ Please fill in all required fields.";
      return;
    }

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok && data.status === "sent") {
        statusEl.textContent = "✅ Thanks! Your message has been sent.";
        form.reset();
      } else {
        statusEl.textContent = `❌ ${data.error || "Sorry, something went wrong."}`;
      }
    } catch {
      statusEl.textContent = "❌ Network error. Please try again.";
    }
  });
})();
