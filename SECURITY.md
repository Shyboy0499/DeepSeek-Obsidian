# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not open a public issue**.

Instead, report it privately by emailing the maintainers. We will respond as
quickly as possible and work with you to resolve the issue responsibly.

## Security Considerations

DeepSeek-Obsidian handles sensitive data:

- **API keys** are read from environment variables only and are never stored
  in config files or logs.
- **Your notes** are read locally from your Obsidian vault and are never
  uploaded except as context to the AI provider you configured.
- **Shell commands** (`!command`) execute locally with your user's permissions.

Please keep these in mind when reviewing or contributing code.
