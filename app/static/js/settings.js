// Settings Page Functionality
document.addEventListener("DOMContentLoaded", loadIntegrations);

window.ecommerceConfigs = {};

async function loadIntegrations() {
  try {
    const response = await fetch("/api/integrations");
    const data = await response.json();

    let hasEcommerce = false;
    let firstEcommerceProvider = "";

    data.integrations.forEach((integration) => {
      if (integration.provider === "meta_whatsapp") {
        populateWhatsAppForm(integration.config);
        updateStatus("whatsapp", true);
      } else if (
        ["shopify", "woocommerce", "custom_api"].includes(integration.provider)
      ) {
        window.ecommerceConfigs[integration.provider] = integration.config;
        hasEcommerce = true;
        if (!firstEcommerceProvider) firstEcommerceProvider = integration.provider;
        updateStatus("ecommerce", true); // overall status
      }
    });

    if (hasEcommerce) {
      document.getElementById("ecommercePlatformSelector").value = firstEcommerceProvider;
      changeEcommercePlatform();
    }
  } catch (error) {
    console.error("Failed to load integrations:", error);
  }
}

function populateWhatsAppForm(config) {
  document.getElementById("whatsappPhone").value = config.phone_number_id || "";
  document.getElementById("whatsappApiKey").value = config.access_token || "";
  document.getElementById("whatsappBusiness").value =
    config.business_name || "";
  document.getElementById("deleteWhatsapp").style.display = "inline-flex";
}

function changeEcommercePlatform() {
  const provider = document.getElementById("ecommercePlatformSelector").value;
  const form = document.getElementById("ecommerceForm");
  const icon = document.getElementById("ecommerceIcon");
  
  if (!provider) {
    form.style.display = "none";
    icon.innerHTML = "🛒";
    return;
  }
  
  form.style.display = "block";
  
  // Reset form before populating
  form.reset();
  
  const clientIdGroup = document.getElementById("clientIdGroup");
  const clientSecretGroup = document.getElementById("clientSecretGroup");
  const accessTokenGroup = document.getElementById("accessTokenGroup");
  const clientIdLabel = document.getElementById("clientIdLabel");
  const clientSecretLabel = document.getElementById("clientSecretLabel");
  const accessTokenLabel = document.getElementById("accessTokenLabel");
  const storeUrlLabel = document.getElementById("storeUrlLabel");

  if (provider === "shopify") {
    icon.innerHTML = "🛍️";
    clientIdGroup.style.display = "block";
    clientSecretGroup.style.display = "block";
    accessTokenGroup.style.display = "block";
    clientIdLabel.innerText = "Client ID";
    clientSecretLabel.innerText = "Client Secret";
    accessTokenLabel.innerText = "Access Token";
    storeUrlLabel.innerText = "Store URL";
  } else if (provider === "woocommerce") {
    icon.innerHTML = "🛒";
    clientIdGroup.style.display = "block";
    clientSecretGroup.style.display = "block";
    accessTokenGroup.style.display = "none";
    clientIdLabel.innerText = "Consumer Key";
    clientSecretLabel.innerText = "Consumer Secret";
    storeUrlLabel.innerText = "Store URL";
  } else if (provider === "custom_api") {
    icon.innerHTML = "🔗";
    clientIdGroup.style.display = "none";
    clientSecretGroup.style.display = "block";
    accessTokenGroup.style.display = "block";
    accessTokenLabel.innerText = "API Key (Optional)";
    clientSecretLabel.innerText = "Headers / Secret (Optional)";
    storeUrlLabel.innerText = "API Endpoint";
  }
  
  // Populate if configured
  if (window.ecommerceConfigs && window.ecommerceConfigs[provider]) {
    const config = window.ecommerceConfigs[provider];
    document.getElementById("storeUrl").value = config.store_url || "";
    document.getElementById("storeClientId").value = config.client_id || "";
    document.getElementById("storeClientSecret").value = config.client_secret || "";
    document.getElementById("storeAccessToken").value = config.access_token || "";
    document.getElementById("storeWebhook").value = config.webhook_url || "";
    document.getElementById("storeName").value = config.store_name || "";
    document.getElementById("deleteEcommerce").style.display = "inline-flex";
  } else {
    document.getElementById("deleteEcommerce").style.display = "none";
  }
}

function updateStatus(type, configured) {
  const statusEl = document.getElementById(`${type}Status`);
  if (configured) {
    statusEl.innerHTML =
      '<span class="status-badge configured">✓ Configured</span>';
  } else {
    statusEl.innerHTML =
      '<span class="status-badge not-configured">Not Configured</span>';
  }
}

