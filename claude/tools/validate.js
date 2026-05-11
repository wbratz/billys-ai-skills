#!/usr/bin/env node
/**
 * Validates registry/index.yaml against the actual files in skills/, agents/, plugins/.
 * Exit 0 = all good. Exit 1 = validation errors found.
 */

const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

const ROOT = path.resolve(__dirname, "..");
const REGISTRY_PATH = path.join(ROOT, "registry", "index.yaml");
const CATEGORIES_PATH = path.join(ROOT, "registry", "categories.yaml");

const REQUIRED_FIELDS = ["id", "type", "name", "description", "category", "author", "version", "path"];
const VALID_TYPES = ["skill", "agent", "plugin"];
const SEMVER_RE = /^\d+\.\d+\.\d+$/;
const ID_RE = /^[a-z0-9-]+\/[a-z0-9-]+$/;

let errors = [];

function error(context, msg) {
  errors.push(`[${context}] ${msg}`);
}

function loadYaml(filePath) {
  try {
    return yaml.load(fs.readFileSync(filePath, "utf8"));
  } catch (e) {
    console.error(`Failed to parse ${filePath}: ${e.message}`);
    process.exit(1);
  }
}

const registry = loadYaml(REGISTRY_PATH);
const categoriesData = loadYaml(CATEGORIES_PATH);
const validCategories = new Set((categoriesData.categories || []).map((c) => c.id));

const sections = { skills: "skill", agents: "agent", plugins: "plugin" };

for (const [section, expectedType] of Object.entries(sections)) {
  const entries = registry[section] || [];
  for (const entry of entries) {
    const ctx = entry.id || `${section}[unknown]`;

    // Required fields
    for (const field of REQUIRED_FIELDS) {
      if (!entry[field]) error(ctx, `Missing required field: ${field}`);
    }

    if (entry.id && !ID_RE.test(entry.id)) {
      error(ctx, `id must be namespace/slug (lowercase kebab-case), got: ${entry.id}`);
    }

    if (entry.type && entry.type !== expectedType) {
      error(ctx, `type mismatch: entry is in '${section}' but type is '${entry.type}'`);
    }

    if (entry.type && !VALID_TYPES.includes(entry.type)) {
      error(ctx, `invalid type: ${entry.type}`);
    }

    if (entry.version && !SEMVER_RE.test(entry.version)) {
      error(ctx, `version must be semver (x.y.z), got: ${entry.version}`);
    }

    if (entry.category && !validCategories.has(entry.category)) {
      error(ctx, `unknown category '${entry.category}' — add it to registry/categories.yaml first`);
    }

    if (entry.description && entry.description.length > 140) {
      error(ctx, `description exceeds 140 chars (${entry.description.length})`);
    }

    if (entry.tags && entry.tags.length > 8) {
      error(ctx, `too many tags (${entry.tags.length}); max is 8`);
    }

    // Check the definition file actually exists
    if (entry.path) {
      const absPath = path.join(ROOT, entry.path);
      if (!fs.existsSync(absPath)) {
        error(ctx, `definition file not found: ${entry.path}`);
      }
    }
  }
}

if (errors.length > 0) {
  console.error(`\nValidation failed — ${errors.length} error(s):\n`);
  errors.forEach((e) => console.error(`  ✗ ${e}`));
  console.error();
  process.exit(1);
} else {
  const total =
    (registry.skills || []).length +
    (registry.agents || []).length +
    (registry.plugins || []).length;
  console.log(`Validation passed — ${total} registry entries OK.`);
  process.exit(0);
}
