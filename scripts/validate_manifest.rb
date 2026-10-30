#!/usr/bin/env ruby

# frozen_string_literal: true

# 这个脚本是首版 Manifest 的确定性边界检查。
# 它不执行能力，也不把文件存在提升为能力已经可用；只有明确写入 Manifest 的入口才会被检查。

require "json"
require "optparse"
require "yaml"

REPOSITORY = "suanhai-team-external-expression-infrastructure"
ALLOWED_KINDS = %w[skill template tool workflow harness check].freeze
ALLOWED_ROOT_KEYS = %w[schema_version repository capabilities].freeze
ALLOWED_CAPABILITY_KEYS = %w[id kind path entrypoint purpose inputs outputs uses].freeze
SUPPORTED_SCHEMA_KEYS = %w[$schema $id title type additionalProperties required properties const enum items pattern minLength].freeze

options = {
  root: File.expand_path("..", __dir__),
  manifest: "manifest.yml",
  schema: "schemas/manifest.schema.json"
}

OptionParser.new do |parser|
  parser.banner = "Usage: ruby scripts/validate_manifest.rb [options]"
  parser.on("--root PATH", "仓库根目录") { |value| options[:root] = File.expand_path(value) }
  parser.on("--manifest PATH", "Manifest 路径，相对于仓库根目录") { |value| options[:manifest] = value }
  parser.on("--schema PATH", "Schema 路径，相对于仓库根目录") { |value| options[:schema] = value }
end.parse!

root = File.realpath(options[:root])

def fail_validation(message)
  warn "Manifest validation failed: #{message}"
  exit 1
end

def read_path(root, relative_path, label)
  fail_validation("#{label} 不存在: #{relative_path}") unless File.file?(File.expand_path(relative_path, root))
  File.expand_path(relative_path, root)
end

manifest_path = read_path(root, options[:manifest], "Manifest")
schema_path = read_path(root, options[:schema], "Schema")

begin
  schema = JSON.parse(File.read(schema_path))
rescue JSON::ParserError => error
  fail_validation("Schema 不是合法 JSON: #{error.message}")
end

begin
  manifest = YAML.safe_load(File.read(manifest_path), permitted_classes: [], aliases: false)
rescue Psych::Exception => error
  fail_validation("Manifest 不是合法 YAML: #{error.message}")
end

def schema_errors(value, schema, location = "$", errors = [])
  unless schema.is_a?(Hash)
    errors << "#{location}: schema 节点必须是 object"
    return errors
  end

  unsupported = schema.keys - SUPPORTED_SCHEMA_KEYS
  errors << "#{location}: 使用了校验器不支持的 schema 关键字 #{unsupported.join(', ')}" unless unsupported.empty?

  type_matches = case schema["type"]
                 when "object" then value.is_a?(Hash)
                 when "array" then value.is_a?(Array)
                 when "string" then value.is_a?(String)
                 when "integer" then value.is_a?(Integer)
                 else true
                 end
  errors << "#{location}: 必须是 #{schema["type"]}" if schema["type"] && !type_matches
  return errors unless type_matches

  errors << "#{location}: 必须等于 #{schema["const"].inspect}" if schema.key?("const") && value != schema["const"]
  if schema["enum"] && !schema["enum"].include?(value)
    errors << "#{location}: 值不在允许集合中"
  end
  if schema["minLength"] && value.is_a?(String) && value.length < schema["minLength"]
    errors << "#{location}: 长度不能小于 #{schema["minLength"]}"
  end
  if schema["pattern"] && value.is_a?(String) && !Regexp.new(schema["pattern"]).match?(value)
    errors << "#{location}: 格式不符合 #{schema["pattern"]}"
  end

  if value.is_a?(Hash)
    required = schema["required"] || []
    (required - value.keys).each { |key| errors << "#{location}.#{key}: 缺少必需字段" }

    properties = schema["properties"] || {}
    value.each do |key, child|
      property_schema = properties[key]
      if property_schema
        schema_errors(child, property_schema, "#{location}.#{key}", errors)
      elsif schema["additionalProperties"] == false
        errors << "#{location}.#{key}: 不允许的字段"
      end
    end
  elsif value.is_a?(Array) && schema["items"]
    value.each_with_index do |child, index|
      schema_errors(child, schema["items"], "#{location}[#{index}]", errors)
    end
  end

  errors
