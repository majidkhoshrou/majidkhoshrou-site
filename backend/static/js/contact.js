(() => {
  const form = document.getElementById("contactForm");
  const statusEl = document.getElementById("status");
  if (!form) return;

  async function submitForm(event) {
    event.preventDefault();
    if (!statusEl) return;

    statusEl.textContent = "Sending…";

    const payload = {
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      message: form.message.value.trim(),
      company: form.company.value.trim(), // honeypot
    };

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
    } catch (err) {
      statusEl.textContent = "❌ Network error. Please try again.";
    }
  }

  form.addEventListener("submit", submitForm);
})();
