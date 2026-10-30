#!/usr/bin/env bash
# Prepares the repo to call Gemini in your Google Cloud project (Vertex AI). Safe to run more than once.
# Run it from the repo root, in Cloud Shell or on a laptop with gcloud:  bash scripts/setup.sh
set -uo pipefail

ok()   { echo "✅ $*"; }
warn() { echo "⚠️  $*"; }
fail() { echo "❌ $*"; exit 1; }

cd "$(dirname "$0")/.." || exit 1

# 1. Project
PROJECT="$(gcloud config get-value project 2>/dev/null)"
[ -n "$PROJECT" ] || fail "No project set. Run \`gcloud config set project YOUR_PROJECT_ID\` first."
gcloud projects describe "$PROJECT" --format="value(projectId)" >/dev/null 2>&1 \
  || fail "Can't open project '$PROJECT'. Check the Project ID (not the name) and run \`gcloud config set project YOUR_PROJECT_ID\` again."
ok "Project: $PROJECT"

# 2. Billing (Gemini on Vertex AI needs it; free trial credits work)
BILLING="$(gcloud billing projects describe "$PROJECT" --format="value(billingEnabled)" 2>/dev/null)"
case "$BILLING" in
  True)  ok "Billing is linked" ;;
  False) fail "Billing isn't linked to $PROJECT. In the console open Billing › Link a billing account, then run this script again." ;;
  *)     warn "Couldn't check billing (you may not have permission to see it). Continuing." ;;
esac

# 3. Credentials: Cloud Shell has them; a laptop needs application-default credentials
if [ "${CLOUD_SHELL:-}" != "true" ]; then
  gcloud auth application-default print-access-token >/dev/null 2>&1 \
    || fail "No application-default credentials. Run \`gcloud auth application-default login\`, then run this script again."
fi
ok "Credentials found"

# 4. The Vertex AI API (about a minute the first time)
gcloud services enable aiplatform.googleapis.com --project "$PROJECT" --quiet >/dev/null 2>&1 \
  || fail "Couldn't turn on the Vertex AI API. Wait a minute and run this script again."
ok "Vertex AI API is on"

# 5. uv and the Python packages
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 || fail "Couldn't install uv. Check your connection and run this script again."
fi
uv sync --quiet 2>/dev/null || fail "Couldn't install the Python packages. Run this script again."
ok "Packages installed (ADK $(uv run --quiet python -c 'import google.adk; print(google.adk.__version__)'))"

# 6. .env: the agents call Gemini in your project. "global" spreads the load across regions.
if [ -f .env ] && ! grep -q "^GOOGLE_CLOUD_PROJECT=$PROJECT$" .env; then
  cp .env .env.bak && warn "Your old .env is now .env.bak"
fi
cat > .env <<ENV
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=$PROJECT
GOOGLE_CLOUD_LOCATION=global
MODEL=gemini-3.8-flash
ENV
ok ".env written"

# 7. Next step
if [ "${CLOUD_SHELL:-}" = "true" ]; then
  echo "✅ Ready. Next: uv run adk web --reload_agents --port 8080 --allow_origins \"*\" steps"
else
  echo "✅ Ready. Next: uv run adk web --reload_agents steps"
fi
