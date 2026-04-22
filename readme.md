# ZEDEDA ZKS Bootstrap (Debian Package)

This package installs **K3s** and automatically **imports the Kubernetes cluster into ZEDEDA ZKS** during package installation.

The bootstrap logic is executed **once at install time** via `dpkg -i`.  

---

## What this package does

During installation, the package:

1. Reads configuration from `/etc/zks-bootstrap/config.env`
2. Installs **K3s** using the official installer (`get.k3s.io`) or from a pre-downloaded binary in case of an airgap environment
3. Waits for the Kubernetes API and node to become ready
4. Authenticates with ZEDEDA (API token or username/password)
5. Creates a ZKS cluster instance
6. Fetches and applies the ZKS import manifest
7. Waits until the cluster reaches **RUN_STATE_ONLINE**

---

## TLS / insecure ZEDEDA endpoint

If your ZEDEDA endpoint uses a self-signed/untrusted TLS certificate, set this in `/etc/zks-bootstrap/config.env`:

```bash
ZEDCONTROL_INSECURE=1
```

This makes the bootstrapper use `curl --insecure` for ZEDEDA/ZKS API calls and for downloading the registration manifest.

## K3s registry mirror (registries.yaml)

If your cluster pulls images from an internal registry, the bootstrapper can write `/etc/rancher/k3s/registries.yaml`.

Defaults (configurable in `/etc/zks-bootstrap/config.env`):

```bash
K3S_REGISTRY_HOST="forgejo-zks.local.zededa.net"
K3S_REGISTRY_INSECURE_SKIP_VERIFY=1
```
