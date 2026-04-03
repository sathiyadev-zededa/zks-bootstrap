#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
#  install.sh — Deploy RT Webhook via Helm (no cert-manager, no extra Jobs)
#
#  How it works:
#    helm install  → Helm renders templates:
#                    • genCA + genSignedCert produce 10-year TLS certs
#                    • Secret (tls.crt, tls.key, ca.crt) written to cluster
#                    • MutatingWebhookConfiguration with correct caBundle
#                    • Deployment + Service for the webhook pod
#    helm upgrade  → lookup() finds existing Secret → reuses certs (no churn)
#
#  Cert rotation:
#    kubectl delete secret rt-webhook-tls -n aramco-demo
#    helm upgrade rt-webhook ./rt-webhook
#    kubectl rollout restart deployment/rt-webhook -n aramco-demo
#
#  Usage:
#    ./install.sh
#
#  Upgrade:
#    helm upgrade rt-webhook ./rt-webhook
#
#  Uninstall:
#    helm uninstall rt-webhook
# ─────────────────────────────────────────────────────────────────────────────
set -e

GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

echo ""
echo "============================================"
echo "  ZEDEDA RT Webhook — Helm Deploy"
echo "  Device: $(hostname)"
echo "============================================"
echo ""

# Check kubectl and helm are available
command -v kubectl > /dev/null || fail "kubectl not found"
command -v helm    > /dev/null || {
  info "Helm not found — installing..."
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
}

ok "kubectl: $(kubectl version --client --short 2>/dev/null | head -1)"
ok "helm:    $(helm version --short)"
echo ""

# Install or upgrade
RELEASE="rt-webhook"
NAMESPACE="aramco-demo"

if helm status "${RELEASE}" --namespace "${NAMESPACE}" > /dev/null 2>&1; then
  info "Upgrading existing release '${RELEASE}'..."
  helm upgrade "${RELEASE}" ./rt-webhook --namespace "${NAMESPACE}"
else
  info "Installing release '${RELEASE}'..."
  helm install "${RELEASE}" ./rt-webhook --namespace "${NAMESPACE}" --create-namespace
fi

echo ""
ok "Helm install complete"
echo ""
echo "  Watch webhook pod:         kubectl logs -l app.kubernetes.io/name=rt-webhook -n ${NAMESPACE} -f"
echo "  Verify caBundle is set:    kubectl get mutatingwebhookconfiguration rt-webhook -o jsonpath='{.webhooks[0].clientConfig.caBundle}' | wc -c"
echo "  Check TLS secret:          kubectl get secret rt-webhook-tls -n ${NAMESPACE}"
echo ""
