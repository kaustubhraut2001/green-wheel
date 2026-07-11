# Docker Hub DNS Fix
# ================
# The error "failed to resolve source metadata for docker.io" means Docker
# cannot reach Docker Hub. This is almost always a DNS issue on Windows.
#
# QUICK FIX (takes 2 minutes):
# ─────────────────────────────
# 1. Open Docker Desktop
# 2. Click the gear icon (Settings)
# 3. Click "Docker Engine" in the left sidebar
# 4. You will see a JSON config. Add the "dns" line so it looks like this:
#
#    {
#      "builder": { "gc": { "defaultKeepStorage": "20GB", "enabled": true } },
#      "experimental": false,
#      "dns": ["8.8.8.8", "8.8.4.4"]
#    }
#
# 5. Click "Apply & Restart"
# 6. Wait for Docker to restart (30-60 seconds)
# 7. Run:  fix-and-start.bat
#
# ─────────────────────────────
# WHY THIS HAPPENS:
# Docker Desktop on Windows uses its own virtual network adapter.
# When Windows switches networks (WiFi → Ethernet, VPN on/off),
# Docker's DNS can get stuck pointing at an unreachable resolver.
# Adding Google's DNS (8.8.8.8) as a fallback fixes it permanently.
#
# ALTERNATIVE: Just restart Docker Desktop from the system tray.
# (Right-click the whale icon → Restart)
# This often fixes it without changing settings.
