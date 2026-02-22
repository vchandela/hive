# SDK FAQ

## SDK Version Compatibility

DataStack SDKs follow semantic versioning. Here's what you need to know about SDK version compatibility:

**Current SDK versions:**

| SDK | Latest Version | Minimum Supported |
|-----|---------------|-------------------|
| Python SDK | 3.2.1 | 2.0.0 |
| Node.js SDK | 2.4.0 | 1.5.0 |
| Go SDK | 1.1.0 | 1.0.0 |

**SDK version compatibility policy:**

- **Major SDK versions** (e.g., SDK 2.x → 3.x): May include breaking SDK API changes. Migration guides are provided for each major SDK version.
- **Minor SDK versions** (e.g., SDK 3.1 → 3.2): New features, backward-compatible. Safe to upgrade your SDK.
- **Patch SDK versions** (e.g., SDK 3.2.0 → 3.2.1): Bug fixes only. Always upgrade your SDK to the latest patch.

The DataStack API maintains backward compatibility for at least 2 years. SDK versions older than the minimum supported SDK version may stop working without notice.

## Deprecated SDKs

The following SDKs have been deprecated and should be migrated:

- **Ruby SDK** (deprecated January 2024): Use the REST API directly or the community-maintained Ruby SDK gem `datastack-ruby-unofficial`.
- **Java SDK** (deprecated March 2024): Replaced by the Kotlin SDK which supports both Java and Kotlin SDK usage.
- **Python SDK v1.x**: End of life since June 2024. Upgrade to Python SDK v2.x or later.

Deprecated SDKs continue to work but receive no updates, security patches, or support. Migrate your SDK integration before the end-of-life date.

## Community SDKs

In addition to official SDKs, the community maintains SDK libraries for other languages:

- **Rust SDK**: `datastack-rs` (maintained by @rustdev, 500+ GitHub stars). This community SDK supports all query and import endpoints.
- **Elixir SDK**: `ex_datastack` (maintained by @elixirfan). This community SDK covers core query functionality.
- **PHP SDK**: `datastack-php` (maintained by DataStack community). This community SDK is used in production by several WordPress plugins.

Community SDKs are not officially supported by DataStack. Check their GitHub repositories for SDK documentation, issue tracking, and contribution guidelines.