async function saveWhatsApp(event) {
  event.preventDefault();

  const formData = {
    phone_number_id: document.getElementById("whatsappPhone").value,
    access_token: document.getElementById("whatsappApiKey").value,
    business_name: document.getElementById("whatsappBusiness").value,
  };

  try {
    const response = await fetch("/api/integrations/meta_whatsapp", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });

    const data = await response.json();

    if (response.ok) {
      showToast("WhatsApp settings saved successfully!", "success");
      updateStatus("whatsapp", true);
      document.getElementById("deleteWhatsapp").style.display = "inline-flex";
    } else {
      showToast(data.error || "Failed to save settings", "error");
    }
  } catch (error) {
    showToast("An error occurred", "error");
  }
}

async function saveEcommerce(event) {
  event.preventDefault();

  const provider = document.getElementById("ecommercePlatformSelector").value;
  if (!provider) {
    showToast("Please select a store platform", "error");
    return;
  }

  const formData = {
    store_url: document.getElementById("storeUrl").value,
    client_id: document.getElementById("storeClientId").value,
    client_secret: document.getElementById("storeClientSecret").value,
    access_token: document.getElementById("storeAccessToken").value,
    webhook_url: document.getElementById("storeWebhook").value,
    store_name: document.getElementById("storeName").value,
  };

  let displayName = provider === "shopify" ? "Shopify" : provider === "woocommerce" ? "WooCommerce" : "Custom API";
  await submitIntegration(provider, formData, displayName);
}

async function submitIntegration(provider, formData, displayName) {
  try {
    const response = await fetch(`/api/integrations/${provider}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });

    const data = await response.json();

    if (response.ok) {
      showToast(`${displayName} settings saved successfully!`, "success");
      updateStatus(provider === "meta_whatsapp" ? "whatsapp" : "ecommerce", true);
      if (provider !== "meta_whatsapp") {
        window.ecommerceConfigs[provider] = formData;
        document.getElementById("deleteEcommerce").style.display = "inline-flex";
      } else {
        document.getElementById("deleteWhatsapp").style.display = "inline-flex";
      }
    } else {
      showToast(data.error || "Failed to save settings", "error");
    }
  } catch (error) {
    showToast("An error occurred", "error");
  }
}

async function deleteEcommerceIntegration() {
  const provider = document.getElementById("ecommercePlatformSelector").value;
  if (!provider) return;
  await deleteIntegration(provider, "ecommerce");
}

async function deleteIntegration(provider, groupType) {

  if (provider === "whatsapp") {
    provider = "meta_whatsapp";
    groupType = "whatsapp";
  }

  if (!provider) {
    showToast("No integration selected to delete", "error");
    return;
  }

  if (!confirm(`Are you sure you want to remove the ${provider} integration?`)) {
    return;
  }

  try {
    const response = await fetch(`/api/integrations/${provider}`, {
      method: "DELETE",
    });

    if (response.ok) {
      showToast(
        `${groupType.charAt(0).toUpperCase() + groupType.slice(1)} integration removed`,
        "success",
      );
      updateStatus(groupType, false);

      // Clear form
      if (groupType === "whatsapp") {
        document.getElementById("whatsappForm").reset();
        document.getElementById("deleteWhatsapp").style.display = "none";
      } else if (groupType === "ecommerce") {
        delete window.ecommerceConfigs[provider];
        document.getElementById("ecommerceForm").reset();
        document.getElementById("deleteEcommerce").style.display = "none";
        // Check if there are other ecommerce integrations
        if (Object.keys(window.ecommerceConfigs).length === 0) {
            updateStatus("ecommerce", false);
        }
      }
    } else {
      showToast("Failed to remove integration", "error");
    }
  } catch (error) {
    showToast("An error occurred", "error");
  }
}

function togglePassword(inputId) {
  const input = document.getElementById(inputId);
  input.type = input.type === "password" ? "text" : "password";
}

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
            <span class="toast-icon">${
              type === "success" ? "✓" : type === "error" ? "✕" : "ℹ"
            }</span>
            <span class="toast-message">${message}</span>
        `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("fade-out");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function copyToClipboard(text, successMsg) {
  navigator.clipboard.writeText(text).then(() => {
    showToast(successMsg || "Copied to clipboard!", "success");
  }).catch(err => {
    console.error('Failed to copy: ', err);
    showToast("Failed to copy text", "error");
  });
}

async function changeVerifyToken() {
  if (!confirm("Are you sure you want to change the Verify Token? You will need to update it in your Meta Developer Portal as well.")) {
    return;
  }
  
  try {
    const response = await fetch("/api/integrations/token", { method: "POST" });
    const data = await response.json();
    
    if (response.ok) {
      document.getElementById("displayVerifyToken").value = data.token;
      showToast("Verify Token updated!", "success");
    } else {
      showToast("Failed to update token", "error");
    }
  } catch (err) {
    showToast("Error updating token", "error");
  }
}
