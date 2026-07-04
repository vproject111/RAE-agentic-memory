{{/*
Expand the name of the chart.
*/}}
{{- define "rae.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "rae.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "rae.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "rae.labels" -}}
helm.sh/chart: {{ include "rae.chart" . }}
{{ include "rae.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "rae.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rae.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "rae.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "rae.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
PostgreSQL connection string
*/}}
{{- define "rae.postgresHost" -}}
{{- .Values.postgresql.host }}
{{- end }}

{{/*
Redis host
*/}}
{{- define "rae.redisHost" -}}
{{- .Values.redis.host }}
{{- end }}

{{/*
Qdrant host
*/}}
{{- define "rae.qdrantHost" -}}
{{- .Values.qdrant.host }}
{{- end }}
