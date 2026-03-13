#!/usr/bin/env bash
# Run Claude Code in console mode with the same configuration as VSCode

export AWS_PROFILE="nonprod"
export AWS_REGION="eu-central-1"
export CLAUDE_CODE_USE_BEDROCK="1"
export CLAUDE_CODE_ENABLE_TELEMETRY="1"

export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"
export OTEL_METRICS_EXPORTER="otlp"
export OTEL_LOGS_EXPORTER="otlp"
export OTEL_METRIC_EXPORT_INTERVAL="5000"
export OTEL_RESOURCE_ATTRIBUTES="machine.name=${HOST},user.id=console"

export ANTHROPIC_MODEL="arn:aws:bedrock:eu-central-1:654654484446:inference-profile/eu.anthropic.claude-sonnet-4-6"

exec claude "$@"