end

schema_issues = schema_errors(manifest, schema)
fail_validation(schema_issues.join("\n")) unless schema_issues.empty?

fail_validation("repository 必须为 #{REPOSITORY}") unless manifest["repository"] == REPOSITORY

def relative_posix_path?(value)
  return false unless value.is_a?(String) && !value.empty?
  return false if value.include?("\\") || value.start_with?("/") || value.match?(/\A[A-Za-z]:/)

  !value.split("/").include?("..")
end

manifest["capabilities"].each_with_index do |capability, index|
  prefix = "capabilities[#{index}]"
  fail_validation("#{prefix} 必须是 mapping") unless capability.is_a?(Hash)

  unknown_keys = capability.keys.map(&:to_s) - ALLOWED_CAPABILITY_KEYS
  fail_validation("#{prefix} 存在未知字段: #{unknown_keys.join(', ')}") unless unknown_keys.empty?

  %w[id kind path entrypoint purpose].each do |key|
    fail_validation("#{prefix}.#{key} 缺失") unless capability.key?(key)
  end

  id = capability["id"]
  fail_validation("#{prefix}.id 必须是非空标识") unless id.is_a?(String) && id.match?(/\A[a-z0-9][a-z0-9._-]*\z/)
  fail_validation("#{prefix}.kind 不受支持") unless ALLOWED_KINDS.include?(capability["kind"])
  fail_validation("#{prefix}.purpose 必须是非空字符串") unless capability["purpose"].is_a?(String) && !capability["purpose"].strip.empty?

  %w[inputs outputs uses].each do |key|
    next unless capability.key?(key)

    values = capability[key]
    fail_validation("#{prefix}.#{key} 必须是字符串数组") unless values.is_a?(Array) && values.all? { |value| value.is_a?(String) }
    if key == "uses"
      values.each do |value|
        fail_validation("#{prefix}.uses 包含非法能力 ID: #{value}") unless value.match?(/\A[a-z0-9][a-z0-9._-]*\z/)
      end
    end
  end

  %w[path entrypoint].each do |key|
    value = capability[key]
    fail_validation("#{prefix}.#{key} 必须是仓库内相对 POSIX 路径") unless relative_posix_path?(value)

    expanded = File.expand_path(value, root)
    root_prefix = root.end_with?(File::SEPARATOR) ? root : "#{root}#{File::SEPARATOR}"
    fail_validation("#{prefix}.#{key} 越出仓库根目录") unless expanded == root || expanded.start_with?(root_prefix)
    fail_validation("#{prefix}.#{key} 指向的入口不存在: #{value}") unless File.exist?(expanded)
    resolved = File.realpath(expanded)
    fail_validation("#{prefix}.#{key} 通过符号链接越出仓库根目录") unless resolved == root || resolved.start_with?(root_prefix)
  end
end

capability_ids = manifest["capabilities"].map { |capability| capability["id"] }
fail_validation("capabilities 中存在重复 ID") unless capability_ids.uniq.length == capability_ids.length
manifest["capabilities"].each_with_index do |capability, index|
  next unless capability.key?("uses")
  fail_validation("capabilities[#{index}].uses 只允许 workflow 声明依赖") unless capability["kind"] == "workflow"

  capability["uses"].each do |dependency|
    fail_validation("capabilities[#{index}].uses 引用了未声明能力: #{dependency}") unless capability_ids.include?(dependency)
  end
end

puts "Manifest valid: #{manifest_path} (#{manifest["capabilities"].length} capabilities)"
