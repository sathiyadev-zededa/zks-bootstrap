{{/*
_helpers.tpl — Shared template helpers for rt-webhook Helm chart
*/}}

{{/*
Chart name
*/}}
{{- define "rt-webhook.name" -}}
{{- .Chart.Name }}
{{- end }}

{{/*
Full name — avoids duplication when release name already contains chart name.
  helm install rt-webhook ./rt-webhook  →  "rt-webhook"       (not rt-webhook-rt-webhook)
  helm install my-release ./rt-webhook  →  "my-release-rt-webhook"
*/}}
{{- define "rt-webhook.fullname" -}}
{{- if contains .Chart.Name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Common labels applied to every resource
*/}}
{{- define "rt-webhook.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "rt-webhook.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels — used by Deployment selector and Service selector
Must be stable across upgrades (do not include chart version)
*/}}
{{- define "rt-webhook.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rt-webhook.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Image reference — combines repository and tag
*/}}
{{- define "rt-webhook.image" -}}
{{- printf "%s:%s" .Values.image.repository .Values.image.tag }}
{{- end }}
