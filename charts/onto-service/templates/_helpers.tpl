{{/*
OaaS 通用 Helper 模板
*/}}

{{/* 生成全名 */}}
{{- define "onto-service.fullname" -}}
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

{{/* 生成名称 */}}
{{- define "onto-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* 生成 Chart 标签 */}}
{{- define "onto-service.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* 通用标签 */}}
{{- define "onto-service.labels" -}}
helm.sh/chart: {{ include "onto-service.chart" . }}
{{ include "onto-service.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* 选择器标签 */}}
{{- define "onto-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "onto-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Java 服务全名 */}}
{{- define "onto-service.java.fullname" -}}
{{- printf "%s-java" (include "onto-service.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Python 服务全名 */}}
{{- define "onto-service.python.fullname" -}}
{{- printf "%s-python" (include "onto-service.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Web 服务全名 */}}
{{- define "onto-service.web.fullname" -}}
{{- printf "%s-web" (include "onto-service.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* 服务账户名 */}}
{{- define "onto-service.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "onto-service.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
