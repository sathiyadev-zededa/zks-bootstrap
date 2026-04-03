"""
RT Mutating Admission Webhook — ZEDEDA / Saudi Aramco Demo
Intercepts pod CREATE requests and injects RT configuration
for any pod labelled rt-workload: "true"

Injections:
  - Prepends taskset -c <RT_CPU_CORE> to container command
  - Adds SYS_NICE + IPC_LOCK capabilities (SCHED_FIFO + mlockall)
  - Adds annotations: rt-pinned-cpu=<core>, rt-webhook-mutated=true

Config via environment variables (set by Helm values.yaml):
  RT_CPU_CORE  — CPU core to pin to          (default: "3")
  RT_LABEL     — Pod label key to look for   (default: "rt-workload")
  RT_VALUE     — Pod label value to match    (default: "true")
"""

import os
import json
import base64
import ssl
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ── Runtime config from environment (injected by Helm Deployment template) ───
RT_CPU_CORE = os.environ.get("RT_CPU_CORE", "3")
RT_LABEL    = os.environ.get("RT_LABEL",    "rt-workload")
RT_VALUE    = os.environ.get("RT_VALUE",    "true")


# ─────────────────────────────────────────────────────────────────────────────
#  Health endpoint (liveness + readiness probe)
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":      "ok",
        "rt_cpu_core": RT_CPU_CORE,
        "rt_label":    f"{RT_LABEL}={RT_VALUE}",
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
#  Admission endpoint — called by k3s API server for every pod CREATE
#  that matches the MutatingWebhookConfiguration rules
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/mutate", methods=["POST"])
def mutate():
    review = request.get_json()

    if not review:
        logger.error("Received empty request body")
        return jsonify({"error": "empty body"}), 400

    req         = review.get("request", {})
    request_uid = req.get("uid", "")
    pod         = req.get("object", {})
    labels      = pod.get("metadata", {}).get("labels", {})
    pod_name    = pod.get("metadata", {}).get("name", "<unnamed>")

    logger.info(f"AdmissionReview uid={request_uid} pod={pod_name}")

    if labels.get(RT_LABEL) == RT_VALUE:
        logger.info(f"Pod '{pod_name}' matches {RT_LABEL}={RT_VALUE} — applying RT patches")
        patches   = build_patches(pod)
        patch_b64 = base64.b64encode(json.dumps(patches).encode()).decode()

        response = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid":       request_uid,
                "allowed":   True,
                "patchType": "JSONPatch",
                "patch":     patch_b64,
            },
        }
        logger.info(f"Applied {len(patches)} patches to pod '{pod_name}'")

    else:
        logger.info(f"Pod '{pod_name}' no RT label — passing through unchanged")
        response = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid":     request_uid,
                "allowed": True,
            },
        }

    return jsonify(response)


# ─────────────────────────────────────────────────────────────────────────────
#  Build JSON Patch (RFC 6902) operations
# ─────────────────────────────────────────────────────────────────────────────
def build_patches(pod):
    patches    = []
    containers = pod.get("spec", {}).get("containers", [])

    for i, container in enumerate(containers):
        name = container.get("name", f"container-{i}")

        # ── Patch 1: Prepend taskset -c <core> to command ────────────────────
        command = container.get("command", [])
        if command:
            if command[0] != "taskset":
                new_command = ["taskset", "-c", RT_CPU_CORE] + command
                patches.append({
                    "op":    "replace",
                    "path":  f"/spec/containers/{i}/command",
                    "value": new_command,
                })
                logger.info(f"  [{name}] command patched: {new_command}")
            else:
                logger.info(f"  [{name}] taskset already present, skipping")
        else:
            patches.append({
                "op":    "add",
                "path":  f"/spec/containers/{i}/command",
                "value": ["taskset", "-c", RT_CPU_CORE],
            })
            logger.info(f"  [{name}] no command, added taskset wrapper")

        # ── Patch 2: Inject SYS_NICE + IPC_LOCK capabilities ─────────────────
        sec_ctx = container.get("securityContext")

        if sec_ctx is None:
            patches.append({
                "op":    "add",
                "path":  f"/spec/containers/{i}/securityContext",
                "value": {"capabilities": {"add": ["SYS_NICE", "IPC_LOCK"]}},
            })
        else:
            caps = sec_ctx.get("capabilities")
            if caps is None:
                patches.append({
                    "op":    "add",
                    "path":  f"/spec/containers/{i}/securityContext/capabilities",
                    "value": {"add": ["SYS_NICE", "IPC_LOCK"]},
                })
            else:
                existing = caps.get("add", [])
                new_caps = list(existing)
                for cap in ["SYS_NICE", "IPC_LOCK"]:
                    if cap not in new_caps:
                        new_caps.append(cap)
                op = "replace" if existing else "add"
                patches.append({
                    "op":    op,
                    "path":  f"/spec/containers/{i}/securityContext/capabilities/add",
                    "value": new_caps,
                })

        logger.info(f"  [{name}] injected SYS_NICE + IPC_LOCK")

    # ── Patch 3: Add RT annotations ──────────────────────────────────────────
    annotations = pod.get("metadata", {}).get("annotations")
    if annotations is None:
        patches.append({
            "op":    "add",
            "path":  "/metadata/annotations",
            "value": {
                "rt-pinned-cpu":      RT_CPU_CORE,
                "rt-webhook-mutated": "true",
            },
        })
    else:
        patches.append({
            "op":    "add",
            "path":  "/metadata/annotations/rt-pinned-cpu",
            "value": RT_CPU_CORE,
        })
        patches.append({
            "op":    "add",
            "path":  "/metadata/annotations/rt-webhook-mutated",
            "value": "true",
        })

    return patches


# ─────────────────────────────────────────────────────────────────────────────
#  Entrypoint
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("/certs/tls.crt", "/certs/tls.key")

    logger.info("=" * 60)
    logger.info("  ZEDEDA RT Mutating Admission Webhook")
    logger.info(f"  Listening : 0.0.0.0:8443 (TLS)")
    logger.info(f"  RT label  : {RT_LABEL}={RT_VALUE}")
    logger.info(f"  RT core   : {RT_CPU_CORE}")
    logger.info("=" * 60)

    app.run(host="0.0.0.0", port=8443, ssl_context=context, threaded=True)
